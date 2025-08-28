import os
import sys
from datetime import datetime, timezone

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS, cross_origin

# DON'T CHANGE THIS !!! (kept from your original)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# --- Import blueprints (your existing routes) ---
from routes.agents import agents_bp
from routes.human_simulator import human_simulator_bp
from routes.revolutionary_relay import revolutionary_relay_bp
from routes.payments import payments_bp
from routes.ai_pair_system import ai_pair_system_bp
from routes.conference_system import conference_system_bp

# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)

# Config (unchanged)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unitylab-ultimate-orchestration-engine-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'database', 'app.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------------------------------------------------------------------
# CORS â robust defaults so frontend can POST without preflight failure
# ----------------------------------------------------------------------------
# Easiest, unblock-now setting: allow all origins for /api/* (you can tighten later)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-user-id"],
    expose_headers=["Content-Type"]
)

# If you prefer an allowlist instead of '*', replace above with e.g.:
# CORS(app, resources={r"/api/*": {"origins": [
#     "https://unitylab.io",
#     "https://*.unitylab.io",
#     "https://*.netlify.app",
#     "http://localhost:3000"
# ]}}, methods=["GET","POST","OPTIONS"], allow_headers=[...])

# Convenience kwargs if you want to add @cross_origin on specific routes
CORS_ALLOW_KW = dict(
    origins="*",
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-user-id"]
)

# ----------------------------------------------------------------------------
# Register blueprints (kept as in your current backend)
# ----------------------------------------------------------------------------
app.register_blueprint(agents_bp, url_prefix='/api/agents')
app.register_blueprint(human_simulator_bp, url_prefix='/api/human-simulator')
app.register_blueprint(revolutionary_relay_bp, url_prefix='/api/revolutionary-relay')
app.register_blueprint(payments_bp, url_prefix='/api/payments')

# NOTE: You previously mounted the pair system under '/api/repair-system' for compatibility.
# Keeping it unchanged so existing frontend calls don't break.
app.register_blueprint(ai_pair_system_bp, url_prefix='/api/repair-system')

app.register_blueprint(conference_system_bp, url_prefix='/api/conference-system')

# ----------------------------------------------------------------------------
# Legacy compatibility endpoint
# ----------------------------------------------------------------------------
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@cross_origin(**CORS_ALLOW_KW)
def legacy_chat():
    """Legacy chat endpoint - redirects to agents API"""
    try:
        data = request.get_json(silent=True) or {}
        agent_id = data.get('agent') or data.get('agent_id') or 'gpt-4o'
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Forward to unified agents API (absolute URL so it works behind proxies)
        import requests
        target = f"{request.host_url.rstrip('/')}/api/agents/chat"
        resp = requests.post(target, json={'agent_id': agent_id, 'message': message}, timeout=60)

        try:
            payload = resp.json()
        except Exception:
            payload = {'error': 'Upstream did not return JSON', 'status': resp.status_code, 'text': resp.text}
        return jsonify(payload), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'UnityLab Enhanced Backend',
        'version': '4.0.0',
        'features': {
            'agents': '20 AI agents available',
            'human_simulator': 'AI clone development system',
            'revolutionary_relay': 'Expert Panel + Conference Chain modes',
            'repair_system': 'AI debugging and repair functionality',
            'conference_system': 'Multi-agent conference orchestration',
            'payments': 'Stripe integration with 4 tiers'
        },
        'enhanced_features': [
            'AI Repair System: Debug and fix code/content automatically',
            'Conference System: Orchestrate complex multi-agent discussions',
            'Human Simulator: Advanced AI clone development',
            'Expert Panel Mode: 10 independent agent pairs',
            'Conference Chain Mode: 20 agents with context',
            'Real-time collaboration and synthesis'
        ],
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

# ----------------------------------------------------------------------------
# Static / SPA root
# ----------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def root():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

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
            '/health'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Please check logs for details'
    }), 500

# Add permissive CORS headers on every response (belt & suspenders)
@app.after_request
def add_cors_headers(resp):
    resp.headers.setdefault('Access-Control-Allow-Origin', '*')
    resp.headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    resp.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, x-user-id')
    return resp

# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # Use PORT=8080 by default (matches your logs)
    port = int(os.environ.get('PORT', '8080'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower()
