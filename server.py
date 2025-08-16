# server.py
# Now tracks a list of connected students per room.

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
import re
from datetime import datetime
import socket

# --- App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Constants ---
CHEATING_KEYWORDS_REGEX = re.compile(r'chatgpt|gemini|gfg|leetcode|stackoverflow|chegg', re.IGNORECASE)
HIGH_CHAR_PASTE_THRESHOLD = 100

# --- State Management ---
# A dictionary to store participants in each room
# Format: { 'room_id': { 'session_id': 'student_id', ... }, ... }
room_participants = {}

# --- Helper Functions ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def emit_student_list(room):
    """Helper function to broadcast the current student list to a room."""
    student_list = []
    if room in room_participants:
        student_list = list(room_participants[room].values())

    print(f"Updating student list for room '{room}': {student_list}")
    socketio.emit('update_student_list', {'students': sorted(student_list)}, room=room)

# --- Routes (No changes here) ---
@app.route('/dashboard/<room_id>')
def dashboard(room_id):
    return render_template('index.html', room_id=room_id)

@app.route('/')
def index():
    return "Monitoring server is running. Go to /dashboard/your_exam_room_id to see an examiner view."

@app.route('/log', methods=['POST'])
def log_activity():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Invalid data"}), 400
    student_id = data.get('student_id', 'Unknown Student')
    room_id = data.get('room_id', 'default_room')
    event_type = data.get('event_type')
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"Received log from {student_id} in Room {room_id}: {event_type}")

    alert_data = {'student_id': student_id, 'timestamp': timestamp}
    message = ""

    if event_type == 'keystroke':
        keystrokes = data.get('keystrokes', '')
        found_keywords = CHEATING_KEYWORDS_REGEX.findall(keystrokes)
        for keyword in set(found_keywords):
            alert_data.update({
                'type': 'Keyword Detected', 'message': f'Suspicious keyword "<strong>{keyword}</strong>" typed.', 'color': 'bg-orange-100'
            })
            socketio.emit('new_alert', alert_data, room=room_id)

    elif event_type == 'paste':
        pasted_content = data.get('pasted_content', '')
        pasted_length = len(pasted_content)
        is_high_char = pasted_length > HIGH_CHAR_PASTE_THRESHOLD
        alert_data.update({
            'type': 'High Character Paste' if is_high_char else 'Paste Detected',
            'message': f'A large amount of text ({pasted_length} chars) was pasted.' if is_high_char else f'Pasted {pasted_length} characters.',
            'color': 'bg-red-200' if is_high_char else 'bg-red-100',
            'paste_content': pasted_content
        })
        socketio.emit('new_alert', alert_data, room=room_id)

    elif event_type == 'window_title':
        title = data.get('title', '')
        alert_data.update({
            'type': 'Suspicious Window',
            'message': f'Active window title contains banned keyword: <strong>{title}</strong>',
            'color': 'bg-blue-100'
        })
        socketio.emit('new_alert', alert_data, room=room_id)

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
    """Handles any client disconnecting."""
    sid = request.sid
    room_to_update = None
    disconnected_student = None

    # Check if the disconnected client was a student
    for room, participants in room_participants.items():
        if sid in participants:
            disconnected_student = participants.pop(sid)
            room_to_update = room
            if not participants: # If room is empty, remove it
                del room_participants[room]
            break

    if disconnected_student:
        print(f"Student '{disconnected_student}' disconnected from room '{room_to_update}'.")
        emit_student_list(room_to_update)
    else:
        print('An examiner dashboard disconnected.')

# --- Main Execution ---
if __name__ == '__main__':
    host_ip = get_local_ip()
    port = 5000
    print("=====================================================")
    print("          SERVER IS STARTING")
    print(f" 🖥️  Examiner Dashboard URL: http://{host_ip}:{port}/dashboard/<your_room_id>")
    print("=====================================================")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)