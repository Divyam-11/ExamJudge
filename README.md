# ExamJudge: Real-Time Student Monitoring System

ExamJudge is a client-server application designed to help examiners monitor students during online assessments. It now supports room-based monitoring, allowing multiple exams to be managed from a single server. It tracks student activity—keystrokes, clipboard usage, and application window titles—and sends real-time alerts to a centralized dashboard if any suspicious behavior is detected.

## Features

- **Multi-Room Monitoring**: Create unique rooms for different exams. Each room has its own dashboard and student list.
- **Live Student Presence**: The dashboard displays a real-time list of all students connected to a specific exam room.
- **Real-Time Alerts**: The examiner's dashboard updates in real-time with alerts for suspicious activities.
- **Keystroke Analysis**: Detects when students type keywords related to cheating (e.g., "chatgpt", "stackoverflow").
- **Clipboard Monitoring**: Flags instances of copied and pasted content, with special alerts for large amounts of pasted text.
- **Suspicious Window Detection**: Alerts examiners if a student opens a window with a title containing banned keywords.
- **Simple GUI**: The student-side client is a simple Tkinter application that is easy to run.
- **Web-Based Dashboard**: The examiner's dashboard is a clean, modern web interface that can be accessed from any device on the same network.

## How It Works

The system consists of two main components:

1.  **Student Monitor (`student_monitor.py`)**: A Python GUI application that students run on their local machines. It now connects to the server via Socket.IO to register presence and sends keyboard, clipboard, and window title data via HTTP POST requests.
2.  **Server (`server.py`)**: A Flask server that uses Socket.IO to manage rooms and student connections. It receives activity data from student monitors, checks for suspicious patterns, and pushes alerts to the correct examiner dashboard.
3.  **Examiner Dashboard (`templates/index.html`)**: A web page that connects to the server via Socket.IO to join a specific room and display a live feed of alerts and connected students.

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
 🖥️  Examiner Dashboard URL: http://192.168.1.8:5000/dashboard/<your_room_id>
=====================================================
```

- **Choose a unique `room_id`** for your exam (e.g., `final_exam_math_101`).
- **Open the Examiner Dashboard URL** in a web browser, replacing `<your_room_id>` with your chosen ID. For example: `http://192.168.1.8:5000/dashboard/final_exam_math_101`.
- **Keep this server running** throughout the examination.

### Step 2: Run the Student Monitor

On each student's computer, run the `student_monitor.py` script.

```bash
python student_monitor.py
```

This will open a small GUI application with the following fields:

1.  **Exam Room ID**: Enter the **exact same room ID** you chose for the dashboard.
2.  **Student ID**: Enter a unique identifier for the student (e.g., "student_001", "john_doe").
3.  **Start Monitoring**: Click this button to begin monitoring. The status will change to "Monitoring" and the buttons will be disabled.
4.  **Stop Monitoring**: This button becomes active once monitoring starts. Click it to stop the client.

**Important**:
- The `SERVER_ADDRESS` in `student_monitor.py` is currently set to `http://127.0.0.1:5000`. If the server is running on a different machine, you **must** change this URL to the server's local IP address (e.g., `http://192.168.1.8:5000`).
- The student client must be able to reach the server over the network.

### Step 3: Monitor the Dashboard

As students connect and start working, their names will appear in the "Connected Students" list on the dashboard. Any suspicious activity will appear as an alert in real-time. Alerts are color-coded for severity:
- **Orange**: A suspicious keyword was typed.
- **Red**: Content was pasted from the clipboard.
- **Blue**: A window with a suspicious title was opened.

For paste alerts, you can click on the alert to view the content that was pasted.

## Customization

- **Banned Keywords**: To change the keywords that trigger alerts, modify the `BANNED_KEYWORDS` list in `student_monitor.py` and the `CHEATING_KEYWORDS_REGEX` in `server.py`.
- **Server URL**: If you deploy the server to a public address, update the `SERVER_ADDRESS` constant in `student_monitor.py` and the `socket` connection URL in `templates/index.html`.
- **Styling**: The dashboard's appearance can be modified by editing the Tailwind CSS classes in `templates/index.html`.