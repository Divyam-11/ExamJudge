# server.py
# Now includes database logging, admin panel, and live student tracking.

import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, join_room, emit # <--- MODIFIED IMPORT
from flask_cors import CORS
import re
from datetime import datetime
import database

# --- App Initialization & DB Setup ---
database.init_db()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Constants ---
CHEATING_KEYWORDS_REGEX = re.compile(r'chatgpt|gemini|gfg|leetcode|stackoverflow|chegg', re.IGNORECASE)
HIGH_CHAR_PASTE_THRESHOLD = 100

# --- NEW: State Management for Live Students ---
# Format: { 'room_id': { 'session_id': 'student_id', ... }, ... }
room_participants = {}

# --- NEW: Helper to broadcast student list ---
def emit_student_list(room):
    """Helper function to broadcast the current student list to a room."""
    student_list = []
    if room in room_participants:
        student_list = list(room_participants[room].values())
    print(f"Updating student list for room '{room}': {sorted(student_list)}")
    socketio.emit('update_student_list', {'students': sorted(student_list)}, room=room)


# --- Database Helper (Unchanged) ---
def log_to_db(timestamp, room_id, student_id, event_type, message, details=""):
    try:
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO logs (timestamp, room_id, student_id, event_type, message, details) VALUES (?, ?, ?, ?, ?, ?)',
            (timestamp, room_id, student_id, event_type, message, details)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database logging error: {e}")

# --- Routes (Unchanged) ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        new_room_id = request.form['room_id'].strip()
        if new_room_id:
            try:
                cursor.execute('INSERT INTO rooms (id) VALUES (?)', (new_room_id,)); conn.commit()
            except sqlite3.IntegrityError: pass
        return redirect(url_for('admin'))
    cursor.execute('SELECT id FROM rooms ORDER BY id')
    rooms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('admin.html', rooms=rooms)

@app.route('/admin/delete/<room_id>', methods=['POST'])
def delete_room(room_id):
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rooms WHERE id = ?', (room_id,)); conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/dashboard/<room_id>')
def dashboard(room_id):
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM rooms WHERE id = ?', (room_id,))
    if cursor.fetchone():
        conn.close()
        return render_template('index.html', room_id=room_id)
    conn.close()
    return "Error: Room not found. Please create it in the <a href='/admin'>Admin Panel</a>.", 404

@app.route('/logs/<room_id>')
def view_logs(room_id):
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    cursor.execute('SELECT id FROM rooms WHERE id = ?', (room_id,))
    if not cursor.fetchone(): return "Error: Room not found.", 404
    cursor.execute('SELECT * FROM logs WHERE room_id = ? ORDER BY timestamp DESC', (room_id,))
    logs = cursor.fetchall()
    conn.close()
    return render_template('logs.html', logs=logs, room_id=room_id)

@app.route('/')
def index():
    return "Monitoring server is running. Go to <a href='/admin'>/admin</a> to manage rooms."

@app.route('/log', methods=['POST'])
def log_activity():
    # This function remains unchanged
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Invalid data"}), 400
    student_id = data.get('student_id', 'Unknown Student')
    room_id = data.get('room_id', 'default_room')
    event_type = data.get('event_type')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert_data = {'student_id': student_id, 'timestamp': timestamp.split(" ")[1]}
    if event_type == 'keystroke':
        keystrokes = data.get('keystrokes', '')
        found_keywords = CHEATING_KEYWORDS_REGEX.findall(keystrokes)
        for keyword in set(found_keywords):
            message = f'Suspicious keyword "{keyword}" typed.'
            alert_data.update({'type': 'Keyword Detected', 'message': f'Suspicious keyword "<strong>{keyword}</strong>" typed.', 'color': 'bg-orange-100'})
            socketio.emit('new_alert', alert_data, room=room_id)
            log_to_db(timestamp, room_id, student_id, 'Keyword Detected', message, details=f"Keyword: {keyword}")
    elif event_type == 'paste':
        pasted_content = data.get('pasted_content', '')
        pasted_length = len(pasted_content)
        is_high_char = pasted_length > HIGH_CHAR_PASTE_THRESHOLD
        alert_type = 'High Character Paste' if is_high_char else 'Paste Detected'
        message = f'A large amount of text ({pasted_length} chars) was pasted.' if is_high_char else f'Pasted {pasted_length} characters.'
        alert_data.update({'type': alert_type, 'message': message, 'color': 'bg-red-200' if is_high_char else 'bg-red-100', 'paste_content': pasted_content})
        socketio.emit('new_alert', alert_data, room=room_id)
        log_to_db(timestamp, room_id, student_id, alert_type, message, details=pasted_content)
    elif event_type == 'window_title':
        title = data.get('title', '')
        message = f'Active window title contains banned keyword: {title}'
        alert_data.update({'type': 'Suspicious Window', 'message': f'Active window title: <strong>{title}</strong>', 'color': 'bg-blue-100'})
        socketio.emit('new_alert', alert_data, room=room_id)
        log_to_db(timestamp, room_id, student_id, 'Suspicious Window', message, details=f"Window Title: {title}")
    return jsonify({"status": "success"}), 200

# --- Socket.IO Events ---
@socketio.on('join_room')
def handle_join_room(data):
    """Handles a dashboard client joining a room."""
    room = data['room_id']
    join_room(room)
    print(f'Dashboard client has joined room: {room}')
    emit_student_list(room) # Send current list on join

@socketio.on('student_connect')
def handle_student_connect(data):
    """Handles a student client connecting and registering."""
    room = data['room_id']
    student_id = data['student_id']
    sid = request.sid
    if room not in room_participants:
        room_participants[room] = {}
    room_participants[room][sid] = student_id
    print(f"Student '{student_id}' connected to room '{room}'.")
    emit_student_list(room)

@socketio.on('disconnect')
def handle_disconnect():
    """Handles any client disconnecting, including students."""
    sid = request.sid
    room_to_update = None
    for room, participants in room_participants.items():
        if sid in participants:
            disconnected_student = participants.pop(sid)
            room_to_update = room
            if not participants: del room_participants[room]
            print(f"Student '{disconnected_student}' disconnected from room '{room_to_update}'.")
            emit_student_list(room_to_update)
            break

# --- Main Execution (Unchanged) ---
if __name__ == '__main__':
    port = 5000
    print("=====================================================")
    print("          SERVER IS STARTING")
    print(f" 🔑 Admin Panel URL: http://127.0.0.1:{port}/admin")
    print(f" 🖥️  Dashboard URL: http://127.0.0.1:{port}/dashboard/<room_id>")
    print("=====================================================")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

