@startuml
left to right direction

actor Student
actor Examiner

rectangle "ExamJudge System" {
  usecase "Take Exam" as UC1
  usecase "Start Monitoring" as UC2
  usecase "Stop Monitoring" as UC3
  usecase "Send Activity Data" as UC4
  
  usecase "Monitor Exam" as UC5
  usecase "View Dashboard" as UC6
  usecase "Manage Rooms" as UC7
  usecase "View Logs" as UC8
  
  usecase "Generate Alerts" as UC9
  usecase "Log Activity" as UC10
}

Student -- UC1
Student -- UC2
Student -- UC3

UC2 ..> UC4 : <<include>>

Examiner -- UC5
Examiner -- UC6
Examiner -- UC7
Examiner -- UC8

UC1 ..> UC9 : <<extend>>
UC1 ..> UC10 : <<extend>>
UC4 ..> UC9 : <<extend>>
UC4 ..> UC10 : <<extend>>

@enduml
