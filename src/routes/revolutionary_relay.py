# src/routes/revolutionary_relay.py
import uuid
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

# -----------------------------------------------------------------------------
# In-memory session store
# -----------------------------------------------------------------------------
SESSIONS = {}

# Blueprint + logger
revolutionary_relay_bp = Blueprint("revolutionary_relay", __name__)
logger = logging.getLogger("revolutionary_relay")
logger.setLevel(logging.INFO)

# Defaults
DEFAULT_AGENTS = ["gpt-4o", "mistral-large", "deepseek-r1"]  # override via JSON body
MAX_WORKERS = 6


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _new_session(prompt: str, mode: str) -> dict:
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "prompt": prompt,
        "mode": mode,  # "expert_panel" | "conference_chain"
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "results": [],
        "error": None,
    }
    SESSIONS[session_id] = session
    logger.info(f"[RevolutionaryRelay] Started session {session_id} mode={mode}")
    return session


def _complete_session(session_id: str, results: list):
    sess = SESSIONS.get(session_id)
    if not sess:
        return
    sess["results"] = results
    sess["status"] = "completed"
    sess["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"[RevolutionaryRelay] Completed session {session_id}")


def _call_agent(base_url: str, agent_id: str, message: str) -> str:
    """
    Call our own Agents API to keep all provider logic in one place.
    Normalizes the response into a plain string.
    """
    try:
        url = f"{base_url}/api/agents/chat"
        resp = requests.post(url, json={"agent_id": agent_id, "message": message}, timeout=90)
        # Try to parse JSON; fall back to raw text
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        # Normalize common keys
        for key in ("response", "message", "text", "content", "output"):
            if isinstance(data.get(key), str):
                return data[key]

        # If provider wrapped content deeper, just return the JSON string
        return str(data)
    except Exception as e:
        logger.exception(f"Agent call failed for {agent_id}")
        return f"[ERROR from {agent_id}] {e}"


def _run_expert_panel(base_url: str, prompt: str, agents: list[str]) -> list[dict]:
    """Run agents in parallel; independent responses."""
    results = []
    with ThreadPoolExecutor(max_workers=min(len(agents), MAX_WORKERS)) as ex:
        futs = {ex.submit(_call_agent, base_url, a, prompt): a for a in agents}
        for fut in as_completed(futs):
            agent = futs[fut]
            out = fut.result()
            results.append({"agent": agent, "response": out})
    return results


def _run_conference_chain(base_url: str, prompt: str, agents: list[str]) -> list[dict]:
    """
    Sequential, sticky context: each agent sees the prompt plus a rolling
    transcript of previous agents' outputs.
    """
    results = []
    rolling_context = ""
    current_prompt = prompt

    for agent in agents:
        reply = _call_agent(base_url, agent, current_prompt)
        results.append({"agent": agent, "response": reply})

        # Update rolling context for next agent
        rolling_context += f"\n\n[{agent}] {reply}"
        current_prompt = (
            f"{prompt}\n\nPrior context from other agents:\n{rolling_context}\n\n"
            "Please build on the prior responses, avoid repeating points, "
            "and move the discussion forward with concrete insights."
        )
    return results


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@revolutionary_relay_bp.route("/start-expert-panel", methods=["POST", "OPTIONS"])
@cross_origin()
def start_expert_panel():
    """
    Body:
      { "prompt": "...", "agents": ["gpt-4o","mistral-large","deepseek-r1"]? }
    Returns (synchronously completed for simplicity):
      { session_id, status: "completed", mode, results: [...] }
    """
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Missing 'prompt'"}), 400

        agents = data.get("agents") or DEFAULT_AGENTS
        session = _new_session(prompt, "expert_panel")

        base_url = request.host_url.rstrip("/")
        results = _run_expert_panel(base_url, prompt, agents)
        _complete_session(session["session_id"], results)

        return jsonify({
            "session_id": session["session_id"],
            "status": "completed",
            "mode": "expert_panel",
            "results": results
        }), 200
    except Exception as e:
        logger.exception("Failed to run expert panel")
        return jsonify({"error": str(e)}), 500


@revolutionary_relay_bp.route("/start-conference-chain", methods=["POST", "OPTIONS"])
@cross_origin()
def start_conference_chain():
    """
    Body:
      { "prompt": "...", "agents": ["gpt-4o","mistral-large","deepseek-r1"]? }
    Returns (synchronously completed for simplicity):
      { session_id, status: "completed", mode, results: [...] }
    """
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Missing 'prompt'"}), 400

        agents = data.get("agents") or DEFAULT_AGENTS
        session = _new_session(prompt, "conference_chain")

        base_url = request.host_url.rstrip("/")
        results = _run_conference_chain(base_url, prompt, agents)
        _complete_session(session["session_id"], results)

        return jsonify({
            "session_id": session["session_id"],
            "status": "completed",
            "mode": "conference_chain",
            "results": results
        }), 200
    except Exception as e:
        logger.exception("Failed to run conference chain")
        return jsonify({"error": str(e)}), 500


@revolutionary_relay_bp.route("/session-status/<session_id>", methods=["GET"])
@cross_origin()
def session_status(session_id):
    s = SESSIONS.get(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": s["status"],
        "created_at": s["created_at"],
        "completed_at": s.get("completed_at"),
        "progress": 100 if s["status"] == "completed" else 0
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

    html = f"""
    <html>
      <head><title>Revolutionary Relay Report</title></head>
      <body style='font-family:Arial; background:#0a0f1c; color:white; padding:20px;'>
        <h1>Session Report</h1>
        <p><b>Session ID:</b> {session_id}</p>
        <p><b>Status:</b> {s['status']}</p>
        <p><b>Mode:</b> {s['mode']}</p>
        <p><b>Prompt:</b> {s['prompt']}</p>
        <h2>Results</h2>
        <ul>
          {''.join(f"<li><b>{r['agent']}</b>: {r['response']}</li>" for r in s['results'])}
        </ul>
      </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
