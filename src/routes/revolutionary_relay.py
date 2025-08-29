# routes/revolutionary_relay.py
import uuid
import logging
import threading
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import requests

# In-memory session store (replace with DB later if needed)
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
        "mode": mode,  # expert_panel or conference_chain
        "status": "queued",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "error": None,
    }
    SESSIONS[session_id] = session
    return session


def _call_agent(model: str, prompt: str):
    """
    Calls the /api/agents/chat endpoint for a given model.
    Falls back to mock if call fails.
    """
    try:
        response = requests.post(
            "http://localhost:5000/api/agents/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("output") or data.get("content") or str(data)
        else:
            return f"[error] Agent {model} failed with {response.status_code}"
    except Exception as e:
        return f"[mock] {model} responding to: {prompt} ({e})"


def _run_expert_panel(session_id: str, prompt: str, pairs: int = 10):
    """Run expert panel with N pairs (2 agents per pair)."""
    if session_id not in SESSIONS:
        return
    session = SESSIONS[session_id]
    session["status"] = "running"

    # Example agents list
    agent_models = [
        "openai/gpt-4o",
        "deepseek/deepseek-r1",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.0-flash-exp",
        "cohere/command-r-plus",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-large",
        "qwen/qwen-2.5-72b-instruct",
        "perplexity/llama-3.1-sonar-huge-128k-online",
        "openai/gpt-4-turbo"
    ]

    results = []
    total_agents = pairs * 2
    for i in range(total_agents):
        model = agent_models[i % len(agent_models)]
        result = _call_agent(model, prompt)
        results.append({"agent": model, "response": result})
        session["progress"] = int((i + 1) / total_agents * 100)

    session["results"] = results
    session["status"] = "completed"
    session["completed_at"] = datetime.now(timezone.utc).isoformat()


def _run_conference_chain(session_id: str, prompt: str, rounds: int = 20):
    """Run sequential chain of agents, passing context each round."""
    if session_id not in SESSIONS:
        return
    session = SESSIONS[session_id]
    session["status"] = "running"

    agent_models = [
        "openai/gpt-4o",
        "deepseek/deepseek-r1",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.0-flash-exp",
        "cohere/command-r-plus",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-large",
        "qwen/qwen-2.5-72b-instruct",
    ]

    context = prompt
    results = []
    for i in range(rounds):
        model = agent_models[i % len(agent_models)]
        result = _call_agent(model, context)
        results.append({"round": i + 1, "agent": model, "response": result})
        context = f"{context}\n\nAgent {model} said:\n{result}"
        session["progress"] = int((i + 1) / rounds * 100)

    session["results"] = results
    session["status"] = "completed"
    session["completed_at"] = datetime.now(timezone.utc).isoformat()


# --- Endpoints ---
@revolutionary_relay_bp.route("/start-expert-panel", methods=["POST"])
@cross_origin()
def start_expert_panel():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    pairs = int(data.get("pairs", 10))
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    session = _new_session(prompt, "expert_panel")
    threading.Thread(target=_run_expert_panel, args=(session["session_id"], prompt, pairs)).start()

    return jsonify({
        "session_id": session["session_id"],
        "status": "started",
        "mode": "expert_panel"
    }), 200


@revolutionary_relay_bp.route("/start-conference-chain", methods=["POST"])
@cross_origin()
def start_conference_chain():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    rounds = int(data.get("rounds", 20))
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    session = _new_session(prompt, "conference_chain")
    threading.Thread(target=_run_conference_chain, args=(session["session_id"], prompt, rounds)).start()

    return jsonify({
        "session_id": session["session_id"],
        "status": "started",
        "mode": "conference_chain"
    }), 200


@revolutionary_relay_bp.route("/session-status/<session_id>", methods=["GET"])
@cross_origin()
def session_status(session_id):
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "status": session["status"],
        "progress": session.get("progress", 0),
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
            {''.join(f"<li><b>{r.get('agent','Round '+str(r.get('round')))}</b>: {r['response']}</li>" for r in session['results'])}
        </ul>
    </body>
    </html>
    """
    return html, 200, {"Content-Type": "text/html"}
