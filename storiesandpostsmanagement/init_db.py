import sqlite3
import os

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATABASE_PATH


def _column_exists(cursor, table, column):
    """Return True if column exists in table."""
    # Validate table name against whitelist to prevent SQL injection
    valid_tables = {'stories', 'comments', 'badges', 'achievements',
                    'achievement_badges', 'user_badges', 'user_achievements',
                    'user_activity_dates'}
    if table not in valid_tables:
        raise ValueError(f"Invalid table name: {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def init_db():
    # Initialize the database with stories, comments, and gamification tables.
    # Ensure data directory exists
    data_dir = os.path.dirname(DATABASE_PATH)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create stories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caption TEXT NOT NULL,
            description TEXT NOT NULL,
            tags TEXT,
            event_title TEXT,
            category TEXT NOT NULL,
            privacy TEXT NOT NULL,
            allowed_groups TEXT,
            scheduled_at TEXT,
            media_paths TEXT,
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT,
            author_id INTEGER
        )
    ''')
    # Migration: add author_id if table existed without it
    if not _column_exists(cursor, 'stories', 'author_id'):
        try:
            cursor.execute('ALTER TABLE stories ADD COLUMN author_id INTEGER')
        except sqlite3.OperationalError:
            pass
    
    # Migration: add flagged/flag_reason columns for content moderation
    if not _column_exists(cursor, 'stories', 'flagged'):
        try:
            cursor.execute('ALTER TABLE stories ADD COLUMN flagged INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
    if not _column_exists(cursor, 'stories', 'flag_reason'):
        try:
            cursor.execute('ALTER TABLE stories ADD COLUMN flag_reason TEXT')
        except sqlite3.OperationalError:
            pass
    if not _column_exists(cursor, 'stories', 'flagged_at'):
        try:
            cursor.execute('ALTER TABLE stories ADD COLUMN flagged_at TEXT')
        except sqlite3.OperationalError:
            pass
    conn.commit()
    
    # Create indexes for common queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_category ON stories(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_is_deleted ON stories(is_deleted)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_author_id ON stories(author_id)')
    
    conn.commit()
    
    # Create comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            author_id INTEGER,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        )
    ''')
    if not _column_exists(cursor, 'comments', 'author_id'):
        try:
            cursor.execute('ALTER TABLE comments ADD COLUMN author_id INTEGER')
        except sqlite3.OperationalError:
            pass
    conn.commit()
    
    # Create index for comments by story_id
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_story_id ON comments(story_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id)')
    
    conn.commit()
    
    # --- Gamification: badges ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            icon_url TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_badges_sort_order ON badges(sort_order)')
    
    # --- Gamification: achievements ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            rule_type TEXT NOT NULL,
            rule_value INTEGER NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_achievements_active ON achievements(active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_achievements_rule_type ON achievements(rule_type)')
    
    # --- Gamification: achievement_badges (many-to-many) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievement_badges (
            achievement_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            PRIMARY KEY (achievement_id, badge_id),
            FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
            FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE
        )
    ''')
    
    # --- Gamification: user_badges (unique per user per badge) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            earned_at TEXT NOT NULL,
            UNIQUE(user_id, badge_id),
            FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_badges_user_id ON user_badges(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_badges_earned_at ON user_badges(earned_at)')
    
    # --- Gamification: user_achievements (unique per user per achievement) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_id INTEGER NOT NULL,
            earned_at TEXT NOT NULL,
            UNIQUE(user_id, achievement_id),
            FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_achievements_earned_at ON user_achievements(earned_at)')
    
    # --- Gamification: user_activity_dates (for days_active_streak stub) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_dates (
            user_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            PRIMARY KEY (user_id, activity_date)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_dates_user_id ON user_activity_dates(user_id)')
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at: {DATABASE_PATH}")


if __name__ == '__main__':
    init_db()
