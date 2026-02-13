"""
Events Module - BridgeGen Platform
Handles event creation, management, and registration
Author: BridgeGen Team
Date: February 2026
"""

from flask import Blueprint

events_bp = Blueprint(
    'events',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/events/static'
)

# Import routes after blueprint is created to avoid circular imports
from events import routes
