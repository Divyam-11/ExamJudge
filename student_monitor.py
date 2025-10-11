# student_monitor_gui.py
# A complete UI overhaul for a more aesthetic and user-friendly experience.

import sys
import threading
import time
import requests
import os.path
import pandas as pd

from pynput import keyboard
import pyperclip
import pygetwindow as gw
import socketio
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget, QHBoxLayout, QFrame
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont, QIcon

# --- Google Auth Imports ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==============================================================================
# ===== CONFIG (Unchanged) =====
# ==============================================================================
SERVER_ADDRESS = 'http://144.24.111.11:5000'
EXCEL_FILE_PATH = 'student_data.xlsx'
EMAIL_COLUMN_NAME = 'STTIETEMAILID'
STUDENT_NAME_COLUMN = 'STUDENTNAME'
ENROLLMENT_COLUMN = 'ENROLLMENTNO'
SUBSECTION_COLUMN = 'Sub Section'
# ==============================================================================

# ===== CONFIG =====
SERVER_ADDRESS = 'http://144.24.111.11:5000' # IMPORTANT: Change this to your server's network IP # IMPORTANT: Change this to your server's network IP
SERVER_URL = f'{SERVER_ADDRESS}/log'
SEND_INTERVAL = 10
BANNED_KEYWORDS = ["chatgpt", "gemini", "gfg", "leetcode", "stackoverflow", "chegg"]
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']


# --- For PyQt Signal Handling (Unchanged) ---
class MonitorSignal(QObject):
    connection_failed = pyqtSignal()
    lookup_success = pyqtSignal(dict)
    lookup_failure = pyqtSignal(str)

# ===== MONITORING LOGIC CLASS (Unchanged) =====
class StudentMonitor:
    # This entire class is unchanged.
    def __init__(self, student_details, room_id, signal_emitter):
        self.student_details = student_details; self.room_id = room_id; self.key_buffer = ""; self.buffer_lock = threading.Lock()
        self.is_running = False; self.threads = []; self.keyboard_listener = None; self.send_timer = None
        self.sio = socketio.Client(); self.setup_sio_events(); self.signals = signal_emitter
    def _send_payload(self, event_type, data):
        try:
            payload = {'room_id': self.room_id, 'event_type': event_type, 'student_details': self.student_details}; payload.update(data)
            requests.post(SERVER_URL, json=payload, timeout=5)
        except requests.exceptions.RequestException as e: print(f"Error sending data: {e}")
    def setup_sio_events(self):
        @self.sio.event
        def connect(): print("Socket.IO connection established..."); self.sio.emit('student_connect', {'room_id': self.room_id, 'student_details': self.student_details})
        @self.sio.event
        def disconnect(): print("Socket.IO disconnected.")
    def _send_data(self):
        if not self.is_running: return
        with self.buffer_lock:
            if self.key_buffer: self._send_payload('keystroke', {'keystrokes': self.key_buffer}); self.key_buffer = ""
        if self.is_running: self.send_timer = threading.Timer(SEND_INTERVAL, self._send_data); self.send_timer.start()
    def _on_press(self, key):
        with self.buffer_lock:
            try: self.key_buffer += key.char
            except AttributeError: self.key_buffer += f'[{str(key).split(".")[-1].upper()}]'
        return self.is_running
    def _clipboard_monitor(self):
        try: previous_clipboard = pyperclip.paste()
        except pyperclip.PyperclipException: return
        while self.is_running:
            try:
                pasted_data = pyperclip.paste()
                if pasted_data and pasted_data != previous_clipboard: previous_clipboard = pasted_data; self._send_payload('paste', {'pasted_content': pasted_data})
            except (pyperclip.PyperclipException, requests.exceptions.RequestException): pass
            time.sleep(2)
    def _window_title_monitor(self):
        last_title = ""
        while self.is_running:
            try:
                active_window = gw.getActiveWindow()
                if active_window and active_window.title:
                    title = active_window.title.lower()
                    if title and title != last_title:
                        last_title = title
                        for keyword in BANNED_KEYWORDS:
                            if keyword in title: self._send_payload('window_title', {'title': active_window.title}); break
            except Exception: pass
            time.sleep(1)
    def start(self):
        if self.is_running: return
        print(f"Starting monitor for {self.student_details.get('email')}..."); self.is_running = True
        try: self.sio.connect(SERVER_ADDRESS)
        except socketio.exceptions.ConnectionError as e: print(f"Failed to connect to server: {e}"); self.is_running = False; self.signals.connection_failed.emit(); return
        self.threads.append(threading.Thread(target=self._clipboard_monitor, daemon=True)); self.threads.append(threading.Thread(target=self._window_title_monitor, daemon=True))
        for t in self.threads: t.start()
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press); self.keyboard_listener.start(); self._send_data(); print("Monitoring started.")
    def stop(self):
        if not self.is_running: return
        print("Stopping monitor..."); self.is_running = False
        if self.sio.connected: self.sio.disconnect()
        if self.keyboard_listener: self.keyboard_listener.stop()
        if self.send_timer: self.send_timer.cancel()
        print("Monitoring stopped.")

