import os

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'stories.db')

# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

# Allowed file extensions for media uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov', 'avi'}

# Valid categories for stories
VALID_CATEGORIES = [
    'Life Lessons',
    'Historical Events',
    'Family Traditions',
    'Career Journey',
    'Hobbies & Skills',
    'Travel Adventures'
]

# Valid privacy settings
VALID_PRIVACY_OPTIONS = ['Public', 'Friends Only', 'Specific Groups']

# Business rules
EDIT_LOCK_HOURS = 24  # Hours after which caption/description are locked
SOFT_DELETE_DAYS = 7  # Days before permanent deletion

# Flask secret key (MUST be set in production via environment variable)
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
if not SECRET_KEY:
    # Development fallback - generates a random key per session
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: Using auto-generated SECRET_KEY. Set FLASK_SECRET_KEY environment variable in production!")

# Gamification: achievement rule types (extensible)
ACHIEVEMENT_RULE_TYPES = [
    'stories_created_total',
    'comments_written_total',
    'likes_received_total',
    'shares_received_total',
    'days_active_streak',
]
