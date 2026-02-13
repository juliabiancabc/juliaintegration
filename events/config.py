"""
Events Configuration
"""
import os

# Upload folder for event images
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'events')

# Database path (uses main BridgeGen database)
DATABASE_PATH = os.path.join('bridgegen.db')

# Max upload size
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
