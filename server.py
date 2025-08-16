# server.py
# Receives data from student monitor and sends alerts to examiner dashboard via rooms.

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, join_room # <--- MODIFIED IMPORT
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

# --- Helper Function to Get Local IP ---
def get_local_ip():
    """Finds the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# --- Routes ---
@app.route('/dashboard/<room_id>') # <--- MODIFIED ROUTE
def dashboard(room_id):
    """Serves the main examiner dashboard, passing the room_id to the template."""
    return render_template('index.html', room_id=room_id) # <--- PASS ROOM_ID TO HTML

@app.route('/')
def index():
    """Root URL to confirm the server is running."""
    return "Monitoring server is running. Go to /dashboard/your_exam_room_id to see an examiner view."

@app.route('/log', methods=['POST'])
def log_activity():
    """Receives monitoring data from the student's application."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    student_id = data.get('student_id', 'Unknown Student')
    room_id = data.get('room_id', 'default_room') # <--- GET ROOM_ID FROM STUDENT
    event_type = data.get('event_type')
    timestamp = datetime.now().strftime('%H:%M:%S')

    print(f"Received from {student_id} in Room {room_id}: {event_type}")

    if event_type == 'keystroke':
        keystrokes = data.get('keystrokes', '')
        found_keywords = CHEATING_KEYWORDS_REGEX.findall(keystrokes)
        for keyword in set(found_keywords):
            socketio.emit('new_alert', {
                'student_id': student_id,
                'type': 'Keyword Detected',
                'message': f'Suspicious keyword "<strong>{keyword}</strong>" typed.',
                'timestamp': timestamp,
                'color': 'bg-orange-100'
            }, room=room_id) # <--- EMIT TO SPECIFIC ROOM

    elif event_type == 'paste':
        pasted_content = data.get('pasted_content', '')
        pasted_length = len(pasted_content)
        alert_type = 'High Character Paste' if pasted_length > HIGH_CHAR_PASTE_THRESHOLD else 'Paste Detected'
        message = f'A large amount of text ({pasted_length} chars) was pasted.' if pasted_length > HIGH_CHAR_PASTE_THRESHOLD else f'Pasted {pasted_length} characters.'
        color = 'bg-red-200' if pasted_length > HIGH_CHAR_PASTE_THRESHOLD else 'bg-red-100'
        socketio.emit('new_alert', {
            'student_id': student_id,
            'type': alert_type,
            'message': message,
            'timestamp': timestamp,
            'color': color,
            'paste_content': pasted_content
        }, room=room_id) # <--- EMIT TO SPECIFIC ROOM

    elif event_type == 'window_title':
        title = data.get('title', '')
        socketio.emit('new_alert', {
            'student_id': student_id,
            'type': 'Suspicious Window',
            'message': f'Active window title contains banned keyword: <strong>{title}</strong>',
            'timestamp': timestamp,
            'color': 'bg-blue-100'
        }, room=room_id) # <--- EMIT TO SPECIFIC ROOM

    return jsonify({"status": "success"}), 200

# --- Socket.IO Events ---
@socketio.on('connect')
def handle_connect():
    print('A dashboard client connected.')

@socketio.on('join_room') # <--- NEW EVENT HANDLER
def handle_join_room(data):
    """Handles a dashboard client joining a specific room."""
    room = data['room_id']
    join_room(room)
    print(f'Dashboard client has joined room: {room}')

@socketio.on('disconnect')
def handle_disconnect():
    print('Examiner dashboard disconnected.')

# --- Main Execution ---
if __name__ == '__main__':
    host_ip = get_local_ip()
    port = 5000
    print("=====================================================")
    print("          SERVER IS STARTING")
    print(f" 🖥️  Examiner Dashboard URL: http://{host_ip}:{port}/dashboard/<your_room_id>")
    print("          Share this URL with devices on the same network.")
    print("=====================================================")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)