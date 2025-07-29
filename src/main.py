import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from datetime import datetime

# Import all route blueprints (enhanced system)
from routes.agents import agents_bp
from routes.human_simulator import human_simulator_bp
from routes.revolutionary_relay import revolutionary_relay_bp
from routes.payments import payments_bp
from routes.ai_pair_system import ai_pair_system_bp
from routes.conference_system import conference_system_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'unitylab-ultimate-orchestration-engine-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS for frontend integration
CORS(app, origins=[
    'http://localhost:3000',
    'https://lucky-kheer-f8d0d3.netlify.app',
    'https://thepromptlink.com',
    'https://thepromptlink.netlify.app',
    'https://singular-bunny-82fc57.netlify.app',
    'https://incomparable-cascaron-dd9815.netlify.app',
    'https://effervescent-pothos-4fbe1c.netlify.app',
    'https://jazzy-shortbread-e3aee3.netlify.app',
    'https://dancing-meerkat-41c610.netlify.app',
    'https://helpful-jalebi-df5d7d.netlify.app',
    'https://superlative-gecko-f59930.netlify.app'
], allow_headers=['Content-Type', 'Authorization', 'x-user-id'])

# Register all blueprints (FIXED URL PREFIXES)
app.register_blueprint(agents_bp, url_prefix='/api/agents')
app.register_blueprint(human_simulator_bp, url_prefix='/api/human-simulator')
app.register_blueprint(revolutionary_relay_bp, url_prefix='/api/revolutionary-relay')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(ai_pair_system_bp, url_prefix='/api/repair-system')  # Fixed: repair-system instead of ai-pair-system
app.register_blueprint(conference_system_bp, url_prefix='/api/conference-system')

# Legacy endpoints for backward compatibility
@app.route('/api/chat', methods=['POST'])
def legacy_chat():
    """Legacy chat endpoint - redirects to agents API"""
    from flask import request
    try:
        data = request.get_json()
        agent_id = data.get('agent', 'gpt-4o')  # Default to GPT-4o
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Forward to unified agents API
        import requests
        response = requests.post(
            f"{request.host_url}api/agents/chat",
            json={'agent_id': agent_id, 'message': message}
        )
        return response.json()
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
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
        'timestamp': datetime.utcnow().isoformat()
    })

# Root endpoint
@app.route('/', methods=['GET'])
def root():
    return send_from_directory(app.static_folder, 'index.html')

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Error handlers
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("🚀 UnityLab Enhanced Backend - AI Collaboration on Autopilot")
    print("🌟 Features: Human Simulator + Repair System + Conference System")
    print(f"🤖 Total AI Agents: 20")
    print(f"🧠 Human Simulator: AI clone development")
    print(f"🔧 Repair System: AI debugging and repair")
    print(f"🏛️ Conference System: Multi-agent orchestration")
    print(f"💳 Payment Tiers: Free ($0), Basic ($19), Pro ($99), Expert ($499)")
    print(f"🔗 Port: {port}")
    print("🏆 READY FOR ULTIMATE AI COLLABORATION!")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
