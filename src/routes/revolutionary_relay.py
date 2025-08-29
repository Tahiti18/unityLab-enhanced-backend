# routes/revolutionary_relay.py
import os
import uuid
import logging
import threading
from datetime import datetime, timezone

import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
revolutionary_relay_bp = Blueprint("revolutionary_relay", __name__)
logger = logging.getLogger("revolutionary_relay")
logger.setLevel(logging.INFO)

OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# In-memory session store. (Swap to DB/Redis later if needed)
# session schema:
# {
#   id, prompt, mode, status: running|completed|error,
#   created_at, completed_at, progress (0..100),
#   results: [{agent, model, response, error}], error
# }
SESSIONS = {}

# Default agent set if /api/agents/list is unavailable
FALLBACK_AGENTS = [
    {"name": "gpt-4o",      "model": "openai/gpt-4o"},
    {"name": "claude-3.5",  "model": "anthropic/claude-3.5-sonnet"},
    {"name": "deepseek-r1", "model": "deepseek/deepseek-r1"},
]

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _new_session(prompt: str, mode: str) -> dict:
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "prompt": prompt,
        "mode": mode,  # "expert_panel" | "conference_chain"
        "status": "running",
        "created_at": _utc_now(),
        "completed_at": None,
        "progress": 0,
        "results": [],
        "error": None,
    }
    SESSIONS[sid] = session
    logger.info(f"[Relay] session started id={sid} mode={mode}")
    return session

def _complete_session(session_id: str, results: list):
    s = SESSIONS.get(session_id)
    if not s:
        return
    s["results"] = results
    s["status"] = "completed"
    s["completed_at"] = _utc_now()
    s["progress"] = 100
    logger.info(f"[Relay] session completed id={session_id}")

def _error_session(session_id: str, message: str):
    s = SESSIONS.get(session_id)
    if not s:
        return
    s["status"] = "error"
    s["error"] = message
    s["completed_at"] = _utc_now()
    s["progress"] = s.get("progress", 0)
    logger.error(f"[Relay] session error id={session_id}: {message}")

def _get_active_agents_from_backend() -> list:
    """
    Fetch active agents from your own backend:
      GET /api/agents/list  -> {"agents": {...}}
    Falls back to a strong default trio if unreachable.
    """
    try:
        base = request.host_url.rstrip("/")
        url = f"{base}/api/agents/list"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        agents_dict = data.get("agents", {})
        active = []
        for key, v in agents_dict.items():
            if isinstance(v, dict) and v.get("active"):
                active.append({"name": v.get("name", key), "model": v.get("model")})
        if not active:
            logger.warning("[Relay] /api/agents/list returned no active agents; using fallback.")
            return FALLBACK_AGENTS
        return active
    except Exception as e:
        logger.warning(f"[Relay] could not load /api/agents/list; using fallback. err={e}")
        return FALLBACK_AGENTS

