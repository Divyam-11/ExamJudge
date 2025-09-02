# Project Write-Up

## Project Name
**ExamJudge: Real-Time Student Monitoring System**

## Group No.
**[Enter Group Number]**

## Team No.
**[Enter Team Number]**

---

## Executive Summary
The integrity of online assessments is a significant concern for educational institutions and certification programs. Traditional proctoring solutions can be expensive and intrusive. ExamJudge is a client-server application designed to address this challenge by providing a lightweight, real-time student monitoring system. It allows examiners to supervise online exams by tracking student activities such as keystrokes, clipboard usage, and application window titles. The system is built with a focus on ease of use and deployment, featuring a simple student-side client and a web-based examiner dashboard. By detecting and flagging suspicious behavior in real-time, ExamJudge aims to deter academic dishonesty and ensure a fair testing environment for all participants.

---

## Present a Solution
ExamJudge's solution is composed of two main components: a student-side monitoring agent and a centralized server with a web-based dashboard for examiners.

- **What problem does it address?**
  The project addresses the difficulty of monitoring students during online exams, where it is easy for students to access unauthorized resources (e.g., web browsers, messaging apps) without being detected.

- **How does it work?**
  1.  **Student Monitor (`student_monitor.py`):** A Python application that students run on their computers. It captures keyboard inputs, clipboard content, and active window titles.
  2.  **Server (`server.py`):** A Flask server that receives data from all student monitors. It analyzes the data for suspicious patterns, such as the use of banned keywords (e.g., "chatgpt", "stackoverflow") or large paste operations.
  3.  **Examiner Dashboard (`templates/index.html`):** When the server detects suspicious activity, it pushes a real-time alert to the examiner's web dashboard. The dashboard also displays a list of all connected students.

- **Key features and functionalities:**
    - **Room-based Monitoring:** Create unique rooms for different exams.
    - **Real-Time Alerts:** Instant notifications for suspicious activities.
    - **Multi-faceted Monitoring:** Tracks keystrokes, clipboard pastes, and window titles.
    - **Web-Based Dashboard:** Accessible from any modern web browser.
    - **Simple Client UI:** A minimal and easy-to-use interface for students.

---

## Novelty / Unique Selling Point (USP)
The novelty of ExamJudge lies in its simplicity and its focus on real-time, actionable alerts.

- **What differentiates it from existing solutions?**
  Unlike many commercial proctoring services that rely on video and audio surveillance, ExamJudge is a more lightweight and less intrusive solution. It focuses on direct indicators of cheating, such as accessing specific websites or pasting pre-written answers. The room-based system also provides a flexible and scalable way to manage multiple exams simultaneously.

- **Highlight any unique technologies, processes, or approaches.**
  The use of **Socket.IO** for real-time communication between the server and the examiner's dashboard ensures that alerts are delivered instantly. The combination of monitoring multiple activity types (keystrokes, clipboard, and window titles) provides a more comprehensive picture of student behavior than single-method solutions.

---

## Objectives
1.  To develop a robust client-server application for real-time monitoring of students during online assessments.
2.  To implement a system for detecting suspicious activities, including the use of banned keywords, clipboard pasting, and accessing unauthorized applications.
3.  To create a user-friendly web-based dashboard for examiners to view real-time alerts and a list of connected students.
4.  To design a simple and intuitive GUI for the student-side monitoring client.
5.  To ensure the system is scalable and can support multiple exam rooms simultaneously.

---

## Methodology
- **Research and analysis steps:** The project started with an analysis of the common methods students use to cheat in online exams. This informed the decision to focus on monitoring keystrokes, clipboard activity, and window titles.
- **Tools, technologies, and frameworks used:**
    - **Backend:** Python, Flask, Flask-SocketIO
    - **Frontend:** React, Socket.IO Client
    - **Student Client:** Python, Tkinter, pynput, pyperclip, pygetwindow
- **Development and testing process:** The development process was iterative. The server and client were developed in parallel, with regular testing to ensure that data was being transmitted and processed correctly. The final phase involved end-to-end testing with multiple clients connected to the server.

---

## Project Deliverables / Outcomes
- **Product or prototype:**
    - A functional `server.py` application.
    - A functional `student_monitor.py` application.
    - A web-based examiner dashboard (`index.html`).
- **Documentation:**
    - A `README.md` file with detailed setup and usage instructions.
    - A `writeup.md` file (this document) detailing the project.
- **Reports/analysis:** The system provides real-time analysis of student activity through the alerts on the dashboard.

---

## Look and Feel of Product / Product Perspective
- **Student Monitor:** The student-side client has a minimal and straightforward GUI built with Tkinter. It requires the student to enter a room ID and their student ID, and then start the monitoring with a single button click.
- **Examiner Dashboard:** The examiner's dashboard is a modern, single-page web application. It is designed to be clean and easy to read, with a real-time feed of alerts and a clear list of connected students. The use of color-coded alerts helps the examiner quickly identify the severity of different events.
- **Platform:** The student client is a desktop application (cross-platform thanks to Python), and the examiner dashboard is a web application accessible from any device with a web browser.

---

## Scope of Application
- **Target industries or users:**
    - Educational institutions (schools, colleges, universities)
    - Online course providers and MOOCs
    - Corporate training and certification programs
- **Use cases:**
    - Monitoring online exams and quizzes.
    - Ensuring compliance during remote work assessments.
    - Proctoring online coding tests and technical interviews.
- **Future scalability potential:** The room-based architecture allows the system to be scaled to handle a large number of concurrent exams. Future enhancements could include a centralized database for storing and reviewing past exam sessions, and more advanced analytics to detect patterns of cheating.

---

## Timeline / Gantt Chart
| Phase              | Duration (Weeks) | Timeline         |
|--------------------|-----------------|----------------- |
| Requirement Analysis | 1               | Week 1          |
| Design & Prototyping | 2               | Week 2 - Week 3 |
| Development         | 4               | Week 4 - Week 7 |
| Testing & Refinement | 2               | Week 8 - Week 9 |
| Final Deployment    | 1               | Week 10         |

---