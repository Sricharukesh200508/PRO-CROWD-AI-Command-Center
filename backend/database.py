import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "crowd_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Image analysis history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            count INTEGER,
            pressure INTEGER,
            cpi REAL,
            tier TEXT,
            model_name TEXT
        )
    ''')
    
    # Video sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_start DATETIME DEFAULT CURRENT_TIMESTAMP,
            filename TEXT
        )
    ''')
    
    # Video timeline data linked to sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp_offset REAL,
            count INTEGER,
            pressure INTEGER,
            cpi REAL,
            tier TEXT,
            FOREIGN KEY (session_id) REFERENCES video_sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def log_image_analysis(count, pressure, cpi, tier, model_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO image_history (count, pressure, cpi, tier, model_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (count, pressure, cpi, tier, model_name))
    conn.commit()
    conn.close()

def start_video_session(filename):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO video_sessions (filename) VALUES (?)', (filename,))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def log_video_frame(session_id, offset, count, pressure, cpi, tier):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO video_timeline (session_id, timestamp_offset, count, pressure, cpi, tier)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, offset, count, pressure, cpi, tier))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get image history
    cursor.execute('SELECT * FROM image_history ORDER BY timestamp DESC LIMIT 50')
    images = [dict(row) for row in cursor.fetchall()]
    
    # Get video sessions
    cursor.execute('SELECT * FROM video_sessions ORDER BY session_start DESC LIMIT 20')
    sessions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"images": images, "sessions": sessions}

def get_session_timeline(session_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM video_timeline WHERE session_id = ? ORDER BY timestamp_offset ASC', (session_id,))
    timeline = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return timeline

def clear_all_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM image_history')
    cursor.execute('DELETE FROM video_timeline')
    cursor.execute('DELETE FROM video_sessions')
    conn.commit()
    conn.close()
