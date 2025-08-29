# src/routes/revolutionary_relay.py
import os
import uuid
import logging
import threading
from datetime import datetime, timezone

import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

# -----------------------------------------------------------------------------
# Blueprint & logging
# -----------------------------------------------------------------------------
revolutionary_relay_bp = Blueprint("revolutionary_relay", __name__)
logger = logging.getLogger("revolutionary_relay")
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Fallback agents if /api/agents is unavailable
FALLBACK_AGENTS = [
    {"name": "GPT-4o",        "model": "openai/gpt-4o"},
    {"name": "Claude 3.5",    "model": "anthropic/claude-3.5-sonnet"},
    {"name": "DeepSeek R1",   "model": "deepseek/deepseek-r1"},
]

# In-memory session store
# session = {
#   "id", "prompt", "mode", "status", "created_at", "completed_at",
#   "progress", "results": [ {agent, model, response, error} ], "error"
# }
SESSIONS = {}


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
        "mode": mode,                   # "expert_panel" | "conference_chain"
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
    logger.error(f"[Relay] session error id={session_id}: {message}")


def _get_active_agents_from_backend() -> list:
    """
    Load agents from your backend:
      GET /api/agents  -> {"agents": {...}}
    Returns a list of {"name","model"} entries.
    Falls back if anything fails.
    """
    try:
        base = request.host_url.rstrip("/")
        url = f"{base}/api/agents"  # <-- FIXED to match your backend
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        agents_dict = data.get("agents", {})
        active = []
        for key, v in agents_dict.items():
            if v.get("active") and v.get("model"):
                active.append({"name": v.get("name", key), "model": v["model"]})
        if not active:
            logger.warning("[Relay] /api/agents returned no active agents, using fallback set.")
            return FALLBACK_AGENTS
        return active
    except Exception as e:
        logger.warning(f"[Relay] could not load /api/agents: {e}. Using fallback agents.")
        return FALLBACK_AGENTS


def _call_openrouter(model: str, prompt: str) -> str:
    """
    Call OpenRouter with a simple chat completion.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing on the server.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # Defensive extraction
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return str(data)


# -----------------------------------------------------------------------------
# Workers (background threads)
# -----------------------------------------------------------------------------
def _run_expert_panel(session_id: str):
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _get_active_agents_from_backend()
        # Optional: cap to avoid huge bills; change/remove as you like.
        # agents = agents[:10]

        total = max(len(agents), 1)
        results = []

        for idx, agent in enumerate(agents, start=1):
            try:
                out = _call_openrouter(agent["model"], s["prompt"])
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": out,
                    "error": None
                })
            except Exception as e:
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": None,
                    "error": str(e)
                })
            s["progress"] = int(idx * 100 / total)

        _complete_session(session_id, results)

    except Exception as e:
        _error_session(session_id, str(e))


def _run_conference_chain(session_id: str):
    """
    Sequential chain where each agent builds on prior output.
    """
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _get_active_agents_from_backend()
        # agents = agents[:20]

        total = max(len(agents), 1)
        results = []
        context = s["prompt"]

        for idx, agent in enumerate(agents, start=1):
            try:
                chained_prompt = (
                    "Build on the evolving conference discussion below.\n\n"
                    "=== Current context ===\n"
                    f"{context}\n\n"
                    "=== Your task ===\n"
                    "Add the next best contribution (concise but substantive)."
                )
                out = _call_openrouter(agent["model"], chained_prompt)
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": out,
                    "error": None
                })
                context += f"\n\n[{agent['name']}]: {out}"
            except Exception as e:
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": None,
                    "error": str(e)
                })
            s["progress"] = int(idx * 100 / total)

        _complete_session(session_id, results)

    except Exception as e:
        _error_session(session_id, str(e))


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
    threading.Thread(
        target=_run_expert_panel, args=(session["id"],), daemon=True
    ).start()

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
    threading.Thread(
        target=_run_conference_chain, args=(session["id"],), daemon=True
    ).start()

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
            items.append(
                f"<li><b>{r['agent']}</b> ({r['model']}): "
                f"<span style='color:#ff9aa2'>ERROR: {r['error']}</span></li>"
            )
        else:
            items.append(
                f"<li><b>{r['agent']}</b> ({r['model']}): {r['response']}</li>"
            )

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Revolutionary Relay Report</title>
      </head>
      <body style="font-family:Arial; background:#0a0f1c; color:#e8f6ff; padding:24px;">
        <h1>Session Report</h1>
        <p><b>Session ID:</b> {session_id}</p>
        <p><b>Status:</b> {s['status']}</p>
        <p><b>Mode:</b> {s['mode']}</p>
        <p><b>Prompt:</b> {s['prompt']}</p>
        <p><b>Progress:</b> {s.get('progress', 0)}%</p>
        <h2>Results</h2>
        <ul>{''.join(items)}</ul>
      </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
