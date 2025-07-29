from flask import Blueprint, request, jsonify
import requests
import os
import json
import uuid
from datetime import datetime
import sqlite3
import threading
import time

revolutionary_relay_bp = Blueprint('revolutionary_relay', __name__)

# Session storage
active_sessions = {}

# Agent configuration (same as agents.py but organized for relay)
RELAY_AGENTS = [
    # Current working 10 agents
    {'id': 'gpt-4o', 'name': 'GPT-4o', 'model': 'openai/gpt-4o', 'specialty': 'Strategic Analysis'},
    {'id': 'chatgpt-4-turbo', 'name': 'ChatGPT 4 Turbo', 'model': 'openai/gpt-4-turbo', 'specialty': 'Business Strategy'},
    {'id': 'deepseek-r1', 'name': 'DeepSeek R1', 'model': 'deepseek/deepseek-r1', 'specialty': 'Technical Expert'},
    {'id': 'meta-llama-3.3', 'name': 'Meta Llama 3.3', 'model': 'meta-llama/llama-3.3-70b-instruct', 'specialty': 'Creative Analysis'},
    {'id': 'mistral-large', 'name': 'Mistral Large', 'model': 'mistralai/mistral-large', 'specialty': 'Analytical Processing'},
    {'id': 'gemini-2.0-flash', 'name': 'Gemini 2.0 Flash', 'model': 'google/gemini-2.0-flash-exp', 'specialty': 'Creative Synthesis'},
    {'id': 'perplexity-pro', 'name': 'Perplexity Pro', 'model': 'perplexity/llama-3.1-sonar-huge-128k-online', 'specialty': 'Research Expert'},
    {'id': 'gemini-pro-1.5', 'name': 'Gemini Pro 1.5', 'model': 'google/gemini-pro-1.5', 'specialty': 'Document Analysis'},
    {'id': 'command-r-plus', 'name': 'Command R+', 'model': 'cohere/command-r-plus', 'specialty': 'Enterprise Solutions'},
    {'id': 'qwen-2.5-72b', 'name': 'Qwen 2.5 72B', 'model': 'qwen/qwen-2.5-72b-instruct', 'specialty': 'Multilingual Expert'},
    
    # Additional 10 revolutionary agents
    {'id': 'llama-3.3-70b', 'name': 'Llama 3.3 70B', 'model': 'meta-llama/llama-3.3-70b-instruct', 'specialty': 'Logical Reasoning'},
    {'id': 'mixtral-8x22b', 'name': 'Mixtral 8x22B', 'model': 'mistralai/mixtral-8x22b-instruct', 'specialty': 'System Design'},
    {'id': 'yi-large', 'name': 'Yi Large', 'model': '01-ai/yi-large', 'specialty': 'Innovation Expert'},
    {'id': 'nous-hermes-3', 'name': 'Nous Hermes 3', 'model': 'nousresearch/hermes-3-llama-3.1-405b', 'specialty': 'Free Thinking'},
    {'id': 'wizardlm-2', 'name': 'WizardLM 2', 'model': 'microsoft/wizardlm-2-8x22b', 'specialty': 'Mathematical Reasoning'},
    {'id': 'dolphin-mixtral', 'name': 'Dolphin Mixtral', 'model': 'cognitivecomputations/dolphin-2.9-llama3-70b', 'specialty': 'Bold Synthesis'},
    {'id': 'openhermes-2.5', 'name': 'OpenHermes 2.5', 'model': 'teknium/openhermes-2.5-mistral-7b', 'specialty': 'Collaboration Expert'},
    {'id': 'starling-7b', 'name': 'Starling 7B', 'model': 'berkeley-nest/starling-lm-7b-alpha', 'specialty': 'Quick Insights'},
    {'id': 'neural-chat', 'name': 'Neural Chat', 'model': 'intel/neural-chat-7b-v3-3', 'specialty': 'Dialogue Expert'},
    {'id': 'zephyr-beta', 'name': 'Zephyr Beta', 'model': 'huggingfaceh4/zephyr-7b-beta', 'specialty': 'Final Synthesis'}
]

