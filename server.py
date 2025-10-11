# server.py
# Now serves the built React application and the API from one place.

import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
import re
from datetime import datetime
import database

# --- App Initialization & DB Setup ---
database.init_db()

# --- MODIFIED: Flask App Initialization for serving React ---
# The 'dist' folder is where your built React app lives.
app = Flask(__name__, static_folder='dist')

# Since the frontend and backend are on the same server, CORS is simpler.
# We still allow all origins for the API and log endpoints for flexibility.
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/log": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Constants & State Management (Unchanged) ---
CHEATING_KEYWORDS_REGEX = re.compile(r'chatgpt|gemini|gfg|leetcode|stackoverflow|chegg', re.IGNORECASE)
HIGH_CHAR_PASTE_THRESHOLD = 100
room_participants = {}

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

# --- API Endpoints (Unchanged) ---
# All your /api/... routes remain exactly the same.
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    conn = sqlite3.connect('monitoring.db'); cursor = conn.cursor()
    cursor.execute('SELECT id FROM rooms ORDER BY id')
    rooms = [row[0] for row in cursor.fetchall()]; conn.close()
    return jsonify(rooms)

@app.route('/api/rooms', methods=['POST'])
def create_room():
    data = request.get_json()
    new_room_id = data.get('roomId', '').strip()
    if not new_room_id: return jsonify({"error": "Room ID cannot be empty"}), 400
    conn = sqlite3.connect('monitoring.db'); cursor = conn.cursor()
    try: cursor.execute('INSERT INTO rooms (id) VALUES (?)', (new_room_id,)); conn.commit()
    except sqlite3.IntegrityError: pass
    finally: conn.close()
    return jsonify({"message": "Room created successfully"}), 201

@app.route('/api/rooms/<room_id>', methods=['DELETE'])
def api_delete_room(room_id):
    conn = sqlite3.connect('monitoring.db'); cursor = conn.cursor()
    cursor.execute('DELETE FROM rooms WHERE id = ?', (room_id,)); conn.commit(); conn.close()
    return jsonify({"message": "Room deleted successfully"}), 200

@app.route('/api/logs/<room_id>', methods=['GET'])
def get_logs_for_room(room_id):
    conn = sqlite3.connect('monitoring.db'); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    cursor.execute('SELECT * FROM logs WHERE room_id = ? ORDER BY timestamp DESC', (room_id,))
    logs = [dict(row) for row in cursor.fetchall()]; conn.close()
    return jsonify(logs)

# --- Log Activity Endpoint (Unchanged) ---
@app.route('/log', methods=['POST'])
def log_activity():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Invalid data"}), 400
    student_details = data.get('student_details', {})
    student_id = student_details.get('email', 'Unknown Student')
    room_id = data.get('room_id', 'default_room')
    event_type = data.get('event_type')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert_data = {'student_id': f"{student_details.get('name', 'Unknown')} ({student_details.get('enrollment', 'N/A')})", 'timestamp': timestamp.split(" ")[1]}
    log_details = f"Name: {student_details.get('name')}, Roll: {student_details.get('enrollment')}, Subsection: {student_details.get('subsection', 'N/A')}"

    # Logic for handling different event types (keystroke, paste, etc.) is unchanged
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

# --- Socket.IO Events (Unchanged) ---
# All your socket.io handlers remain the same.
@socketio.on('join_room')
def handle_join_room(data):
    room = data['room_id']
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

# --- NEW: Catch-all route to serve the React app ---
# This must be the LAST route in your file.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = 5000
    print("=====================================================")
    print("      EXAMJUDGE FULL STACK SERVER IS STARTING")
    print(f"  Application running at: http://127.0.0.1:{port}")
    print("=====================================================")
    socketio.run(app, host='0.0.0.0', port=port)