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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# In-memory session store (swap for DB if needed)
# {
#   id, prompt, mode, status, created_at, completed_at, progress,
#   config: {...}, results: [{agent, model, response, error}], error
# }
SESSIONS: dict[str, dict] = {}

# Fallback if agents endpoint can’t be read
FALLBACK_AGENTS = [
    {"name": "GPT-4o",        "model": "openai/gpt-4o"},
    {"name": "Claude 3.5",    "model": "anthropic/claude-3.5-sonnet"},
    {"name": "DeepSeek R1",   "model": "deepseek/deepseek-r1"},
]

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _new_session(prompt: str, mode: str, config: dict) -> dict:
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "prompt": prompt,
        "mode": mode,  # "expert_panel" | "conference_chain"
        "status": "running",
        "created_at": _utc_now(),
        "completed_at": None,
        "progress": 0,
        "config": config or {},
        "results": [],
        "error": None,
    }
    SESSIONS[sid] = session
    logger.info(f"[Relay] session started id={sid} mode={mode} cfg={config}")
    return session

def _complete_session(session_id: str, results: list):
    s = SESSIONS.get(session_id)
    if not s:
        return
    s["results"] = results
    s["status"] = "completed"
    s["completed_at"] = _utc_now()
    s["progress"] = 100
    logger.info(f"[Relay] session completed id={session_id} results={len(results)}")

def _error_session(session_id: str, message: str):
    s = SESSIONS.get(session_id)
    if not s:
        return
    s["status"] = "error"
    s["error"] = message
    s["completed_at"] = _utc_now()
    logger.error(f"[Relay] session error id={session_id}: {message}")

def _fetch_active_agents(base_url: str) -> list[dict]:
    """
    Load active agents from your own backend (server-to-server).
    Falls back to 3 defaults if unreachable or empty.
    """
    try:
        url = f"{base_url.rstrip('/')}/api/agents/list"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        agents_dict = data.get("agents", {})
        active = []
        for key, v in agents_dict.items():
            if v.get("active"):
                active.append({
                    "name": v.get("name", key),
                    "model": v.get("model"),
                })
        if active:
            return active
        logger.warning("[Relay] /api/agents/list returned no active agents; using fallback.")
        return FALLBACK_AGENTS
    except Exception as e:
        logger.warning(f"[Relay] could not load /api/agents/list: {e}; using fallback.")
        return FALLBACK_AGENTS

def _call_openrouter(model: str, prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing in environment.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

# -----------------------------------------------------------------------------
# Workers (run in background threads)
# -----------------------------------------------------------------------------
def _run_expert_panel(session_id: str, base_url: str, max_pairs: int):
    """
    Run A↔B style independent pairs. We just collect single responses
    per agent for now (use your own debate logic if you want back-and-forth).
    """
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _fetch_active_agents(base_url)
        # Use first 2 * max_pairs agents (cap by available)
        slice_n = min(len(agents), max(1, max_pairs) * 2)
        agents = agents[:slice_n]

        results = []
        total = len(agents)
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
            s["progress"] = int(idx * 100 / max(total, 1))
        _complete_session(session_id, results)
    except Exception as e:
        _error_session(session_id, str(e))

def _run_conference_chain(session_id: str, base_url: str, max_agents: int):
    """
    Sequential chain where each agent builds on an evolving context.
    """
    s = SESSIONS.get(session_id)
    if not s:
        return
    try:
        agents = _fetch_active_agents(base_url)
        # Use first max_agents agents (cap at available, up to 30)
        max_agents = min(max(1, int(max_agents)), 30)
        agents = agents[:max_agents]

        running_context = s["prompt"]
        results = []
        total = len(agents)
        for idx, agent in enumerate(agents, start=1):
            try:
                prompt = (
                    "Build on the conference discussion below.\n\n"
                    f"=== Current context ===\n{running_context}\n\n"
                    "=== Your task ===\nAdd the next best contribution. Be substantive, concise, and avoid repetition."
                )
                out = _call_openrouter(agent["model"], prompt)
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": out,
                    "error": None
                })
                running_context += f"\n\n[{agent['name']}]: {out}"
            except Exception as e:
                results.append({
                    "agent": agent["name"],
                    "model": agent["model"],
                    "response": None,
                    "error": str(e)
                })
            s["progress"] = int(idx * 100 / max(total, 1))
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
    max_pairs = int(data.get("max_pairs", 10))  # default 10 pairs (20 agents)
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    base_url = request.host_url.rstrip("/")  # capture BEFORE thread starts
    session = _new_session(prompt, "expert_panel", {"max_pairs": max_pairs})
    threading.Thread(
        target=_run_expert_panel,
        args=(session["id"], base_url, max_pairs),
        daemon=True
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
    max_agents = int(data.get("max_agents", data.get("maxAgents", 20)))  # default 20, cap 30
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    base_url = request.host_url.rstrip("/")
    session = _new_session(prompt, "conference_chain", {"max_agents": max_agents})
    threading.Thread(
        target=_run_conference_chain,
        args=(session["id"], base_url, max_agents),
        daemon=True
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
        "config": s.get("config", {}),
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
        "config": s.get("config", {}),
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
                f"<span style='color:#f88'>ERROR: {r['error']}</span></li>"
            )
        else:
            items.append(
                f"<li><b>{r['agent']}</b> ({r['model']}): {r['response']}</li>"
            )

    html = f"""
    <html>
      <head>
        <title>Session Report</title>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: Arial; background:#0a0f1c; color:#e8f6ff; padding:24px; }}
          h1, h2 {{ color:#9be1ff; }}
          .kv span {{ display:inline-block; margin-right:16px; }}
          ul {{ line-height:1.5 }}
        </style>
      </head>
      <body>
        <h1>Session Report</h1>
        <div class="kv">
          <span><b>Session ID:</b> {session_id}</span>
          <span><b>Status:</b> {s['status']}</span>
          <span><b>Mode:</b> {s['mode']}</span>
          <span><b>Progress:</b> {s.get('progress',0)}%</span>
        </div>
        <p><b>Prompt:</b> {s['prompt']}</p>
        <h2>Results</h2>
        <ul>{''.join(items)}</ul>
      </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