def _call_openrouter(model: str, prompt: str) -> str:
    """
    Call OpenRouter model with the given prompt.
    Debug logs show whether the key is present and what HTTP status/body we got.
    """
    # === DEBUG: confirm key presence & prefix ===
    if OPENROUTER_API_KEY:
        logger.info(f"[Relay] Using OPENROUTER_API_KEY prefix: {OPENROUTER_API_KEY[:10]}...")
    else:
        # Immediate, explicit error if key is missing at runtime
        raise RuntimeError("OPENROUTER_API_KEY is missing at runtime.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=60)
    except Exception as e:
        logger.error(f"[Relay] OpenRouter network error model={model}: {type(e).__name__}: {e}")
        raise

    # === DEBUG: log status & brief body ===
    status = resp.status_code
    tail = resp.text[:500] if resp.text else ""
    logger.info(f"[Relay] OpenRouter response model={model} status={status} body_snippet={tail!r}")

    # Raise for HTTP errors so we capture details in results
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        # If schema unexpected, log full JSON snippet
        logger.error(f"[Relay] Unexpected OpenRouter schema for model={model}: {data}")
        raise

# -----------------------------------------------------------------------------
# Workers (run in background threads)
# -----------------------------------------------------------------------------
def _run_expert_panel(session_id: str):
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _get_active_agents_from_backend()
        results = []
        total = max(1, len(agents))
        for idx, agent in enumerate(agents, start=1):
            try:
                out = _call_openrouter(agent["model"], s["prompt"])
                results.append({
                    "agent": agent["name"], "model": agent["model"],
                    "response": out, "error": None
                })
            except Exception as e:
                results.append({
                    "agent": agent["name"], "model": agent["model"],
                    "response": None, "error": f"{type(e).__name__}: {e}"
                })
            s["progress"] = int(idx * 100 / total)
        _complete_session(session_id, results)
    except Exception as e:
        _error_session(session_id, f"{type(e).__name__}: {e}")

def _run_conference_chain(session_id: str):
    """Sequential sticky chain: each agent builds on prior output."""
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _get_active_agents_from_backend()
        running_context = s["prompt"]
        results = []
        total = max(1, len(agents))
        for idx, agent in enumerate(agents, start=1):
            try:
                prompt = (
                    "Build on the evolving conference discussion below.\n\n"
                    f"=== Current context ===\n{running_context}\n\n"
                    "=== Your task ===\nAdd the next best contribution (concise but substantive), "
                    "avoid repetition, and push the discussion forward with concrete insights."
                )
                out = _call_openrouter(agent["model"], prompt)
                results.append({
                    "agent": agent["name"], "model": agent["model"],
                    "response": out, "error": None
                })
                running_context += f"\n\n[{agent['name']}]: {out}"
            except Exception as e:
                results.append({
                    "agent": agent["name"], "model": agent["model"],
                    "response": None, "error": f"{type(e).__name__}: {e}"
                })
            s["progress"] = int(idx * 100 / total)
        _complete_session(session_id, results)
    except Exception as e:
        _error_session(session_id, f"{type(e).__name__}: {e}")

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@revolutionary_relay_bp.route("/start-expert-panel", methods=["POST", "OPTIONS"])
@cross_origin()
def start_expert_panel():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    session = _new_session(prompt, "expert_panel")
    threading.Thread(target=_run_expert_panel, args=(session["id"],), daemon=True).start()

    return jsonify({
        "session_id": session["id"],
        "status": "started",
        "mode": "expert_panel"
    }), 200

@revolutionary_relay_bp.route("/start-conference-chain", methods=["POST", "OPTIONS"])
@cross_origin()
def start_conference_chain():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    session = _new_session(prompt, "conference_chain")
    threading.Thread(target=_run_conference_chain, args=(session["id"],), daemon=True).start()

    return jsonify({
        "session_id": session["id"],
        "status": "started",
        "mode": "conference_chain"
    }), 200

@revolutionary_relay_bp.route("/session-status/<session_id>", methods=["GET"])
@cross_origin()
def session_status(session_id):
    s = SESSIONS.get(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": s["status"],
        "progress": s.get("progress", 0),
        "created_at": s["created_at"],
        "completed_at": s.get("completed_at"),
    }), 200

@revolutionary_relay_bp.route("/session-results/<session_id>", methods=["GET"])
@cross_origin()
def session_results(session_id):
    s = SESSIONS.get(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": s["status"],
        "results": s["results"],
        "error": s.get("error"),
    }), 200

@revolutionary_relay_bp.route("/generate-html-report/<session_id>", methods=["GET"])
@cross_origin()
def generate_html_report(session_id):
    s = SESSIONS.get(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404

    items = []
    for r in s["results"]:
        if r.get("error"):
            items.append(f"<li><b>{r['agent']}</b> ({r['model']}): "
                         f"<span style='color:#f88'>ERROR: {r['error']}</span></li>")
        else:
            safe = (r['response'] or "").replace("<","&lt;").replace(">","&gt;")
            items.append(f"<li><b>{r['agent']}</b> ({r['model']}): {safe}</li>")

    html = f"""
    <html>
      <head>
        <title>Revolutionary Relay Report</title>
        <meta charset="utf-8" />
      </head>
      <body style="font-family:Arial; background:#0a0f1c; color:#e8f6ff; padding:24px;">
        <h1>Session Report</h1>
        <p><b>Session ID:</b> {session_id}</p>
        <p><b>Status:</b> {s['status']}</p>
        <p><b>Mode:</b> {s['mode']}</p>
        <p><b>Prompt:</b> {s['prompt']}</p>
        <p><b>Progress:</b> {s.get('progress',0)}%</p>
        <h2>Results</h2>
        <ul>{''.join(items)}</ul>
      </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
