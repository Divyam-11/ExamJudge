# database.py
# Initializes the SQLite database and tables.

import sqlite3

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()

    # Create a table to store the valid room IDs
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS rooms (
                                                        id TEXT PRIMARY KEY NOT NULL
                   )
                   ''')

    # Create a table to log all student activities/alerts
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS logs (
                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                       timestamp TEXT NOT NULL,
                                                       room_id TEXT NOT NULL,
                                                       student_id TEXT NOT NULL,
                                                       event_type TEXT NOT NULL,
                                                       message TEXT NOT NULL,
                                                       details TEXT,
                                                       FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
                       )
                   ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")