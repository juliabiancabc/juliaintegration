"""
Auth helpers integrated with BridgeGen's session-based authentication.
Reads user_id and user_type from Flask session set by the main app's login system.
"""
from typing import Optional
from flask import session, abort


def get_current_user_id() -> Optional[int]:
    """
    Return the current logged-in user's ID from session.
    Returns None if no user is logged in.
    """
    return session.get('user_id')


def is_mod() -> bool:
    """
    Return True if the current user is a moderator.
    Checks user_type set by BridgeGen's login system.
    """
    return session.get('user_type') == 'moderator'


def require_mod():
    """Abort with 403 if the current user is not a moderator."""
    if not is_mod():
        abort(403, description="Moderator access required")
