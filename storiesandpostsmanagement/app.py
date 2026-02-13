"""
Stories & Posts Management - Flask Blueprint
Converted from standalone Flask app to Blueprint for integration with BridgeGen.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    get_flashed_messages, jsonify, session
)
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sys
import sqlite3
from datetime import datetime

# Ensure this package's directory is on the path for local imports
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

# Import configuration and services
from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, DATABASE_PATH
from services.story_service import StoryService
from services.comment_service import CommentService
from models.story_post import StoryPost
from auth_stub import get_current_user_id, is_mod

# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
stories_bp = Blueprint(
    'stories',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/stories-static'  # Avoid conflict with main app's /static
)

# Initialize services
story_service = StoryService()
comment_service = CommentService()


def _get_db():
    """Get a direct database connection for moderation queries."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Auth decorator (reads session set by BridgeGen main app)
# ---------------------------------------------------------------------------
def login_required(f):
    """Require login - redirects to main app's login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))  # Main app's login route
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Initialize DB on first request
# ---------------------------------------------------------------------------
@stories_bp.before_app_request
def _init_stories_db_once():
    """Initialize stories database tables on first request (runs once)."""
    if not getattr(stories_bp, '_db_initialized', False):
        # Ensure upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        from init_db import init_db
        init_db()
        stories_bp._db_initialized = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@stories_bp.route('/')
@login_required
def list_stories():
    """List all stories with search, filter, and sort options."""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')
    sort_by = request.args.get('sort', 'recent')

    stories = story_service.list_stories(
        search=search if search else None,
        category=category if category else None,
        sort_by=sort_by
    )

    categories = story_service.get_categories()

    return render_template(
        'stories/list.html',
        stories=stories,
        categories=categories,
        current_search=search,
        current_category=category,
        current_sort=sort_by
    )


@stories_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_story():
    """Create a new story."""
    categories = story_service.get_categories()
    privacy_options = story_service.get_privacy_options()

    if request.method == 'POST':
        caption = request.form.get('caption', '')
        description = request.form.get('description', '')
        category = request.form.get('category', '')
        privacy = request.form.get('privacy', '')
        event_title = request.form.get('event_title', '')
        scheduled_at = request.form.get('scheduled_at', '')

        tags_input = request.form.get('tags', '')
        tags = [t.strip() for t in tags_input.replace(',', ' ').split() if t.strip()]

        allowed_groups_input = request.form.get('allowed_groups', '')
        allowed_groups = [g.strip() for g in allowed_groups_input.split(',') if g.strip()]

        media_files = request.files.getlist('media')
        media_files = [f for f in media_files if f and f.filename]

        story, errors, newly_earned_badges = story_service.create_story(
            caption=caption,
            description=description,
            category=category,
            privacy=privacy,
            tags=tags,
            event_title=event_title if event_title else None,
            allowed_groups=allowed_groups,
            scheduled_at=scheduled_at if scheduled_at else None,
            media_files=media_files if media_files else None,
            current_user_id=get_current_user_id(),
        )

        if errors:
            return render_template(
                'stories/create.html',
                categories=categories,
                privacy_options=privacy_options,
                errors=errors,
                form_data=request.form
            )

        flash('Post was created successfully', 'success')
        if newly_earned_badges:
            names = ', '.join(b.get('title', '') for b in newly_earned_badges)
            flash(f'New badge(s) earned: {names}', 'success')
        return redirect(url_for('stories.view_story', story_id=story.id))

    return render_template(
        'stories/create.html',
        categories=categories,
        privacy_options=privacy_options,
        errors={},
        form_data={}
    )


@stories_bp.route('/<int:story_id>')
@login_required
def view_story(story_id):
    """View an individual story."""
    story = story_service.get_story(story_id)

    if not story:
        flash('Story not found', 'error')
        return redirect(url_for('stories.list_stories'))

    if story.is_deleted and not is_mod():
        flash('Story not found', 'error')
        return redirect(url_for('stories.list_stories'))

    return render_template('stories/view.html', story=story)


@stories_bp.route('/<int:story_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_story(story_id):
    """Edit an existing story."""
    story = story_service.get_story(story_id)

    if not story:
        flash('Story not found', 'error')
        return redirect(url_for('stories.list_stories'))

    if story.is_deleted:
        flash('Cannot edit a deleted story', 'error')
        return redirect(url_for('stories.list_stories'))

    current_user_id = get_current_user_id()
    if story.author_id and current_user_id and current_user_id != story.author_id and not is_mod():
        flash('You do not have permission to edit this story', 'error')
        return redirect(url_for('stories.view_story', story_id=story_id))

    categories = story_service.get_categories()
    privacy_options = story_service.get_privacy_options()
    is_editable = story.is_editable()

    if request.method == 'POST':
        caption = request.form.get('caption', story.caption)
        description = request.form.get('description', story.description)
        category = request.form.get('category', story.category)
        privacy = request.form.get('privacy', story.privacy)

        tags_input = request.form.get('tags', '')
        tags = [t.strip() for t in tags_input.replace(',', ' ').split() if t.strip()]

        allowed_groups_input = request.form.get('allowed_groups', '')
        allowed_groups = [g.strip() for g in allowed_groups_input.split(',') if g.strip()]

        media_files = request.files.getlist('media')
        media_files = [f for f in media_files if f and f.filename]

        updated_story, errors = story_service.update_story(
            story_id=story_id,
            caption=caption if is_editable else None,
            description=description if is_editable else None,
            category=category,
            privacy=privacy,
            tags=tags,
            allowed_groups=allowed_groups,
            media_files=media_files if media_files else None
        )

        if errors:
            return render_template(
                'stories/edit.html',
                story=story,
                categories=categories,
                privacy_options=privacy_options,
                is_editable=is_editable,
                errors=errors
            )

        flash('Post was updated successfully', 'update')
        return redirect(url_for('stories.view_story', story_id=story_id))

    return render_template(
        'stories/edit.html',
        story=story,
        categories=categories,
        privacy_options=privacy_options,
        is_editable=is_editable,
        errors={}
    )


@stories_bp.route('/<int:story_id>/delete', methods=['POST'])
@login_required
def delete_story(story_id):
    """Soft delete a story."""
    story = story_service.get_story(story_id)

    if not story:
        flash('Story not found', 'error')
        return redirect(url_for('stories.list_stories'))

    current_user_id = get_current_user_id()
    if story.author_id and current_user_id and current_user_id != story.author_id and not is_mod():
        flash('You do not have permission to delete this story', 'error')
        return redirect(url_for('stories.view_story', story_id=story_id))

    success, title = story_service.delete_story(story_id)

    if success:
        flash(f'"{title}" was successfully deleted', 'delete')
    else:
        flash('Failed to delete story', 'error')

    if is_mod():
        return redirect(url_for('stories.mod_manage_posts'))
    return redirect(url_for('stories.list_stories'))


@stories_bp.route('/deleted')
@login_required
def deleted_stories():
    """View recently deleted stories."""
    stories = story_service.list_deleted_stories()
    return render_template('stories/deleted.html', stories=stories)


@stories_bp.route('/<int:story_id>/restore', methods=['POST'])
@login_required
def restore_story(story_id):
    """Restore a soft-deleted story."""
    story = story_service.get_story(story_id)

    if not story:
        flash('Story not found', 'error')
        return redirect(url_for('stories.deleted_stories'))

    current_user_id = get_current_user_id()
    if story.author_id and current_user_id and current_user_id != story.author_id and not is_mod():
        flash('You do not have permission to restore this story', 'error')
        return redirect(url_for('stories.deleted_stories'))

    success, message = story_service.restore_story(story_id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('stories.deleted_stories'))


@stories_bp.route('/purge-expired', methods=['POST'])
@login_required
def purge_expired():
    """Permanently delete expired soft-deleted stories (admin endpoint)."""
    count = story_service.purge_expired_stories()
    flash(f'Permanently deleted {count} expired stories', 'success')
    return redirect(url_for('stories.deleted_stories'))


@stories_bp.route('/<int:story_id>/like', methods=['POST'])
@login_required
def like_story(story_id):
    """Like or unlike a story (AJAX endpoint)."""
    if request.is_json:
        action = request.json.get('action', 'like')
    else:
        action = request.form.get('action', 'like')

    if action == 'unlike':
        new_count, newly_earned_badges = story_service.unlike_story(story_id)
    else:
        new_count, newly_earned_badges = story_service.like_story(story_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': True,
            'likes_count': new_count,
            'liked': action == 'like',
            'newly_earned_badges': newly_earned_badges or [],
        })
    return redirect(url_for('stories.view_story', story_id=story_id))


@stories_bp.route('/<int:story_id>/share', methods=['POST'])
@login_required
def share_story(story_id):
    """Share a story (AJAX endpoint)."""
    new_count, newly_earned_badges = story_service.share_story(story_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': True,
            'shares_count': new_count,
            'newly_earned_badges': newly_earned_badges or [],
        })
    return redirect(url_for('stories.view_story', story_id=story_id))


@stories_bp.route('/<int:story_id>/comments')
@login_required
def get_comments(story_id):
    """Get comments for a story (AJAX endpoint)."""
    comments = comment_service.get_comments(story_id)
    comments_data = [c.to_dict() for c in comments]
    return jsonify({
        'success': True,
        'comments': comments_data
    })


@stories_bp.route('/<int:story_id>/comments', methods=['POST'])
@login_required
def add_comment(story_id):
    """Add a comment to a story (AJAX endpoint)."""
    if request.is_json:
        author_name = request.json.get('author_name', '')
        content = request.json.get('content', '')
    else:
        author_name = request.form.get('author_name', '')
        content = request.form.get('content', '')

    comment, errors, newly_earned_badges = comment_service.add_comment(
        story_id=story_id,
        author_name=author_name,
        content=content,
        author_id=get_current_user_id(),
    )

    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400

    story = story_service.get_story(story_id)

    return jsonify({
        'success': True,
        'comment': comment.to_dict(),
        'comments_count': story.comments_count if story else 0,
        'newly_earned_badges': newly_earned_badges or [],
    })


@stories_bp.route('/<int:story_id>/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(story_id, comment_id):
    """Delete a comment (AJAX endpoint)."""
    from repositories.comment_repository import CommentRepository
    comment_repo = CommentRepository()
    comment = comment_repo.find_by_id(comment_id)

    if not comment:
        return jsonify({'success': False, 'error': 'Comment not found'}), 404

    current_user_id = get_current_user_id()
    if comment.author_id and current_user_id and current_user_id != comment.author_id and not is_mod():
        return jsonify({'success': False, 'error': 'You do not have permission to delete this comment'}), 403

    success = comment_service.delete_comment(comment_id)
    story = story_service.get_story(story_id)

    return jsonify({
        'success': success,
        'comments_count': story.comments_count if story else 0
    })


@stories_bp.route('/viewer')
@stories_bp.route('/viewer/<int:story_id>')
@login_required
def story_viewer(story_id=None):
    """Instagram-style story viewer with carousel navigation."""
    import json

    stories = story_service.list_stories(sort_by='recent')

    if not stories:
        flash('No stories available', 'error')
        return redirect(url_for('stories.list_stories'))

    stories_data = []
    for story in stories:
        stories_data.append({
            'id': story.id,
            'caption': story.caption,
            'description': story.description,
            'media_paths': story.media_paths,
            'tags': story.tags,
            'category': story.category,
            'likes_count': story.likes_count,
            'shares_count': story.shares_count,
            'created_at': story.created_at
        })

    initial_index = 0
    if story_id:
        for i, story in enumerate(stories_data):
            if story['id'] == story_id:
                initial_index = i
                break

    return render_template(
        'stories/story_viewer.html',
        stories_json=json.dumps(stories_data),
        initial_index=initial_index
    )


# ---------------------------------------------------------------------------
# Moderation Routes (moderator-only)
# ---------------------------------------------------------------------------

def moderator_required(f):
    """Require moderator access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_type') != 'moderator':
            flash('Access denied. Moderator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@stories_bp.route('/moderation/manage')
@moderator_required
def mod_manage_posts():
    """Manage Posts and Stories - main moderation hub."""
    admin_name = session.get('full_name', 'Admin Name')
    return render_template('moderation/manage.html', admin_name=admin_name)


@stories_bp.route('/moderation/flagged')
@moderator_required
def mod_flagged_posts():
    """View all flagged posts and stories."""
    admin_name = session.get('full_name', 'Admin Name')
    db = _get_db()
    flagged_stories = db.execute(
        'SELECT * FROM stories WHERE flagged = 1 AND is_deleted = 0 ORDER BY flagged_at DESC'
    ).fetchall()
    return render_template('moderation/flagged.html',
                         flagged_stories=flagged_stories,
                         admin_name=admin_name)


@stories_bp.route('/moderation/delete')
@moderator_required
def mod_delete_posts():
    """View all posts for deletion."""
    admin_name = session.get('full_name', 'Admin Name')
    db = _get_db()
    stories = db.execute(
        'SELECT * FROM stories WHERE is_deleted = 0 ORDER BY created_at DESC'
    ).fetchall()
    return render_template('moderation/delete.html',
                         stories=stories,
                         admin_name=admin_name)


@stories_bp.route('/moderation/admin-settings')
@moderator_required
def mod_admin_settings():
    """Admin settings page - flagged posts, badge management."""
    admin_name = session.get('full_name', 'Admin Name')
    return render_template('moderation/admin_settings.html', admin_name=admin_name)


@stories_bp.route('/moderation/<int:story_id>/flag', methods=['POST'])
@login_required
def mod_flag_post(story_id):
    """Flag a post for moderation review (any logged-in user can report)."""
    reason = request.form.get('reason', 'Flagged for inappropriate content')
    db = _get_db()
    db.execute(
        'UPDATE stories SET flagged = 1, flag_reason = ?, flagged_at = ? WHERE id = ?',
        (reason, datetime.now().isoformat(), story_id)
    )
    db.commit()
    flash('Post has been reported for review.', 'success')
    if is_mod():
        return redirect(url_for('stories.mod_flagged_posts'))
    return redirect(url_for('stories.list_stories'))


@stories_bp.route('/moderation/<int:story_id>/unflag', methods=['POST'])
@moderator_required
def mod_unflag_post(story_id):
    """Unflag a post (moderator only)."""
    db = _get_db()
    db.execute(
        'UPDATE stories SET flagged = 0, flag_reason = NULL, flagged_at = NULL WHERE id = ?',
        (story_id,)
    )
    db.commit()
    flash('Post has been unflagged.', 'success')
    return redirect(url_for('stories.mod_flagged_posts'))


@stories_bp.route('/moderation/<int:story_id>/remove', methods=['POST'])
@moderator_required
def mod_remove_post(story_id):
    """Permanently soft-delete a post (moderator only)."""
    db = _get_db()
    db.execute(
        'UPDATE stories SET is_deleted = 1, deleted_at = ? WHERE id = ?',
        (datetime.now().isoformat(), story_id)
    )
    db.commit()
    flash('Post has been removed.', 'delete')
    return redirect(request.referrer or url_for('stories.mod_manage_posts'))


# ---------------------------------------------------------------------------
# Register sub-blueprints (gamification)
# ---------------------------------------------------------------------------
try:
    from blueprints.gamification_bp import gamification_bp
    stories_bp.register_blueprint(gamification_bp)
except ImportError:
    pass  # Gamification module not available
