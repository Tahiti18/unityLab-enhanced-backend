import os
import sys
from datetime import datetime, timezone

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS, cross_origin

# Ensure imports like: from routes.x import blueprint
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# --- Blueprints you already have ---
from routes.agents import agents_bp
from routes.human_simulator import human_simulator_bp
from routes.revolutionary_relay import revolutionary_relay_bp
from routes.payments import payments_bp
from routes.ai_pair_system import ai_pair_system_bp
from routes.conference_system import conference_system_bp

# --- NEW: Advanced pipelines (10 Pairs + Conference Chain) ---
try:
    from routes.pipelines import pipelines_bp  # new file below
except Exception:
    pipelines_bp = None

# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unitylab-ultimate-orchestration-engine-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f"sqlite:///{os.path.join(BASE_DIR, 'database', 'app.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------------------------------------------------------------------
# CORS — permissive for /api/* (tighten later)
# ----------------------------------------------------------------------------
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-user-id"],
    expose_headers=["Content-Type"]
)
CORS_ALLOW_KW = dict(
    origins="*",
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-user-id"]
)

# ----------------------------------------------------------------------------
# Register blueprints
# ----------------------------------------------------------------------------
app.register_blueprint(agents_bp, url_prefix='/api/agents')
app.register_blueprint(human_simulator_bp, url_prefix='/api/human-simulator')
app.register_blueprint(revolutionary_relay_bp, url_prefix='/api/revolutionary-relay')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
# Historical compatibility
app.register_blueprint(ai_pair_system_bp, url_prefix='/api/repair-system')
app.register_blueprint(conference_system_bp, url_prefix='/api/conference-system')

# NEW: real endpoints for the advanced modes
if pipelines_bp:
    app.register_blueprint(pipelines_bp, url_prefix="")
# This exposes:
#   POST /api/pipelines/pairs-run
#   POST /api/pipelines/chain-run

# ----------------------------------------------------------------------------
# Legacy compatibility endpoint
# ----------------------------------------------------------------------------
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@cross_origin(**CORS_ALLOW_KW)
def legacy_chat():
    """Legacy chat endpoint - forwards to /api/agents/chat on same host."""
    try:
        data = request.get_json(silent=True) or {}
        agent_id = data.get('agent') or data.get('agent_id') or 'gpt-5'
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Use relative path to avoid scheme/host issues behind proxies
        import requests
        target = request.host_url.rstrip('/') + '/api/agents/chat'
        upstream = requests.post(target, json={'agent_id': agent_id, 'message': message}, timeout=60)
        try:
            payload = upstream.json()
        except Exception:
            payload = {'error': 'Upstream did not return JSON', 'status': upstream.status_code, 'text': upstream.text}
        return jsonify(payload), upstream.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    features = {
        'agents': '20 AI agents available',
        'human_simulator': 'AI clone development system',
        'revolutionary_relay': 'Expert Panel + Conference Chain modes',
        'repair_system': 'AI debugging and repair functionality',
        'conference_system': 'Multi-agent conference orchestration',
        'payments': 'Stripe integration with 4 tiers',
        'pipelines': bool(pipelines_bp)
    }
    return jsonify({
        'status': 'healthy',
        'service': 'UnityLab Enhanced Backend',
        'version': '4.1.0',
        'features': features,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

# ----------------------------------------------------------------------------
# Static / root
# ----------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def root():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/logo.png')
def serve_logo():
    return send_from_directory(app.static_folder, 'logo.png')

@app.route('/favicon.ico')
def serve_favicon():
    try:
        return send_from_directory(app.static_folder, 'favicon.ico')
    except Exception:
        return ('', 204)

# ----------------------------------------------------------------------------
# Error handlers
# ----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/api/agents',
            '/api/human-simulator',
            '/api/revolutionary-relay',
            '/api/repair-system',
            '/api/conference-system',
            '/api/payments',
            '/api/pipelines/pairs-run',
            '/api/pipelines/chain-run',
            '/health'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Please check logs for details'
    }), 500

# Add permissive CORS headers on every response
@app.after_request
def add_cors_headers(resp):
    resp.headers.setdefault('Access-Control-Allow-Origin', '*')
    resp.headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    resp.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, x-user-id')
    return resp

# ----------------------------------------------------------------------------
# Entrypoint for local dev; Railway will use Gunicorn via Procfile
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print("🚀 UnityLab Enhanced Backend - AI Collaboration on Autopilot")
    print("⭐ Features: Human Simulator + Repair System + Conference System + Pipelines")
    print("🤖 Total AI Agents: 20")
    print(f"🔗 Port: {port}")

    app.run(host='0.0.0.0', port=port, debug=debug)
