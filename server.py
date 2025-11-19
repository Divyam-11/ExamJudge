import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, g
from flask_socketio import SocketIO, join_room, emit, disconnect
from flask_cors import CORS
import re
from datetime import datetime
import database
from functools import wraps

# --- NEW: Firebase Imports ---
import firebase_admin
from firebase_admin import credentials, auth

# --- App Initialization & DB Setup ---
database.init_db()

# --- NEW: Initialize Firebase Admin ---
# Ensure you have 'serviceAccountKey.json' in your project folder
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Warning: Firebase Admin SDK failed to initialize: {e}")
    print("Auth features will fail without a valid serviceAccountKey.json")

app = Flask(__name__, static_folder='dist')
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/log": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Constants (Unchanged) ---
CHEATING_KEYWORDS_REGEX = re.compile(r'chatgpt|gemini|gfg|leetcode|stackoverflow|chegg', re.IGNORECASE)
HIGH_CHAR_PASTE_THRESHOLD = 100
room_participants = {}

# --- NEW: Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

        token = auth_header.split("Bearer ")[1]
        try:
            # Verify the token with Firebase
            decoded_token = auth.verify_id_token(token)
            # Store user info in Flask's global 'g' object
            g.user_id = decoded_token['uid']
            g.user_email = decoded_token.get('email', '')
        except Exception as e:
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401

        return f(*args, **kwargs)
    return decorated_function

# --- Helper to broadcast student list (Unchanged) ---
def emit_student_list(room):
    student_list = []
    if room in room_participants:
        for sid, details in room_participants[room].items():
            name = details.get('name', 'Unknown')
            enrollment = details.get('enrollment', 'N/A')
            subsection = details.get('subsection', 'N/A')
            student_list.append(f"{name} ({enrollment}) - Section: {subsection}")
    socketio.emit('update_student_list', {'students': sorted(student_list)}, room=room)

# --- Database Helper (Unchanged) ---
def log_to_db(timestamp, room_id, student_id, event_type, message, details=""):
    try:
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO logs (timestamp, room_id, student_id, event_type, message, details) VALUES (?, ?, ?, ?, ?, ?)',(timestamp, room_id, student_id, event_type, message, details))
        conn.commit()
        conn.close()
    except Exception as e: print(f"Database logging error: {e}")

# --- UPDATED API Endpoints ---

@app.route('/api/rooms', methods=['GET'])
@login_required  # Protect this route
def get_rooms():
    # Only fetch rooms owned by the current user
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM rooms WHERE owner_id = ? ORDER BY id', (g.user_id,))
    rooms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(rooms)

