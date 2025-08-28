import os
import sys
from datetime import datetime, timezone

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS, cross_origin

# --- Keep your original path insert (important for routes package imports) ---
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# --- Import blueprints ---
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

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unitylab-ultimate-orchestration-engine-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f"sqlite:///{os.path.join(BASE_DIR, 'database', 'app.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------------------------------------------------------------------
# CORS â permissive for /api/* (tighten later if needed)
# ----------------------------------------------------------------------------
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "x-user-id"],
    expose_headers=["Content-Type"]
)

# Convenience kwargs for @cross_origin usage
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
# Historical compatibility: keep ai_pair_system mounted at /api/repair-system
app.register_blueprint(ai_pair_system_bp, url_prefix='/api/repair-system')
app.register_blueprint(conference_system_bp, url_prefix='/api/conference-system')

# ----------------------------------------------------------------------------
# Legacy compatibility endpoint
# ----------------------------------------------------------------------------
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@cross_origin(**CORS_ALLOW_KW)
def legacy_chat():
    """Legacy chat endpoint - forwards to /api/agents/chat"""
    try:
        data = request.get_json(silent=True) or {}
        agent_id = data.get('agent') or data.get('agent_id') or 'gpt-4o'
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Forward to unified agents API (absolute URL ensures proxy friendliness)
        import requests
        target = f"{request.host_url.rstrip('/')}/api/agents/chat"
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
# Static / root
# ----------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def root():
    # Serve your front-end entry (index.html) from static/
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Map common top-level assets that your front-end expects
@app.route('/logo.png')
def serve_logo():
    return send_from_directory(app.static_folder, 'logo.png')

@app.route('/favicon.ico')
def serve_favicon():
    # Optional if you have one; if missing this will 404 harmlessly
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
# Entrypoint
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # Railway provides $PORT; default to 8080 to match your logs if not set
    port = int(os.environ.get('PORT', '8080'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print("ð UnityLab Enhanced Backend - AI Collaboration on Autopilot")
    print("ð Features: Human Simulator + Repair System + Conference System")
    print(f"ð¤ Total AI Agents: 20")
    print(f"ð§  Human Simulator: AI clone development")
    print(f"ð§ Repair System: AI debugging and repair")
    print(f"ðï¸ Conference System: Multi-agent orchestration")
    print(f"ð³ Payment Tiers: Free ($0), Basic ($19), Pro ($99), Expert ($499)")
    print(f"ð Port: {port}")
    print("ð READY FOR ULTIMATE AI COLLABORATION!")

    # Flask dev server (okay on Railway for quick testing; swap to gunicorn for prod)
    app.run(host='0.0.0.0', port=port, debug=debug)
