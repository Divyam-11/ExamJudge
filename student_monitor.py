# student_monitor_gui.py
# A cross-platform GUI application to monitor a student's activity for a specific room.

import tkinter as tk
from tkinter import messagebox
import threading
import time
import requests
from pynput import keyboard
import pyperclip
import pygetwindow as gw
import sys

# ===== CONFIG =====
SERVER_URL = 'http://127.0.0.1:5000/log' # IMPORTANT: Change this to your server's network IP
SEND_INTERVAL = 10
BANNED_KEYWORDS = ["chatgpt", "gemini", "gfg", "leetcode", "stackoverflow", "chegg"]

# ===== MONITORING LOGIC CLASS =====
class StudentMonitor:
    """Encapsulates all monitoring logic to be controlled by the GUI."""
    def __init__(self, student_id, room_id): # <--- MODIFIED CONSTRUCTOR
        self.student_id = student_id
        self.room_id = room_id # <--- STORE ROOM_ID
        self.key_buffer = ""
        self.buffer_lock = threading.Lock()
        self.is_running = False
        self.threads = []
        self.keyboard_listener = None
        self.send_timer = None

    def _send_data(self):
        """Sends the buffered keystrokes to the server and schedules the next send."""
        if not self.is_running:
            return

        with self.buffer_lock:
            if self.key_buffer:
                try:
                    payload = {
                        'student_id': self.student_id,
                        'room_id': self.room_id, # <--- ADD ROOM_ID TO PAYLOAD
                        'keystrokes': self.key_buffer,
                        'event_type': 'keystroke'
                    }
                    requests.post(SERVER_URL, json=payload, timeout=5)
                    self.key_buffer = ""
                except requests.exceptions.RequestException as e:
                    print(f"Error sending data: {e}")

        if self.is_running:
            self.send_timer = threading.Timer(SEND_INTERVAL, self._send_data)
            self.send_timer.start()

    def _on_press(self, key):
        """Callback function for keyboard listener."""
        with self.buffer_lock:
            try:
                self.key_buffer += key.char
            except AttributeError:
                key_name = f'[{str(key).split(".")[-1].upper()}]'
                self.key_buffer += key_name
        return self.is_running

    def _clipboard_monitor(self):
        """Monitors the clipboard for changes and sends new content."""
        try:
            previous_clipboard = pyperclip.paste()
        except pyperclip.PyperclipException:
            print("Could not access clipboard. Disabling clipboard monitor.")
            return

        while self.is_running:
            try:
                pasted_data = pyperclip.paste()
                if pasted_data and pasted_data != previous_clipboard:
                    previous_clipboard = pasted_data
                    payload = {
                        'student_id': self.student_id,
                        'room_id': self.room_id, # <--- ADD ROOM_ID TO PAYLOAD
                        'pasted_content': pasted_data,
                        'event_type': 'paste'
                    }
                    requests.post(SERVER_URL, json=payload, timeout=5)
            except (pyperclip.PyperclipException, requests.exceptions.RequestException) as e:
                print(f"Clipboard or network error: {e}")
            time.sleep(2)

    def _window_title_monitor(self):
        """Monitors the active window title for banned keywords (cross-platform)."""
        last_title = ""
        while self.is_running:
            try:
                active_window = gw.getActiveWindow()
                if active_window and active_window.title:
                    title = active_window.title.lower()
                    if title and title != last_title:
                        last_title = title
                        for keyword in BANNED_KEYWORDS:
                            if keyword in title:
                                payload = {
                                    'student_id': self.student_id,
                                    'room_id': self.room_id, # <--- ADD ROOM_ID TO PAYLOAD
                                    'event_type': 'window_title',
                                    'title': active_window.title
                                }
                                requests.post(SERVER_URL, json=payload, timeout=5)
                                break
            except Exception as e:
                print(f"Error getting window title: {e}")
            time.sleep(1)

    def start(self):
        """Starts all monitoring threads."""
        if self.is_running: return
        print(f"Starting monitor for {self.student_id} in room {self.room_id}...")
        self.is_running = True
        self.threads.append(threading.Thread(target=self._clipboard_monitor, daemon=True))
        self.threads.append(threading.Thread(target=self._window_title_monitor, daemon=True))
        for t in self.threads:
            t.start()
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        self._send_data()
        print("Monitoring started.")

    def stop(self):
        """Stops all monitoring threads and listeners."""
        if not self.is_running: return
        print("Stopping monitor...")
        self.is_running = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.send_timer:
            self.send_timer.cancel()
        print("Monitoring stopped.")

# ===== GUI APPLICATION CLASS =====
class App(tk.Tk):
    """The main GUI application window."""
    def __init__(self):
        super().__init__()
        self.title("Student Monitor")
        self.geometry("400x250") # Increased height for new field
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.monitor_instance = None
        self.create_widgets()

    def create_widgets(self):
        self.main_frame = tk.Frame(self, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        # --- NEW WIDGETS FOR ROOM ID ---
        tk.Label(self.main_frame, text="Exam Room ID:").pack(pady=(0, 5))
        self.room_id_entry = tk.Entry(self.main_frame, width=30)
        self.room_id_entry.pack()
        self.room_id_entry.insert(0, "exam_101")
        # --- END NEW WIDGETS ---

        tk.Label(self.main_frame, text="Student ID:").pack(pady=(10, 5))
        self.id_entry = tk.Entry(self.main_frame, width=30)
        self.id_entry.pack()
        self.id_entry.insert(0, "student_001")
        self.start_button = tk.Button(self.main_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(pady=10)
        self.stop_button = tk.Button(self.main_frame, text="Stop Monitoring", command=self.stop_monitoring, state="disabled")
        self.stop_button.pack()
        self.status_label = tk.Label(self.main_frame, text="Status: Stopped", fg="red")
        self.status_label.pack(pady=10)

    def start_monitoring(self):
        student_id = self.id_entry.get().strip()
        room_id = self.room_id_entry.get().strip() # <--- GET ROOM ID FROM GUI

        if not student_id or not room_id: # <--- VALIDATE BOTH FIELDS
            messagebox.showerror("Error", "Student ID and Room ID cannot be empty.")
            return

        self.monitor_instance = StudentMonitor(student_id, room_id) # <--- PASS ROOM ID
        self.monitor_instance.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.id_entry.config(state="disabled")
        self.room_id_entry.config(state="disabled") # <--- DISABLE ROOM ID FIELD
        self.status_label.config(text=f"Status: Monitoring {student_id} in Room {room_id}", fg="green")

    def stop_monitoring(self):
        if self.monitor_instance:
            self.monitor_instance.stop()
            self.monitor_instance = None
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.id_entry.config(state="normal")
        self.room_id_entry.config(state="normal") # <--- RE-ENABLE ROOM ID FIELD
        self.status_label.config(text="Status: Stopped", fg="red")

    def _on_closing(self):
        if self.monitor_instance and self.monitor_instance.is_running:
            if messagebox.askokcancel("Quit", "Monitoring is active. Do you want to stop it and exit?"):
                self.stop_monitoring()
                self.destroy()
        else:
            self.destroy()

# ===== MAIN =====
if __name__ == "__main__":
    app = App()
    app.mainloop()