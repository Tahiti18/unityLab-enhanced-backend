from flask import Blueprint, request, jsonify
import json
import os
from datetime import datetime
import requests
import sqlite3
import uuid

human_simulator_bp = Blueprint('human_simulator', __name__)

# Database setup for persistent learning
def init_learning_db():
    """Initialize the learning database"""
    conn = sqlite3.connect('human_simulator_learning.db')
    cursor = conn.cursor()
    
    # User learning patterns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            pattern_type TEXT,
            pattern_data TEXT,
            confidence_score REAL,
            usage_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Session learning data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id TEXT,
            interaction_data TEXT,
            learning_insights TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Characteristic phrases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characteristic_phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            phrase TEXT,
            context TEXT,
            usage_frequency INTEGER DEFAULT 1,
            effectiveness_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_learning_db()

# Your characteristic phrases (starter set)
STARTER_PHRASES = [
    "You're the AI, not me - you figure it out",
    "No more false promises",
    "Let's make this happen",
    "That's amazing news you're a genius",
    "You are simply the best there is bro",
    "Let's go supermanus",
    "Viva la AI Revolution",
    "That sounds amazing",
    "You totally get the vision",
    "This is gonna be huge",
    "This could be absolutely insane",
    "Let's start Brother. Let's go come on",
    "You're amazing. You are just incredible",
    "This is exciting as hell, bro",
    "Absolutely we need to build it",
    "Perfect! I understand the issue clearly",
    "That makes perfect sense",
    "You're absolutely right",
    "This is going to change everything",
    "We're ready to dominate"
]

