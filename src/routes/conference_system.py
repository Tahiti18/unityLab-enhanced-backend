from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime
import json
import uuid

conference_system_bp = Blueprint('conference_system', __name__)

# Conference System Configuration
CONFERENCE_AGENTS = {
    'moderator': {
        'name': 'Conference Moderator',
        'model': 'openai/gpt-4o',
        'role': 'Facilitates discussion, manages flow, synthesizes insights',
        'system_prompt': 'You are a skilled conference moderator. Guide discussions, ensure all perspectives are heard, and synthesize key insights.'
    },
    'strategic_analyst': {
        'name': 'Strategic Analyst',
        'model': 'openai/gpt-4-turbo',
        'role': 'Strategic planning and business analysis',
        'system_prompt': 'You are a strategic analyst. Provide strategic insights, identify opportunities, and analyze business implications.'
    },
    'technical_expert': {
        'name': 'Technical Expert',
        'model': 'deepseek/deepseek-r1',
        'role': 'Technical feasibility and implementation',
        'system_prompt': 'You are a technical expert. Assess technical feasibility, provide implementation guidance, and identify technical challenges.'
    },
    'creative_director': {
        'name': 'Creative Director',
        'model': 'meta-llama/llama-3.3-70b-instruct',
        'role': 'Creative solutions and innovation',
        'system_prompt': 'You are a creative director. Generate innovative ideas, think outside the box, and provide creative solutions.'
    },
    'risk_assessor': {
        'name': 'Risk Assessor',
        'model': 'mistralai/mistral-large',
        'role': 'Risk analysis and mitigation strategies',
        'system_prompt': 'You are a risk assessment specialist. Identify potential risks, analyze their impact, and suggest mitigation strategies.'
    },
    'market_researcher': {
        'name': 'Market Researcher',
        'model': 'google/gemini-2.0-flash-exp',
        'role': 'Market analysis and consumer insights',
        'system_prompt': 'You are a market researcher. Provide market insights, analyze trends, and assess consumer behavior.'
    },
    'financial_advisor': {
        'name': 'Financial Advisor',
        'model': 'anthropic/claude-3.5-sonnet',
        'role': 'Financial planning and analysis',
        'system_prompt': 'You are a financial advisor. Analyze financial implications, provide cost-benefit analysis, and suggest financial strategies.'
    },
    'legal_counsel': {
        'name': 'Legal Counsel',
        'model': 'cohere/command-r-plus',
        'role': 'Legal compliance and regulatory guidance',
        'system_prompt': 'You are legal counsel. Assess legal implications, ensure compliance, and identify regulatory considerations.'
    },
    'operations_manager': {
        'name': 'Operations Manager',
        'model': 'perplexity/llama-3.1-sonar-large-128k-online',
        'role': 'Operational efficiency and process optimization',
        'system_prompt': 'You are an operations manager. Focus on operational efficiency, process optimization, and implementation logistics.'
    },
    'customer_advocate': {
        'name': 'Customer Advocate',
        'model': 'qwen/qwen-2.5-72b-instruct',
        'role': 'Customer experience and satisfaction',
        'system_prompt': 'You are a customer advocate. Represent customer interests, focus on user experience, and ensure customer satisfaction.'
    }
}

# Active conferences storage
active_conferences = {}

