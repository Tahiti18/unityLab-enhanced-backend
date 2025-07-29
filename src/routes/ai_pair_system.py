from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime
import json

ai_pair_system_bp = Blueprint('ai_pair_system', __name__)

# AI Pair System Configuration - Intelligent Agent Pairing
AGENT_PROFILES = {
    'gpt-4o': {
        'name': 'GPT-4o',
        'strengths': ['strategic_thinking', 'complex_reasoning', 'synthesis'],
        'personality': 'analytical',
        'best_pairs': ['gemini-2.0-flash', 'deepseek-r1', 'meta-llama-3.3']
    },
    'chatgpt-4-turbo': {
        'name': 'ChatGPT 4 Turbo',
        'strengths': ['business_analysis', 'communication', 'planning'],
        'personality': 'professional',
        'best_pairs': ['mistral-large', 'claude-3.5-sonnet', 'command-r-plus']
    },
    'deepseek-r1': {
        'name': 'DeepSeek R1',
        'strengths': ['technical_analysis', 'coding', 'problem_solving'],
        'personality': 'technical',
        'best_pairs': ['gpt-4o', 'wizardlm-2', 'neural-chat']
    },
    'meta-llama-3.3': {
        'name': 'Meta Llama 3.3',
        'strengths': ['creative_thinking', 'content_generation', 'innovation'],
        'personality': 'creative',
        'best_pairs': ['gemini-2.0-flash', 'yi-large', 'dolphin-mixtral']
    },
    'gemini-2.0-flash': {
        'name': 'Gemini 2.0 Flash',
        'strengths': ['fast_synthesis', 'brainstorming', 'multi_modal'],
        'personality': 'dynamic',
        'best_pairs': ['gpt-4o', 'meta-llama-3.3', 'perplexity-pro']
    }
}

@ai_pair_system_bp.route('/suggest-pair', methods=['POST'])
def suggest_optimal_pair():
    """Suggest optimal AI agent pairing based on task and context"""
    try:
        data = request.get_json()
        task_type = data.get('task_type', 'general')
        primary_agent = data.get('primary_agent')
        context = data.get('context', '')
        
        # AI-powered pairing recommendation
        pairing_prompt = f"""
        Recommend the optimal AI agent pairing for this task:
        
        Task Type: {task_type}
        Primary Agent: {primary_agent if primary_agent else 'Not specified'}
        Context: {context}
        
        Available agents and their strengths:
        {json.dumps(AGENT_PROFILES, indent=2)}
        
        Provide:
        1. RECOMMENDED PAIR: Best two agents for this task
        2. REASONING: Why this pairing works well
        3. EXPECTED SYNERGY: How they complement each other
        4. ALTERNATIVE PAIRS: 2-3 backup options
        """
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://unitylab.ai',
                'X-Title': 'UnityLab AI Pair System'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an AI pairing expert who understands agent capabilities and optimal combinations for different tasks.'
                    },
                    {
                        'role': 'user',
                        'content': pairing_prompt
                    }
                ],
                'max_tokens': 1500,
                'temperature': 0.3
            }
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'AI pairing analysis failed'}), 500
        
        recommendation = response.json()['choices'][0]['message']['content']
        
        return jsonify({
            'status': 'success',
            'pairing_recommendation': {
                'task_type': task_type,
                'analysis': recommendation,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_pair_system_bp.route('/compatibility', methods=['POST'])
def check_agent_compatibility():
    """Check compatibility between two specific agents"""
    try:
        data = request.get_json()
        agent_a = data.get('agent_a')
        agent_b = data.get('agent_b')
        
        if not agent_a or not agent_b:
            return jsonify({'error': 'Both agents are required'}), 400
        
        # Calculate compatibility score
        compatibility_score = 0
        compatibility_factors = []
        
        if agent_a in AGENT_PROFILES and agent_b in AGENT_PROFILES:
            profile_a = AGENT_PROFILES[agent_a]
            profile_b = AGENT_PROFILES[agent_b]
            
            # Check if they're in each other's best pairs
            if agent_b in profile_a.get('best_pairs', []):
                compatibility_score += 30
                compatibility_factors.append('Proven successful pairing')
            
            # Check personality compatibility
            if profile_a['personality'] != profile_b['personality']:
                compatibility_score += 20
                compatibility_factors.append('Complementary personalities')
            
            # Check strength overlap (some overlap is good, too much is redundant)
            common_strengths = set(profile_a['strengths']) & set(profile_b['strengths'])
            if len(common_strengths) == 1:
                compatibility_score += 25
                compatibility_factors.append('Balanced skill overlap')
            elif len(common_strengths) == 0:
                compatibility_score += 15
                compatibility_factors.append('Diverse skill sets')
        
        # Base compatibility for any valid pair
        compatibility_score += 25
        
        compatibility_level = 'Excellent' if compatibility_score >= 80 else \
                            'Good' if compatibility_score >= 60 else \
                            'Fair' if compatibility_score >= 40 else 'Poor'
        
        return jsonify({
            'status': 'success',
            'compatibility': {
                'agent_a': agent_a,
                'agent_b': agent_b,
                'score': min(compatibility_score, 100),
                'level': compatibility_level,
                'factors': compatibility_factors,
                'recommendation': 'Highly recommended' if compatibility_score >= 70 else 'Consider alternatives'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_pair_system_bp.route('/status', methods=['GET'])
def ai_pair_system_status():
    """Get AI Pair System status and capabilities"""
    return jsonify({
        'status': 'active',
        'system': 'UnityLab AI Pair System',
        'capabilities': {
            'intelligent_pairing': True,
            'compatibility_analysis': True,
            'task_based_recommendations': True,
            'agent_profiles': len(AGENT_PROFILES)
        },
        'supported_task_types': [
            'strategic_planning',
            'technical_analysis', 
            'creative_brainstorming',
            'business_analysis',
            'problem_solving',
            'content_creation',
            'general_discussion'
        ]
    })

