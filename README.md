# ExamJudge: Real-Time Student Monitoring System

ExamJudge is a client-server application designed to help examiners monitor students during online assessments. It tracks student activity—keystrokes, clipboard usage, and application window titles—and sends real-time alerts to a centralized dashboard if any suspicious behavior is detected.

## Features

- **Real-Time Alerts**: The examiner's dashboard updates in real-time with alerts for suspicious activities.
- **Keystroke Analysis**: Detects when students type keywords related to cheating (e.g., "chatgpt", "stackoverflow").
- **Clipboard Monitoring**: Flags instances of copied and pasted content, with special alerts for large amounts of pasted text.
- **Suspicious Window Detection**: Alerts examiners if a student opens a window with a title containing banned keywords (e.g., a web browser visiting a cheating website).
- **Simple GUI**: The student-side client is a simple Tkinter application that is easy to run.
- **Web-Based Dashboard**: The examiner's dashboard is a clean, modern web interface that can be accessed from any device on the same network.

## How It Works

The system consists of two main components:

1.  **Student Monitor (`student_monitor.py`)**: A Python GUI application that students run on their local machines. It captures keyboard, clipboard, and window title data and sends it to the server.
2.  **Server (`server.py`)**: A Flask server that receives data from all connected student monitors. It processes this data, checks for suspicious patterns, and pushes alerts to the examiner's dashboard using WebSockets.
3.  **Examiner Dashboard (`templates/index.html`)**: A web page that connects to the server via Socket.IO to display a live feed of alerts.

## Installation

Follow these steps to set up and run the project.

### Prerequisites

- Python 3.6+
- `pip` (Python package installer)

### 1. Clone the Repository

First, clone this repository to your local machine or download the source code.

```bash
git clone <repository-url>
cd ExamJudge
```

### 2. Install Dependencies

The project requires several Python libraries. You can install them all with a single command:

```bash
pip install -r requirements.txt
```

If you do not have a `requirements.txt` file, you can install the packages manually:

```bash
pip install Flask Flask-SocketIO requests pynput pyperclip pywin32
```

**Note on `pywin32`**: This library is specific to Windows and is used for monitoring window titles. This application is intended for Windows environments.

## Usage Guide

### Step 1: Start the Server

First, run the Flask server. This will start the backend that listens for data from the student monitors.

```bash
python server.py
```

When the server starts, it will print the URL for the examiner's dashboard. It will look something like this:

```
=====================================================
          SERVER IS STARTING
 🖥️  Examiner Dashboard URL: http://192.168.1.8:5000/dashboard
          Share this URL with devices on the same network.
=====================================================
```

- **Open the "Examiner Dashboard URL"** in a web browser to view the live dashboard.
- **Keep this server running** throughout the examination.

### Step 2: Run the Student Monitor

On each student's computer, run the `student_monitor.py` script.

```bash
python student_monitor.py
```

This will open a small GUI application with the following fields:

1.  **Student ID**: Enter a unique identifier for the student (e.g., "student_001", "john_doe").
2.  **Start Monitoring**: Click this button to begin monitoring. The status will change to "Monitoring" and the buttons will be disabled.
3.  **Stop Monitoring**: This button becomes active once monitoring starts. Click it to stop the client.

**Important**:
- The `SERVER_URL` in `student_monitor.py` is currently set to `http://127.0.0.1:5000/log`. If the server is running on a different machine, you **must** change this URL to the server's local IP address (e.g., `http://192.168.1.8:5000/log`).
- The student client must be able to reach the server over the network.

### Step 3: Monitor the Dashboard

As students work, any suspicious activity will appear as an alert on the examiner's dashboard in real-time. Alerts are color-coded for severity:
- **Orange**: A suspicious keyword was typed.
- **Red**: Content was pasted from the clipboard.
- **Blue**: A window with a suspicious title was opened.

For paste alerts, you can click on the alert to view the content that was pasted.

## Customization

- **Banned Keywords**: To change the keywords that trigger alerts, modify the `BANNED_KEYWORDS` list in `student_monitor.py` and the `CHEATING_KEYWORDS_REGEX` in `server.py`.
- **Server URL**: If you deploy the server to a public address, update the `SERVER_URL` constant in both `student_monitor.py` and `templates/index.html`.
- **Styling**: The dashboard's appearance can be modified by editing the Tailwind CSS classes in `templates/index.html`.