@conference_system_bp.route('/start', methods=['POST'])
def start_conference():
    """Start a new AI conference session"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        participants = data.get('participants', list(CONFERENCE_AGENTS.keys()))
        conference_type = data.get('type', 'roundtable')  # roundtable, panel, debate
        duration_rounds = data.get('rounds', 3)
        
        if not topic:
            return jsonify({'error': 'Conference topic is required'}), 400
        
        # Create conference session
        conference_id = str(uuid.uuid4())
        
        conference_session = {
            'id': conference_id,
            'topic': topic,
            'type': conference_type,
            'participants': participants,
            'rounds': duration_rounds,
            'current_round': 0,
            'messages': [],
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'moderator_notes': []
        }
        
        active_conferences[conference_id] = conference_session
        
        # Moderator opens the conference
        opening_prompt = f"""
        Welcome to this AI conference on: {topic}

        Conference Type: {conference_type.title()}
        Participants: {', '.join([CONFERENCE_AGENTS[p]['name'] for p in participants if p in CONFERENCE_AGENTS])}
        Planned Rounds: {duration_rounds}

        As the moderator, please:
        1. Open the conference with a brief introduction
        2. Set the agenda and discussion framework
        3. Invite the first participant to share their perspective
        4. Establish the ground rules for productive discussion
        """
        
        moderator_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://unitylab.ai',
                'X-Title': 'UnityLab Conference System'
            },
            json={
                'model': CONFERENCE_AGENTS['moderator']['model'],
                'messages': [
                    {
                        'role': 'system',
                        'content': CONFERENCE_AGENTS['moderator']['system_prompt']
                    },
                    {
                        'role': 'user',
                        'content': opening_prompt
                    }
                ],
                'max_tokens': 1500,
                'temperature': 0.7
            }
        )
        
        if moderator_response.status_code == 200:
            opening_message = moderator_response.json()['choices'][0]['message']['content']
            conference_session['messages'].append({
                'round': 0,
                'speaker': 'moderator',
                'speaker_name': 'Conference Moderator',
                'message': opening_message,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'conference': conference_session
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@conference_system_bp.route('/continue/<conference_id>', methods=['POST'])
def continue_conference(conference_id):
    """Continue conference with next participant"""
    try:
        if conference_id not in active_conferences:
            return jsonify({'error': 'Conference not found'}), 404
        
        conference = active_conferences[conference_id]
        
        if conference['status'] != 'active':
            return jsonify({'error': 'Conference is not active'}), 400
        
        data = request.get_json()
        next_participant = data.get('participant')
        
        # If no specific participant, rotate through participants
        if not next_participant:
            current_round = conference['current_round']
            participants = conference['participants']
            participant_index = current_round % len(participants)
            next_participant = participants[participant_index]
        
        if next_participant not in CONFERENCE_AGENTS:
            return jsonify({'error': 'Invalid participant'}), 400
        
        # Build context from previous messages
        context = f"Conference Topic: {conference['topic']}\n\n"
        context += "Previous Discussion:\n"
        for msg in conference['messages'][-5:]:  # Last 5 messages for context
            context += f"{msg['speaker_name']}: {msg['message']}\n\n"
        
        participant_prompt = f"""
        {context}
        
        As the {CONFERENCE_AGENTS[next_participant]['name']}, please contribute to this conference discussion.
        
        Your role: {CONFERENCE_AGENTS[next_participant]['role']}
        
        Please provide your perspective on the topic, building upon the previous discussion.
        Keep your response focused and valuable to the overall conference goals.
        """
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://unitylab.ai',
                'X-Title': 'UnityLab Conference System'
            },
            json={
                'model': CONFERENCE_AGENTS[next_participant]['model'],
                'messages': [
                    {
                        'role': 'system',
                        'content': CONFERENCE_AGENTS[next_participant]['system_prompt']
                    },
                    {
                        'role': 'user',
                        'content': participant_prompt
                    }
                ],
                'max_tokens': 1500,
                'temperature': 0.7
            }
        )
        
        if response.status_code == 200:
            participant_message = response.json()['choices'][0]['message']['content']
            conference['messages'].append({
                'round': conference['current_round'],
                'speaker': next_participant,
                'speaker_name': CONFERENCE_AGENTS[next_participant]['name'],
                'message': participant_message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            conference['current_round'] += 1
            
            # Check if conference should end
            if conference['current_round'] >= conference['rounds'] * len(conference['participants']):
                conference['status'] = 'completed'
        
        return jsonify({
            'status': 'success',
            'conference': conference,
            'latest_message': {
                'speaker': next_participant,
                'speaker_name': CONFERENCE_AGENTS[next_participant]['name'],
                'message': participant_message if response.status_code == 200 else 'Response failed'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@conference_system_bp.route('/synthesize/<conference_id>', methods=['POST'])
def synthesize_conference(conference_id):
    """Generate conference synthesis and summary"""
    try:
        if conference_id not in active_conferences:
            return jsonify({'error': 'Conference not found'}), 404
        
        conference = active_conferences[conference_id]
        
        # Build full conference transcript
        transcript = f"Conference Topic: {conference['topic']}\n\n"
        for msg in conference['messages']:
            transcript += f"[Round {msg['round']}] {msg['speaker_name']}:\n{msg['message']}\n\n"
        
        synthesis_prompt = f"""
        Synthesize this AI conference discussion into a comprehensive summary:

        {transcript}

        Please provide:
        1. EXECUTIVE SUMMARY: Key insights and conclusions
        2. MAIN THEMES: Primary topics and patterns discussed
        3. CONSENSUS POINTS: Areas where participants agreed
        4. DIVERGENT VIEWS: Different perspectives and debates
        5. ACTION ITEMS: Recommended next steps
        6. PARTICIPANT CONTRIBUTIONS: Summary of each participant's key insights
        7. OVERALL ASSESSMENT: Quality and value of the discussion
        
        Format as a professional conference report.
        """
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://unitylab.ai',
                'X-Title': 'UnityLab Conference System'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an expert conference synthesizer who creates comprehensive, insightful summaries of multi-participant discussions.'
                    },
                    {
                        'role': 'user',
                        'content': synthesis_prompt
                    }
                ],
                'max_tokens': 3000,
                'temperature': 0.3
            }
        )
        
        if response.status_code == 200:
            synthesis = response.json()['choices'][0]['message']['content']
            conference['synthesis'] = synthesis
            conference['synthesized_at'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'status': 'success',
            'conference_id': conference_id,
            'synthesis': synthesis if response.status_code == 200 else 'Synthesis failed',
            'conference_stats': {
                'total_messages': len(conference['messages']),
                'participants': len(conference['participants']),
                'rounds_completed': conference['current_round'],
                'duration': conference.get('synthesized_at', datetime.utcnow().isoformat())
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@conference_system_bp.route('/list', methods=['GET'])
def list_conferences():
    """List all active and completed conferences"""
    return jsonify({
        'status': 'success',
        'conferences': [
            {
                'id': conf_id,
                'topic': conf['topic'],
                'type': conf['type'],
                'status': conf['status'],
                'participants': len(conf['participants']),
                'messages': len(conf['messages']),
                'created_at': conf['created_at']
            }
            for conf_id, conf in active_conferences.items()
        ]
    })

@conference_system_bp.route('/get/<conference_id>', methods=['GET'])
def get_conference(conference_id):
    """Get specific conference details"""
    if conference_id not in active_conferences:
        return jsonify({'error': 'Conference not found'}), 404
    
    return jsonify({
        'status': 'success',
        'conference': active_conferences[conference_id]
    })

@conference_system_bp.route('/agents', methods=['GET'])
def get_conference_agents():
    """Get available conference agents"""
    return jsonify({
        'status': 'success',
        'agents': {
            agent_key: {
                'name': agent['name'],
                'role': agent['role'],
                'model': agent['model']
            }
            for agent_key, agent in CONFERENCE_AGENTS.items()
        }
    })

@conference_system_bp.route('/status', methods=['GET'])
def conference_system_status():
    """Get conference system status"""
    return jsonify({
        'status': 'active',
        'system': 'UnityLab Conference System',
        'capabilities': {
            'multi_agent_conferences': True,
            'real_time_synthesis': True,
            'conference_moderation': True,
            'available_agents': len(CONFERENCE_AGENTS)
        },
        'active_conferences': len([c for c in active_conferences.values() if c['status'] == 'active']),
        'total_conferences': len(active_conferences),
        'conference_types': ['roundtable', 'panel', 'debate']
    })