def call_openrouter_api(agent, message):
    """Call OpenRouter API for specific agent"""
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://thepromptlink.netlify.app',
                'X-Title': 'PromptLink Revolutionary AI Relay'
            },
            json={
                'model': agent['model'],
                'messages': [
                    {
                        'role': 'system',
                        'content': f'You are {agent["name"]}, specializing in {agent["specialty"]}. Provide insightful, collaborative responses that build upon previous insights when available.'
                    },
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                'max_tokens': 2000,
                'temperature': 0.7
            }
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"API Error: {str(e)}"

def expert_panel_worker(session_id, prompt):
    """Worker function for Expert Panel Mode (10 pairs)"""
    session = active_sessions[session_id]
    session['status'] = 'running'
    session['results'] = []
    
    # Create 10 pairs from 20 agents
    pairs = []
    for i in range(0, 20, 2):
        pairs.append([RELAY_AGENTS[i], RELAY_AGENTS[i+1]])
    
    session['total_pairs'] = len(pairs)
    
    for pair_index, pair in enumerate(pairs):
        if session.get('status') == 'stopped':
            break
            
        session['current_pair'] = pair_index + 1
        session['current_agents'] = [pair[0]['name'], pair[1]['name']]
        
        # Agent A responds to prompt
        agent_a_response = call_openrouter_api(pair[0], prompt)
        
        # Agent B responds to prompt (independent analysis)
        agent_b_response = call_openrouter_api(pair[1], prompt)
        
        # Store pair results
        pair_result = {
            'pair_number': pair_index + 1,
            'agent_a': {
                'name': pair[0]['name'],
                'specialty': pair[0]['specialty'],
                'response': agent_a_response
            },
            'agent_b': {
                'name': pair[1]['name'],
                'specialty': pair[1]['specialty'],
                'response': agent_b_response
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        session['results'].append(pair_result)
        
        # Small delay between pairs
        time.sleep(1)
    
    session['status'] = 'completed'
    session['completed_at'] = datetime.utcnow().isoformat()

def conference_chain_worker(session_id, prompt, max_agents=20):
    """Worker function for Conference Chain Mode (sticky context)"""
    session = active_sessions[session_id]
    session['status'] = 'running'
    session['results'] = []
    session['sticky_context'] = prompt
    
    session['total_agents'] = min(max_agents, len(RELAY_AGENTS))
    
    for agent_index in range(session['total_agents']):
        if session.get('status') == 'stopped':
            break
            
        agent = RELAY_AGENTS[agent_index]
        session['current_agent'] = agent_index + 1
        session['current_agent_name'] = agent['name']
        
        # Create message with sticky context
        if agent_index == 0:
            # First agent gets original prompt
            message = prompt
        else:
            # Subsequent agents get original prompt + latest response
            latest_response = session['results'][-1]['response']
            message = f"ORIGINAL PROMPT: {prompt}\n\nPREVIOUS INSIGHT: {latest_response}\n\nBuild upon this insight with your expertise:"
        
        # Get agent response
        agent_response = call_openrouter_api(agent, message)
        
        # Store result
        result = {
            'agent_number': agent_index + 1,
            'agent_name': agent['name'],
            'agent_specialty': agent['specialty'],
            'response': agent_response,
            'sticky_context_used': agent_index > 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        session['results'].append(result)
        
        # Small delay between agents
        time.sleep(1)
    
    session['status'] = 'completed'
    session['completed_at'] = datetime.utcnow().isoformat()

@revolutionary_relay_bp.route('/start-expert-panel', methods=['POST'])
def start_expert_panel():
    """Start Expert Panel Mode (10 pairs working independently)"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'status': 'error', 'message': 'Prompt is required'}), 400
        
        session_id = str(uuid.uuid4())
        
        # Initialize session
        active_sessions[session_id] = {
            'mode': 'expert_panel',
            'prompt': prompt,
            'status': 'starting',
            'created_at': datetime.utcnow().isoformat(),
            'current_pair': 0,
            'total_pairs': 10,
            'current_agents': ['Initializing...', 'Waiting...']
        }
        
        # Start worker thread
        worker_thread = threading.Thread(
            target=expert_panel_worker,
            args=(session_id, prompt)
        )
        worker_thread.daemon = True
        worker_thread.start()
        
        return jsonify({
            'status': 'started',
            'session_id': session_id,
            'mode': 'expert_panel',
            'total_pairs': 10,
            'message': 'Expert Panel Mode started - 10 pairs analyzing independently'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/start-conference-chain', methods=['POST'])
def start_conference_chain():
    """Start Conference Chain Mode (20 agents with sticky context)"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        max_agents = data.get('max_agents', 20)
        
        if not prompt:
            return jsonify({'status': 'error', 'message': 'Prompt is required'}), 400
        
        session_id = str(uuid.uuid4())
        
        # Initialize session
        active_sessions[session_id] = {
            'mode': 'conference_chain',
            'prompt': prompt,
            'status': 'starting',
            'created_at': datetime.utcnow().isoformat(),
            'current_agent': 0,
            'total_agents': min(max_agents, len(RELAY_AGENTS)),
            'current_agent_name': 'Initializing...'
        }
        
        # Start worker thread
        worker_thread = threading.Thread(
            target=conference_chain_worker,
            args=(session_id, prompt, max_agents)
        )
        worker_thread.daemon = True
        worker_thread.start()
        
        return jsonify({
            'status': 'started',
            'session_id': session_id,
            'mode': 'conference_chain',
            'total_agents': min(max_agents, len(RELAY_AGENTS)),
            'message': 'Conference Chain Mode started - agents building with sticky context'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/session-status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """Get real-time session status"""
    try:
        if session_id not in active_sessions:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        session = active_sessions[session_id]
        
        return jsonify({
            'status': 'success',
            'session_data': {
                'session_id': session_id,
                'mode': session['mode'],
                'status': session['status'],
                'current_pair': session.get('current_pair', 0),
                'total_pairs': session.get('total_pairs', 0),
                'current_agent': session.get('current_agent', 0),
                'total_agents': session.get('total_agents', 0),
                'current_agents': session.get('current_agents', []),
                'current_agent_name': session.get('current_agent_name', ''),
                'results_count': len(session.get('results', [])),
                'created_at': session['created_at'],
                'completed_at': session.get('completed_at')
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/session-results/<session_id>', methods=['GET'])
def get_session_results(session_id):
    """Get complete session results"""
    try:
        if session_id not in active_sessions:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        session = active_sessions[session_id]
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'mode': session['mode'],
            'prompt': session['prompt'],
            'results': session.get('results', []),
            'total_results': len(session.get('results', [])),
            'completed': session['status'] == 'completed',
            'created_at': session['created_at'],
            'completed_at': session.get('completed_at')
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/generate-html-report/<session_id>', methods=['GET'])
def generate_html_report(session_id):
    """Generate beautiful HTML report"""
    try:
        if session_id not in active_sessions:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        session = active_sessions[session_id]
        results = session.get('results', [])
        
        if not results:
            return jsonify({'status': 'error', 'message': 'No results to generate report'}), 400
        
        # Generate HTML report
        html_report = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PromptLink Revolutionary AI Analysis Report</title>
            <style>
                body {{ font-family: 'Playfair Display', serif; background: #0a0f1c; color: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .header h1 {{ color: #00d4aa; font-size: 2.5em; margin-bottom: 10px; }}
                .header p {{ color: #cbd5e1; font-size: 1.2em; }}
                .meta-info {{ background: rgba(15, 23, 42, 0.8); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                .result-card {{ background: rgba(15, 23, 42, 0.8); margin: 20px 0; padding: 25px; border-radius: 10px; border-left: 4px solid #00d4aa; }}
                .agent-name {{ color: #00d4aa; font-size: 1.3em; font-weight: bold; margin-bottom: 5px; }}
                .agent-specialty {{ color: #64748b; font-size: 0.9em; margin-bottom: 15px; }}
                .response {{ line-height: 1.6; color: #f8fafc; }}
                .pair-header {{ color: #00d4aa; font-size: 1.5em; margin: 30px 0 15px 0; }}
                .timestamp {{ color: #64748b; font-size: 0.8em; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Revolutionary AI Analysis Report</h1>
                    <p>PromptLink {session['mode'].replace('_', ' ').title()} Results</p>
                </div>
                
                <div class="meta-info">
                    <h3>Session Information</h3>
                    <p><strong>Mode:</strong> {session['mode'].replace('_', ' ').title()}</p>
                    <p><strong>Original Prompt:</strong> {session['prompt']}</p>
                    <p><strong>Total Results:</strong> {len(results)}</p>
                    <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
        """
        
        if session['mode'] == 'expert_panel':
            for i, result in enumerate(results):
                html_report += f"""
                <div class="pair-header">Expert Pair {result['pair_number']}</div>
                
                <div class="result-card">
                    <div class="agent-name">{result['agent_a']['name']}</div>
                    <div class="agent-specialty">{result['agent_a']['specialty']}</div>
                    <div class="response">{result['agent_a']['response']}</div>
                    <div class="timestamp">{result['timestamp']}</div>
                </div>
                
                <div class="result-card">
                    <div class="agent-name">{result['agent_b']['name']}</div>
                    <div class="agent-specialty">{result['agent_b']['specialty']}</div>
                    <div class="response">{result['agent_b']['response']}</div>
                    <div class="timestamp">{result['timestamp']}</div>
                </div>
                """
        else:  # conference_chain
            for i, result in enumerate(results):
                html_report += f"""
                <div class="result-card">
                    <div class="agent-name">Agent {result['agent_number']}: {result['agent_name']}</div>
                    <div class="agent-specialty">{result['agent_specialty']}</div>
                    <div class="response">{result['response']}</div>
                    <div class="timestamp">{result['timestamp']}</div>
                </div>
                """
        
        html_report += """
            </div>
        </body>
        </html>
        """
        
        return jsonify({
            'status': 'success',
            'html_report': html_report,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/stop-session/<session_id>', methods=['POST'])
def stop_session(session_id):
    """Stop running session"""
    try:
        if session_id not in active_sessions:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        active_sessions[session_id]['status'] = 'stopped'
        
        return jsonify({
            'status': 'success',
            'message': 'Session stopped',
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@revolutionary_relay_bp.route('/agents', methods=['GET'])
def get_relay_agents():
    """Get all 20 relay agents"""
    return jsonify({
        'status': 'success',
        'agents': RELAY_AGENTS,
        'total_agents': len(RELAY_AGENTS),
        'current_working': RELAY_AGENTS[:10],
        'revolutionary_additional': RELAY_AGENTS[10:]
    })

