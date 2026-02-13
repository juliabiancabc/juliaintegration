"""
Events Database Initialization
Creates events and registrations tables in the main BridgeGen database.
"""
import sqlite3
from config import DATABASE_PATH

def init_db():
    """Initialize events tables in the main database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            event_type TEXT DEFAULT 'physical',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            seat_amount INTEGER NOT NULL,
            is_closed BOOLEAN DEFAULT 0,
            image_filename TEXT,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # Create registrations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            special_requests TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            UNIQUE(user_id, event_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Events tables initialized successfully!")

if __name__ == '__main__':
    init_db()