# --- AESTHETIC GUI CLASS ---
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.monitor_instance = None
        self.student_details = None
        self.signals = MonitorSignal()
        self.signals.connection_failed.connect(self.handle_connection_failure)
        self.signals.lookup_success.connect(self.handle_lookup_success)
        self.signals.lookup_failure.connect(self.handle_lookup_failure)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Exam Monitor')
        self.setGeometry(300, 300, 450, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #F0F4F8;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #B0C4DE;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #DCE1E6;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #333;
            }
            QFrame#profileCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #EAEFF4;
            }
        """)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.create_welcome_page())
        self.stack.addWidget(self.create_login_page())
        self.stack.addWidget(self.create_monitoring_page())

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

    def create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Welcome to the Exam Monitor")
        title.setFont(QFont('Segoe UI', 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Please ensure you have a stable internet connection and have closed all unauthorized applications before you begin.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #555;")

        lets_go_button = QPushButton("Let's Go")
        lets_go_button.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addWidget(lets_go_button, alignment=Qt.AlignCenter)
        layout.addStretch()
        return page

    def create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        title = QLabel("Setup & Login")
        title.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addSpacing(20)

        layout.addWidget(QLabel("Enter Exam Room ID:"))
        self.room_id_entry = QLineEdit('CS101-Final')
        layout.addWidget(self.room_id_entry)

        self.auth_button = QPushButton('Sign in with Google')
        self.auth_button.clicked.connect(self.authenticate_user)
        layout.addSpacing(10)
        layout.addWidget(self.auth_button, alignment=Qt.AlignCenter)

        self.login_status_label = QLabel("Please sign in to continue.")
        self.login_status_label.setAlignment(Qt.AlignCenter)
        self.login_status_label.setStyleSheet("color: #777;")
        layout.addWidget(self.login_status_label)
        layout.addStretch()
        return page

    def create_monitoring_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(30, 30, 30, 30)

        # Profile Card
        profile_card = QFrame()
        profile_card.setObjectName("profileCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setSpacing(10)
        profile_layout.setContentsMargins(25, 25, 25, 25)

        self.name_label = QLabel("Student Name")
        self.name_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        self.email_label = QLabel("student.email@example.com")
        self.email_label.setStyleSheet("color: #555;")

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        self.enrollment_label = QLabel("Enrollment: 12345")
        self.subsection_label = QLabel("Sub Section: A1")

        profile_layout.addWidget(self.name_label)
        profile_layout.addWidget(self.email_label)
        profile_layout.addSpacing(15)
        profile_layout.addWidget(separator)
        profile_layout.addSpacing(15)
        profile_layout.addWidget(self.enrollment_label)
        profile_layout.addWidget(self.subsection_label)

        # Monitoring Status
        status_frame = QWidget()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setAlignment(Qt.AlignCenter)

        status_indicator = QLabel("●") # Circle character
        status_indicator.setStyleSheet("color: #2ECC71; font-size: 24px;")

        self.monitoring_status_label = QLabel("MONITORING ACTIVE")
        self.monitoring_status_label.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.monitoring_status_label.setStyleSheet("color: #2ECC71;")

        status_layout.addWidget(status_indicator)
        status_layout.addWidget(self.monitoring_status_label)

        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.setStyleSheet("background-color: #E74C3C;")
        self.stop_button.clicked.connect(self.stop_monitoring)

        layout.addWidget(profile_card)
        layout.addSpacing(25)
        layout.addWidget(status_frame)
        layout.addSpacing(25)
        layout.addWidget(self.stop_button, alignment=Qt.AlignCenter)

        return page

    def authenticate_user(self):
        self.login_status_label.setText("Status: Waiting for Google sign-in...")
        self.login_status_label.setStyleSheet("color: #E67E22;")
        self.auth_button.setEnabled(False)
        threading.Thread(target=self._run_auth_and_lookup, daemon=True).start()

    def _run_auth_and_lookup(self):
        # This backend logic is unchanged
        creds = None
        if os.path.exists('token.json'): creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try: creds.refresh(Request())
                except Exception as e: self.signals.lookup_failure.emit(f"Token refresh failed: {e}"); return
            else:
                try:
                    if not os.path.exists('credentials.json'): self.signals.lookup_failure.emit("credentials.json not found."); return
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e: self.signals.lookup_failure.emit(f"Authentication failed: {e}"); return
            with open('token.json', 'w') as token: token.write(creds.to_json())
        try:
            service = build('oauth2', 'v2', credentials=creds)
            email = service.userinfo().get().execute().get('email')
            if not email: self.signals.lookup_failure.emit("Could not get email from Google."); return
        except HttpError as err: self.signals.lookup_failure.emit(f"Google API Error: {err}"); return

        self.login_status_label.setText(f"Signed in as {email}. Verifying...")
        try:
            df = pd.read_excel(EXCEL_FILE_PATH)
            df.columns = df.columns.str.strip()
            student_row = df[df[EMAIL_COLUMN_NAME].str.lower() == email.lower()]
            if not student_row.empty:
                details = student_row.iloc[0]
                self.signals.lookup_success.emit({
                    "email": email, "name": str(details.get(STUDENT_NAME_COLUMN, '')),
                    "enrollment": str(details.get(ENROLLMENT_COLUMN, '')), "subsection": str(details.get(SUBSECTION_COLUMN, ''))
                })
            else:
                self.signals.lookup_failure.emit("Email not found in student roster.")
        except FileNotFoundError: self.signals.lookup_failure.emit(f"'{EXCEL_FILE_PATH}' not found.")
        except Exception as e: self.signals.lookup_failure.emit(f"Could not read Excel file: {e}")

    def handle_lookup_success(self, details_dict):
        self.student_details = details_dict
        # Populate the profile page
        self.name_label.setText(self.student_details['name'])
        self.email_label.setText(self.student_details['email'])
        self.enrollment_label.setText(f"Enrollment: {self.student_details['enrollment']}")
        self.subsection_label.setText(f"Sub Section: {self.student_details['subsection']}")

        # Switch to the monitoring page and start
        self.stack.setCurrentIndex(2)
        self.start_monitoring()

    def handle_lookup_failure(self, error_message):
        QMessageBox.critical(self, "Process Failed", error_message)
        self.login_status_label.setText("Failed. Please try again.");
        self.login_status_label.setStyleSheet("color: #E74C3C;");
        self.auth_button.setEnabled(True)

    def start_monitoring(self):
        room_id = self.room_id_entry.text().strip()
        self.monitor_instance = StudentMonitor(self.student_details, room_id, self.signals)
        threading.Thread(target=self.monitor_instance.start, daemon=True).start()

    def stop_monitoring(self):
        if self.monitor_instance: self.monitor_instance.stop(); self.monitor_instance = None
        self.monitoring_status_label.setText("MONITORING STOPPED")
        self.monitoring_status_label.setStyleSheet("color: #E74C3C;")
        self.stop_button.setEnabled(False)

    def handle_connection_failure(self):
        QMessageBox.critical(self, "Connection Error", "Failed to connect to the server."); self.stop_monitoring()

    def closeEvent(self, event):
        if self.monitor_instance and self.monitor_instance.is_running:
            reply = QMessageBox.question(self, 'Quit', "Monitoring is active. Do you want to stop it and exit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes: self.stop_monitoring(); event.accept()
            else: event.ignore()
        else: event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())