@app.route('/api/rooms', methods=['POST'])
@login_required  # Protect this route
def create_room():
    data = request.get_json()
    new_room_id = data.get('roomId', '').strip()
    if not new_room_id:
        return jsonify({"error": "Room ID cannot be empty"}), 400

    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    try:
        # Store the creator's UID along with the room ID
        cursor.execute('INSERT INTO rooms (id, owner_id) VALUES (?, ?)', (new_room_id, g.user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Room ID already exists"}), 409
    finally:
        conn.close()
    return jsonify({"message": "Room created successfully"}), 201

@app.route('/api/rooms/<room_id>', methods=['DELETE'])
@login_required  # Protect this route
def api_delete_room(room_id):
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()

    # Ensure only the owner can delete the room
    cursor.execute('DELETE FROM rooms WHERE id = ? AND owner_id = ?', (room_id, g.user_id))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Room not found or permission denied"}), 404

    conn.commit()
    conn.close()
    return jsonify({"message": "Room deleted successfully"}), 200

@app.route('/api/logs/<room_id>', methods=['GET'])
@login_required  # Protect this route
def get_logs_for_room(room_id):
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # First verify the user owns this room
    cursor.execute('SELECT 1 FROM rooms WHERE id = ? AND owner_id = ?', (room_id, g.user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Room not found or permission denied"}), 403

    cursor.execute('SELECT * FROM logs WHERE room_id = ? ORDER BY timestamp DESC', (room_id,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

# --- Log Activity Endpoint (Unchanged) ---
# Students do not log in via Firebase, they join via Room ID.
# We keep this public so the student client (Python script) can push logs.
@app.route('/log', methods=['POST'])
def log_activity():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Invalid data"}), 400

    # Validate room exists in DB before logging
    room_id = data.get('room_id', 'default_room')
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM rooms WHERE id = ?', (room_id,))
    exists = cursor.fetchone()
    conn.close()

    if not exists:
        return jsonify({"status": "error", "message": "Invalid Room ID"}), 404

    student_details = data.get('student_details', {})
    student_id = student_details.get('email', 'Unknown Student')
    event_type = data.get('event_type')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert_data = {'student_id': f"{student_details.get('name', 'Unknown')} ({student_details.get('enrollment', 'N/A')})", 'timestamp': timestamp.split(" ")[1]}
    log_details = f"Name: {student_details.get('name')}, Roll: {student_details.get('enrollment')}, Subsection: {student_details.get('subsection', 'N/A')}"

    if event_type == 'keystroke':
        keystrokes = data.get('keystrokes', '')
        found_keywords = CHEATING_KEYWORDS_REGEX.findall(keystrokes)
        for keyword in set(found_keywords):
            message = f'Suspicious keyword "{keyword}" typed.'
            alert_data.update({'type': 'Keyword Detected', 'message': f'Suspicious keyword "<strong>{keyword}</strong>" typed.', 'color': 'orange'})
            socketio.emit('new_alert', alert_data, room=room_id)
            log_to_db(timestamp, room_id, student_id, 'Keyword Detected', message, details=f"Keyword: {keyword}. {log_details}")
    elif event_type == 'paste':
        pasted_content = data.get('pasted_content', '')
        pasted_length = len(pasted_content)
        is_high_char = pasted_length > HIGH_CHAR_PASTE_THRESHOLD
        alert_type = 'High Character Paste' if is_high_char else 'Paste Detected'
        message = f'Pasted {pasted_length} characters.'
        alert_data.update({'type': alert_type, 'message': message, 'color': 'red', 'paste_content': pasted_content})
        socketio.emit('new_alert', alert_data, room=room_id)
        log_to_db(timestamp, room_id, student_id, alert_type, message, details=f"{pasted_content[:500]}... {log_details}")
    elif event_type == 'window_title':
        title = data.get('title', '')
        message = f'Suspicious window opened: {title}'
        alert_data.update({'type': 'Suspicious Window', 'message': f'Active window: <strong>{title}</strong>', 'color': 'blue'})
        socketio.emit('new_alert', alert_data, room=room_id)
        log_to_db(timestamp, room_id, student_id, 'Suspicious Window', message, details=f"Window Title: {title}. {log_details}")

    return jsonify({"status": "success"}), 200

# --- Socket.IO Events (Update for security optional but recommended) ---
# For now, we keep join_room open, but ideally you should verify token on connect.
@socketio.on('join_room')
def handle_join_room(data):
    room = data['room_id']
    # Optional: Check if room belongs to user here if you send token via socket
    join_room(room)
    emit_student_list(room)

@socketio.on('student_connect')
def handle_student_connect(data):
    room = data['room_id']
    student_details = data.get('student_details', {})
    sid = request.sid

    if room not in room_participants:
        room_participants[room] = {}
    room_participants[room][sid] = student_details

    student_name = student_details.get('name', 'Unknown')
    student_email = student_details.get('email', 'N/A')
    print(f"Student '{student_name}' connected to room '{room}'.")
    emit_student_list(room)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_to_db(timestamp, room, student_email, 'Connection', 'Student Joined', f"Name: {student_name}")
    socketio.emit('student_joined', {'name': student_name}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    room_to_update = None
    disconnected_student_details = None
    for room, participants in room_participants.items():
        if sid in participants:
            disconnected_student_details = participants.pop(sid)
            room_to_update = room
            if not participants:
                del room_participants[room]
            break
    if room_to_update and disconnected_student_details:
        student_name = disconnected_student_details.get('name', 'Unknown')
        student_email = disconnected_student_details.get('email', 'N/A')
        print(f"Student '{student_name}' disconnected from room '{room_to_update}'.")
        emit_student_list(room_to_update)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_to_db(timestamp, room_to_update, student_email, 'Connection', 'Student Left', f"Name: {student_name}")
        socketio.emit('student_left', {'name': student_name}, room=room_to_update)

# --- Frontend Serving ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# --- Chatbot ---
from chatbot import get_bot_response
@app.route('/api/chatbot', methods=['POST'])
def chatbot_reply():
    data = request.get_json()
    user_msg = data.get("message", "")
    bot_reply = get_bot_response(user_msg)
    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    port = 5000
    print("=====================================================")
    print("      EXAMJUDGE FULL STACK SERVER IS STARTING")
    print(f"  Application running at: http://127.0.0.1:{port}")
    print("=====================================================")

    socketio.run(app, host='0.0.0.0', port=port)
