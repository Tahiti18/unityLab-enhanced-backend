from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime

agents_bp = Blueprint('agents', __name__)

# --- Curated, stable roster (no Anthropic, no Perplexity). OpenAI = GPT-5 only.
AGENTS = {
    # General / Aggregator
    "gpt-5": {
        "name": "GPT-5",
        "model": "openai/gpt-5",
        "group": "General",
        "active": True,
        "notes": "Primary aggregator and generalist."
    },

    # Fast / Brainstorm
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "model": "google/gemini-2.0-flash-exp",
        "group": "Fast",
        "active": True
    },

    # Reasoning / Code
    "deepseek-r1": {
        "name": "DeepSeek R1",
        "model": "deepseek/deepseek-r1",
        "group": "Reasoning",
        "active": True
    },

    # Long-context / Robust
    "mixtral-8x22b": {
        "name": "Mixtral 8x22B Instruct",
        "model": "mistralai/mixtral-8x22b-instruct",
        "group": "General",
        "active": True
    },
    "mistral-large": {
        "name": "Mistral Large",
        "model": "mistralai/mistral-large",
        "group": "General",
        "active": True
    },

    # Multilingual / Web-ish
    "qwen-2.5-72b": {
        "name": "Qwen 2.5 72B",
        "model": "qwen/qwen-2.5-72b-instruct",
        "group": "Multilingual",
        "active": True
    },

    # Creative / Friendly
    "yi-large": {
        "name": "Yi Large",
        "model": "01-ai/yi-large",
        "group": "Creative",
        "active": True
    },
    "dolphin-mixtral": {
        "name": "Dolphin Mixtral",
        "model": "openrouter/dolphin-mixtral",
        "group": "Creative",
        "active": True
    },
    "wizardlm-2": {
        "name": "WizardLM 2",
        "model": "openrouter/wizardlm-2",
        "group": "General",
        "active": True
    },
    "openhermes-2.5": {
        "name": "OpenHermes 2.5",
        "model": "teknium/openhermes-2.5",
        "group": "General",
        "active": True
    },

    # Extras you already expose in UI (kept, but easy to disable)
    "llama-3.3-70b": {
        "name": "Llama 3.3 70B",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "group": "General",
        "active": True
    },
    "starling-7b": {
        "name": "Starling 7B",
        "model": "openrouter/starling-lm-7b",
        "group": "Light",
        "active": True
    },
    "zephyr-beta": {
        "name": "Zephyr Beta",
        "model": "openrouter/zephyr-7b-beta",
        "group": "Light",
        "active": True
    },

    # Explicitly disabled (kept for reference)
    "perplexity-pro": {
        "name": "Perplexity Pro",
        "model": "perplexity/sonar-pro",
        "group": "Research",
        "active": False,
        "notes": "Disabled: errors/rate limits in multi-agent runs."
    },
    "claude-3.5": {
        "name": "Claude 3.5",
        "model": "anthropic/claude-3-5-sonnet",
        "group": "General",
        "active": False,
        "notes": "Disabled per your preference; collaboration limits."
    },
}

@agents_bp.route('/list', methods=['GET'])
def get_agents():
    """Get all available agents"""
    try:
        # Return first 10 for current interface compatibility
        current_agents = {k: v for k, v in list(AGENTS.items())[:10]}
        
        return jsonify({
            'status': 'success',
            'agents': current_agents,
            'total_agents': len(AGENTS),
            'revolutionary_agents': len(AGENTS) - 10,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@agents_bp.route('/all', methods=['GET'])
def get_all_agents():
    """Get all 20 agents for revolutionary modes"""
    try:
        return jsonify({
            'status': 'success',
            'agents': AGENTS,
            'total_agents': len(AGENTS),
            'current_working': list(AGENTS.keys())[:10],
            'revolutionary_additional': list(AGENTS.keys())[10:],
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@agents_bp.route('/chat', methods=['POST'])
def chat_with_agent():
    """Send message to specific agent"""
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        message = data.get('message')
        
        if not agent_id or not message:
            return jsonify({'status': 'error', 'message': 'Missing agent_id or message'}), 400
        
        if agent_id not in AGENTS:
            return jsonify({'status': 'error', 'message': 'Invalid agent_id'}), 400
        
        agent = AGENTS[agent_id]
        
        # Call OpenRouter API
        openrouter_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://thepromptlink.netlify.app',
                'X-Title': 'PromptLink AI Collaboration'
            },
            json={
                'model': agent['model'],
                'messages': [
                    {
                        'role': 'system',
                        'content': f'You are {agent["name"]}, specializing in {agent["specialty"]}. {agent["description"]}. Collaborate effectively and provide insightful responses.'
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
        
        if openrouter_response.status_code == 200:
            response_data = openrouter_response.json()
            agent_response = response_data['choices'][0]['message']['content']
            
            return jsonify({
                'status': 'success',
                'agent_id': agent_id,
                'agent_name': agent['name'],
                'response': agent_response,
                'specialty': agent['specialty'],
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'OpenRouter API error: {openrouter_response.status_code}'
            }), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@agents_bp.route('/batch-chat', methods=['POST'])
def batch_chat():
    """Send message to multiple agents (for revolutionary modes)"""
    try:
        data = request.get_json()
        agent_ids = data.get('agent_ids', [])
        message = data.get('message')
        
        if not agent_ids or not message:
            return jsonify({'status': 'error', 'message': 'Missing agent_ids or message'}), 400
        
        responses = []
        
        for agent_id in agent_ids:
            if agent_id not in AGENTS:
                continue
                
            agent = AGENTS[agent_id]
            
            # Call OpenRouter API for each agent
            openrouter_response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://thepromptlink.netlify.app',
                    'X-Title': 'PromptLink AI Collaboration'
                },
                json={
                    'model': agent['model'],
                    'messages': [
                        {
                            'role': 'system',
                            'content': f'You are {agent["name"]}, specializing in {agent["specialty"]}. {agent["description"]}. Collaborate effectively and provide insightful responses.'
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
            
            if openrouter_response.status_code == 200:
                response_data = openrouter_response.json()
                agent_response = response_data['choices'][0]['message']['content']
                
                responses.append({
                    'agent_id': agent_id,
                    'agent_name': agent['name'],
                    'response': agent_response,
                    'specialty': agent['specialty']
                })
        
        return jsonify({
            'status': 'success',
            'responses': responses,
            'total_responses': len(responses),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

