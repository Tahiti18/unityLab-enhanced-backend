# routes/revolutionary_relay.py
import uuid
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin

# In-memory session store (can be swapped for DB later)
SESSIONS = {}

# Blueprint
revolutionary_relay_bp = Blueprint("revolutionary_relay", __name__)

# Logger
logger = logging.getLogger("revolutionary_relay")
logger.setLevel(logging.INFO)


# --- Helpers ---
def _new_session(prompt: str, mode: str):
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "prompt": prompt,
        "mode": mode,  # "expert_panel" or "conference_chain"
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "error": None,
    }
    SESSIONS[session_id] = session
    logger.info(f"[RevolutionaryRelay] Started session {session_id} in mode={mode}")
    return session


def _mock_agent_run(prompt: str, mode: str):
    """
    TODO: Replace with actual multi-agent orchestration.
    For now, simulates results from 3 agents.
    """
    return [
        {
            "agent": "gpt-4o",
            "response": f"[{mode}] GPT-4o response to: {prompt}"
        },
        {
            "agent": "deepseek-r1",
            "response": f"[{mode}] DeepSeek-R1 perspective: {prompt}"
        },
        {
            "agent": "claude-3.5",
            "response": f"[{mode}] Claude-3.5 analysis of: {prompt}"
        },
    ]


def _complete_session(session_id: str, results: list):
    if session_id not in SESSIONS:
        return
    SESSIONS[session_id]["results"] = results
    SESSIONS[session_id]["status"] = "completed"
    SESSIONS[session_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"[RevolutionaryRelay] Completed session {session_id}")


# --- Endpoints ---
@revolutionary_relay_bp.route("/start-expert-panel", methods=["POST", "OPTIONS"])
@cross_origin()
def start_expert_panel():
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Missing 'prompt'"}), 400

        session = _new_session(prompt, "expert_panel")
        results = _mock_agent_run(prompt, "expert_panel")
        _complete_session(session["session_id"], results)

        return jsonify({
            "session_id": session["session_id"],
            "status": "started",
            "mode": "expert_panel"
        }), 200
    except Exception as e:
        logger.exception("Failed to start expert panel")
        return jsonify({"error": str(e)}), 500


@revolutionary_relay_bp.route("/start-conference-chain", methods=["POST", "OPTIONS"])
@cross_origin()
def start_conference_chain():
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Missing 'prompt'"}), 400

        session = _new_session(prompt, "conference_chain")
        results = _mock_agent_run(prompt, "conference_chain")
        _complete_session(session["session_id"], results)

        return jsonify({
            "session_id": session["session_id"],
            "status": "started",
            "mode": "conference_chain"
        }), 200
    except Exception as e:
        logger.exception("Failed to start conference chain")
        return jsonify({"error": str(e)}), 500


@revolutionary_relay_bp.route("/session-status/<session_id>", methods=["GET"])
@cross_origin()
def session_status(session_id):
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": session["status"],
        "created_at": session["created_at"],
        "completed_at": session.get("completed_at"),
    }), 200


@revolutionary_relay_bp.route("/session-results/<session_id>", methods=["GET"])
@cross_origin()
def session_results(session_id):
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": session["status"],
        "results": session["results"],
        "error": session.get("error"),
    }), 200


@revolutionary_relay_bp.route("/generate-html-report/<session_id>", methods=["GET"])
@cross_origin()
def generate_html_report(session_id):
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    html = f"""
    <html>
    <head><title>Revolutionary Relay Report</title></head>
    <body style='font-family:Arial; background:#0a0f1c; color:white; padding:20px;'>
        <h1>Session Report</h1>
        <p><b>Session ID:</b> {session_id}</p>
        <p><b>Status:</b> {session['status']}</p>
        <p><b>Mode:</b> {session['mode']}</p>
        <p><b>Prompt:</b> {session['prompt']}</p>
        <h2>Results</h2>
        <ul>
            {''.join(f"<li><b>{r['agent']}</b>: {r['response']}</li>" for r in session['results'])}
        </ul>
    </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
