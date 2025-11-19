import sqlite3

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()

    # Modified: Added 'owner_id' column
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS rooms (
                                                        id TEXT PRIMARY KEY NOT NULL,
                                                        owner_id TEXT NOT NULL
                   )
                   ''')

    # Logs table remains the same
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