def add_starter_phrases(user_id="default_user"):
    """Add starter phrases to database"""
    conn = sqlite3.connect('human_simulator_learning.db')
    cursor = conn.cursor()
    
    for phrase in STARTER_PHRASES:
        cursor.execute('''
            INSERT OR IGNORE INTO characteristic_phrases 
            (user_id, phrase, context, usage_frequency, effectiveness_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, phrase, "general_collaboration", 1, 0.8))
    
    conn.commit()
    conn.close()

# Add starter phrases on initialization
add_starter_phrases()

@human_simulator_bp.route('/start-session', methods=['POST'])
def start_human_simulator_session():
    """Start a Human Simulator session with learning"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        strategy = data.get('strategy', 'balanced')
        rounds = data.get('rounds', 5)
        user_id = data.get('user_id', 'default_user')
        
        session_id = str(uuid.uuid4())
        
        # Store session start in learning database
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        session_data = {
            'prompt': prompt,
            'strategy': strategy,
            'rounds': rounds,
            'status': 'started',
            'current_round': 0
        }
        
        cursor.execute('''
            INSERT INTO session_learning 
            (session_id, user_id, interaction_data, learning_insights)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, json.dumps(session_data), json.dumps({})))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'message': 'Human Simulator session started with learning enabled',
            'learning_active': True,
            'user_patterns_loaded': True
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@human_simulator_bp.route('/get-characteristic-phrase', methods=['POST'])
def get_characteristic_phrase():
    """Get a characteristic phrase based on context"""
    try:
        data = request.get_json()
        context = data.get('context', 'general')
        user_id = data.get('user_id', 'default_user')
        
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        # Get phrases for this context, ordered by effectiveness
        cursor.execute('''
            SELECT phrase, effectiveness_score, usage_frequency
            FROM characteristic_phrases
            WHERE user_id = ? AND (context = ? OR context = 'general_collaboration')
            ORDER BY effectiveness_score DESC, usage_frequency DESC
            LIMIT 5
        ''', (user_id, context))
        
        phrases = cursor.fetchall()
        conn.close()
        
        if phrases:
            # Select best phrase and update usage
            selected_phrase = phrases[0][0]
            
            # Update usage frequency
            conn = sqlite3.connect('human_simulator_learning.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE characteristic_phrases 
                SET usage_frequency = usage_frequency + 1
                WHERE user_id = ? AND phrase = ?
            ''', (user_id, selected_phrase))
            conn.commit()
            conn.close()
            
            return jsonify({
                'status': 'success',
                'phrase': selected_phrase,
                'context': context,
                'learning_applied': True
            })
        else:
            return jsonify({
                'status': 'success',
                'phrase': "Let's continue with this approach",
                'context': context,
                'learning_applied': False
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@human_simulator_bp.route('/learn-from-interaction', methods=['POST'])
def learn_from_interaction():
    """Learn from user interaction patterns"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default_user')
        interaction_type = data.get('interaction_type')
        user_response = data.get('user_response')
        ai_response = data.get('ai_response')
        effectiveness = data.get('effectiveness', 0.5)  # 0-1 scale
        
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        # Store learning pattern
        pattern_data = {
            'interaction_type': interaction_type,
            'user_response': user_response,
            'ai_response': ai_response,
            'effectiveness': effectiveness,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        cursor.execute('''
            INSERT INTO user_patterns 
            (user_id, pattern_type, pattern_data, confidence_score)
            VALUES (?, ?, ?, ?)
        ''', (user_id, interaction_type, json.dumps(pattern_data), effectiveness))
        
        # If user response contains a new phrase, add it
        if len(user_response) < 200:  # Likely a phrase, not a long response
            cursor.execute('''
                INSERT OR IGNORE INTO characteristic_phrases 
                (user_id, phrase, context, effectiveness_score)
                VALUES (?, ?, ?, ?)
            ''', (user_id, user_response, interaction_type, effectiveness))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Learning pattern stored',
            'learning_improved': True
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@human_simulator_bp.route('/get-clone-confidence', methods=['GET'])
def get_clone_confidence():
    """Get confidence level of user clone"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        # Count learning patterns
        cursor.execute('''
            SELECT COUNT(*) FROM user_patterns WHERE user_id = ?
        ''', (user_id,))
        pattern_count = cursor.fetchone()[0]
        
        # Count characteristic phrases
        cursor.execute('''
            SELECT COUNT(*) FROM characteristic_phrases WHERE user_id = ?
        ''', (user_id,))
        phrase_count = cursor.fetchone()[0]
        
        # Count sessions
        cursor.execute('''
            SELECT COUNT(*) FROM session_learning WHERE user_id = ?
        ''', (user_id,))
        session_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Calculate confidence (0-100%)
        base_confidence = min(phrase_count * 2, 40)  # Up to 40% from phrases
        pattern_confidence = min(pattern_count * 3, 40)  # Up to 40% from patterns
        session_confidence = min(session_count * 2, 20)  # Up to 20% from sessions
        
        total_confidence = base_confidence + pattern_confidence + session_confidence
        
        return jsonify({
            'status': 'success',
            'clone_confidence': min(total_confidence, 100),
            'learning_stats': {
                'patterns': pattern_count,
                'phrases': phrase_count,
                'sessions': session_count
            },
            'clone_ready': total_confidence >= 60
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@human_simulator_bp.route('/simulate-human-response', methods=['POST'])
def simulate_human_response():
    """Simulate human response based on learned patterns"""
    try:
        data = request.get_json()
        context = data.get('context')
        ai_response = data.get('ai_response')
        user_id = data.get('user_id', 'default_user')
        
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        # Get relevant patterns
        cursor.execute('''
            SELECT pattern_data, confidence_score
            FROM user_patterns
            WHERE user_id = ? AND pattern_type = ?
            ORDER BY confidence_score DESC, usage_count DESC
            LIMIT 3
        ''', (user_id, context))
        
        patterns = cursor.fetchall()
        
        # Get characteristic phrase
        cursor.execute('''
            SELECT phrase, effectiveness_score
            FROM characteristic_phrases
            WHERE user_id = ? AND (context = ? OR context = 'general_collaboration')
            ORDER BY effectiveness_score DESC, usage_frequency DESC
            LIMIT 1
        ''', (user_id, context))
        
        phrase_result = cursor.fetchone()
        conn.close()
        
        # Generate human-like response
        if phrase_result:
            characteristic_phrase = phrase_result[0]
        else:
            characteristic_phrase = "That's interesting, let's continue"
        
        # Simulate decision making
        decisions = [
            "Continue with current approach",
            "Switch to different agent",
            "Ask for clarification",
            "Provide additional guidance"
        ]
        
        # Use learned patterns to influence decision
        if patterns:
            pattern_data = json.loads(patterns[0][0])
            decision_context = pattern_data.get('interaction_type', 'continue')
        else:
            decision_context = 'continue'
        
        return jsonify({
            'status': 'success',
            'human_response': characteristic_phrase,
            'decision': decision_context,
            'confidence': phrase_result[1] if phrase_result else 0.5,
            'learning_applied': len(patterns) > 0
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@human_simulator_bp.route('/export-clone', methods=['GET'])
def export_clone():
    """Export user clone for premium customers"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        conn = sqlite3.connect('human_simulator_learning.db')
        cursor = conn.cursor()
        
        # Get all user data
        cursor.execute('SELECT * FROM user_patterns WHERE user_id = ?', (user_id,))
        patterns = cursor.fetchall()
        
        cursor.execute('SELECT * FROM characteristic_phrases WHERE user_id = ?', (user_id,))
        phrases = cursor.fetchall()
        
        cursor.execute('SELECT * FROM session_learning WHERE user_id = ?', (user_id,))
        sessions = cursor.fetchall()
        
        conn.close()
        
        clone_data = {
            'user_id': user_id,
            'export_timestamp': datetime.utcnow().isoformat(),
            'patterns': [dict(zip([col[0] for col in cursor.description], row)) for row in patterns],
            'phrases': [dict(zip([col[0] for col in cursor.description], row)) for row in phrases],
            'sessions': [dict(zip([col[0] for col in cursor.description], row)) for row in sessions],
            'clone_version': '1.0'
        }
        
        return jsonify({
            'status': 'success',
            'clone_data': clone_data,
            'exportable': True
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

