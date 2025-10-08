
# ExamJudge Use-Case Diagram

This diagram illustrates the primary use cases for the two main actors in the ExamJudge system: the Examiner and the Student.

```mermaid
left to right direction
actor Student
actor Examiner

rectangle "ExamJudge System" {
  usecase "Start Monitoring" as UC1
  usecase "Send Activity Data" as UC2
  usecase "Stop Monitoring" as UC3
  
  usecase "Manage Exam Rooms" as UC4
  usecase "View Dashboard" as UC5
  usecase "View Student List" as UC6
  usecase "Monitor Live Alerts" as UC7
  usecase "View Pasted Content" as UC8
  usecase "View Historical Logs" as UC9

  Student -- UC1
  Student -- UC3
  UC1 ..> UC2 : <<includes>>

  Examiner -- UC4
  Examiner -- UC5
  Examiner -- UC9
  
  UC5 ..> UC6 : <<includes>>
  UC5 ..> UC7 : <<includes>>
  UC7 ..> UC8 : <<extends>>
}
```

## Actor Descriptions

*   **Examiner**: A user (e.g., teacher, proctor) who sets up exam rooms, monitors student activity in real-time via the web dashboard, and reviews logs.
*   **Student**: A user taking an assessment who runs the monitoring client on their local machine.

## Use-Case Descriptions

| Use Case | Description |
| :--- | :--- |
| **Start Monitoring** | The student launches the client application, enters their ID and the exam room ID, and begins the monitoring session. |
| **Send Activity Data** | *Included in "Start Monitoring"*. The client automatically captures and sends keystrokes, clipboard pastes, and active window titles to the server. |
| **Stop Monitoring** | The student manually stops the monitoring client, ending the session. |
| **Manage Exam Rooms**| The examiner creates or deletes exam rooms through the admin panel. |
| **View Dashboard** | The examiner opens the web dashboard for a specific room to begin monitoring. |
| **View Student List** | *Included in "View Dashboard"*. The examiner sees a real-time list of all students currently connected to the exam room. |
| **Monitor Live Alerts**| *Included in "View Dashboard"*. The examiner views real-time alerts for suspicious activities like banned keywords, pasting, or suspicious window titles. |
| **View Pasted Content**| *Extends "Monitor Live Alerts"*. The examiner can optionally click on a "paste" alert to view the exact content that was pasted. |
| **View Historical Logs**| The examiner can view a persistent log of all alerts and activities that occurred during an exam session for a specific room. |

