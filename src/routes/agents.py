from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime

agents_bp = Blueprint('agents', __name__)

# Complete 20-agent configuration
AGENTS = {
    # Current working 10 agents
    'gpt-4o': {
        'name': 'GPT-4o',
        'model': 'openai/gpt-4o',
        'description': 'Strategic planning & complex reasoning',
        'specialty': 'Strategic Analysis',
        'active': True
    },
    'chatgpt-4-turbo': {
        'name': 'ChatGPT 4 Turbo',
        'model': 'openai/gpt-4-turbo',
        'description': 'Business analysis & communication',
        'specialty': 'Business Strategy',
        'active': True
    },
    'deepseek-r1': {
        'name': 'DeepSeek R1',
        'model': 'deepseek/deepseek-r1',
        'description': 'Advanced coding & technical problem solving',
        'specialty': 'Technical Expert',
        'active': True
    },
    'meta-llama-3.3': {
        'name': 'Meta Llama 3.3',
        'model': 'meta-llama/llama-3.3-70b-instruct',
        'description': 'Creative thinking & content generation',
        'specialty': 'Creative Analysis',
        'active': True
    },
    'mistral-large': {
        'name': 'Mistral Large',
        'model': 'mistralai/mistral-large',
        'description': 'Multilingual & analytical processing',
        'specialty': 'Analytical Processing',
        'active': True
    },
    'gemini-2.0-flash': {
        'name': 'Gemini 2.0 Flash',
        'model': 'google/gemini-2.0-flash-exp',
        'description': 'Fast creative synthesis & brainstorming',
        'specialty': 'Creative Synthesis',
        'active': True
    },
    'perplexity-pro': {
        'name': 'Perplexity Pro',
        'model': 'perplexity/llama-3.1-sonar-huge-128k-online',
        'description': 'Research & fact-finding with web access',
        'specialty': 'Research Expert',
        'active': True
    },
    'gemini-pro-1.5': {
        'name': 'Gemini Pro 1.5',
        'model': 'google/gemini-pro-1.5',
        'description': 'Massive context & document analysis',
        'specialty': 'Document Analysis',
        'active': True
    },
    'command-r-plus': {
        'name': 'Command R+',
        'model': 'cohere/command-r-plus',
        'description': 'Enterprise solutions & business strategy',
        'specialty': 'Enterprise Solutions',
        'active': True
    },
    'qwen-2.5-72b': {
        'name': 'Qwen 2.5 72B',
        'model': 'qwen/qwen-2.5-72b-instruct',
        'description': 'Multilingual expertise & cultural insights',
        'specialty': 'Multilingual Expert',
        'active': True
    },
    
    # Additional 10 revolutionary agents
    'llama-3.3-70b': {
        'name': 'Llama 3.3 70B',
        'model': 'meta-llama/llama-3.3-70b-instruct',
        'description': 'Advanced reasoning & logical analysis',
        'specialty': 'Logical Reasoning',
        'active': True
    },
    'mixtral-8x22b': {
        'name': 'Mixtral 8x22B',
        'model': 'mistralai/mixtral-8x22b-instruct',
        'description': 'Technical expertise & system design',
        'specialty': 'System Design',
        'active': True
    },
    'yi-large': {
        'name': 'Yi Large',
        'model': '01-ai/yi-large',
        'description': 'Innovation & creative problem solving',
        'specialty': 'Innovation Expert',
        'active': True
    },
    'nous-hermes-3': {
        'name': 'Nous Hermes 3',
        'model': 'nousresearch/hermes-3-llama-3.1-405b',
        'description': 'Uncensored collaboration & free thinking',
        'specialty': 'Free Thinking',
        'active': True
    },
    'wizardlm-2': {
        'name': 'WizardLM 2',
        'model': 'microsoft/wizardlm-2-8x22b',
        'description': 'Mathematical reasoning & logic puzzles',
        'specialty': 'Mathematical Reasoning',
        'active': True
    },
    'dolphin-mixtral': {
        'name': 'Dolphin Mixtral',
        'model': 'cognitivecomputations/dolphin-2.9-llama3-70b',
        'description': 'Uncensored synthesis & bold ideas',
        'specialty': 'Bold Synthesis',
        'active': True
    },
    'openhermes-2.5': {
        'name': 'OpenHermes 2.5',
        'model': 'teknium/openhermes-2.5-mistral-7b',
        'description': 'Perfect collaboration & team dynamics',
        'specialty': 'Collaboration Expert',
        'active': True
    },
    'starling-7b': {
        'name': 'Starling 7B',
        'model': 'berkeley-nest/starling-lm-7b-alpha',
        'description': 'Fast synthesis & quick insights',
        'specialty': 'Quick Insights',
        'active': True
    },
    'neural-chat': {
        'name': 'Neural Chat',
        'model': 'intel/neural-chat-7b-v3-3',
        'description': 'Conversational intelligence & dialogue',
        'specialty': 'Dialogue Expert',
        'active': True
    },
    'zephyr-beta': {
        'name': 'Zephyr Beta',
        'model': 'huggingfaceh4/zephyr-7b-beta',
        'description': 'Advanced reasoning & final synthesis',
        'specialty': 'Final Synthesis',
        'active': True
    }
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

