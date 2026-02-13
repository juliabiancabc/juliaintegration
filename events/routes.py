"""
Events Management - Flask Blueprint
Converted from wdp_julia standalone app to Blueprint for integration with BridgeGen.

Author: BridgeGen Team
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify
)
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
from io import StringIO, BytesIO
import os
import sys
import sqlite3
import csv

# Ensure this package's directory is on the path for local imports
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

# Import configuration
from config import UPLOAD_FOLDER, DATABASE_PATH

# ---------------------------------------------------------------------------
# Blueprint definition
# ---------------------------------------------------------------------------
events_bp = Blueprint(
    'events',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/events-static'
)

# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
def _get_db():
    """Get a direct database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------------------------
# Auth decorators (reads session set by BridgeGen main app)
# ---------------------------------------------------------------------------
def login_required(f):
    """Require login - redirects to main app's login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Require admin/organizer role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_type') not in ['moderator', 'organizer']:
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# Initialize DB on first request
# ---------------------------------------------------------------------------
@events_bp.before_app_request
def _init_events_db_once():
    """Initialize events database tables on first request (runs once)."""
    if not getattr(events_bp, '_db_initialized', False):
        # Ensure upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        from init_db import init_db
        init_db()
        events_bp._db_initialized = True

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_event(event_id):
    """Get event by ID."""
    db = _get_db()
    event = db.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    db.close()
    return dict(event) if event else None

def get_registration_count(event_id):
    """Get registration count for an event."""
    db = _get_db()
    count = db.execute('SELECT COUNT(*) as count FROM registrations WHERE event_id = ?', (event_id,)).fetchone()
    db.close()
    return count['count'] if count else 0

def is_registered(event_id, user_id):
    """Check if user is registered for an event."""
    db = _get_db()
    reg = db.execute('SELECT * FROM registrations WHERE event_id = ? AND user_id = ?', 
                     (event_id, user_id)).fetchone()
    db.close()
    return reg is not None

# ---------------------------------------------------------------------------
# Routes - User Events
# ---------------------------------------------------------------------------
@events_bp.route('/', endpoint='view_events')
@login_required
def view_events():
    """List all events for users."""
    db = _get_db()
    events = db.execute('SELECT * FROM events ORDER BY date ASC').fetchall()
    
    # Get user registrations
    user_id = session.get('user_id')
    registrations = db.execute('SELECT event_id FROM registrations WHERE user_id = ?', 
                              (user_id,)).fetchall()
    registered_event_ids = [r['event_id'] for r in registrations]
    
    db.close()
    
    return render_template('view_events.html', 
                         events=[dict(e) for e in events],
                         registered_event_ids=registered_event_ids)

@events_bp.route('/calendar')
@login_required
def view_calendar():
    """View calendar with registered events."""
    db = _get_db()
    user_id = session.get('user_id')
    
    registrations = db.execute('''
        SELECT e.* FROM events e
        JOIN registrations r ON e.id = r.event_id
        WHERE r.user_id = ?
        ORDER BY e.date ASC
    ''', (user_id,)).fetchall()
    
    db.close()
    
    return render_template('view_calendar.html', events=[dict(e) for e in registrations])

@events_bp.route('/event/<int:event_id>')
@login_required
def user_event_detail(event_id):
    """View event details for users."""
    event = get_event(event_id)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events.view_events'))
    
    user_id = session.get('user_id')
    is_reg = is_registered(event_id, user_id)
    
    return render_template('user_event_detail.html', event=event, is_registered=is_reg)

@events_bp.route('/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    """Register for an event."""
    user_id = session.get('user_id')
    
    if is_registered(event_id, user_id):
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.view_events'))
    
    special_requests = request.form.get('special_requests', '')
    
    db = _get_db()
    db.execute('''
        INSERT INTO registrations (user_id, event_id, special_requests, registered_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, event_id, special_requests, datetime.utcnow()))
    db.commit()
    db.close()
    
    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('events.view_events'))

@events_bp.route('/unregister/<int:event_id>')
@login_required
def unregister_event(event_id):
    """Unregister from an event."""
    user_id = session.get('user_id')
    
    db = _get_db()
    db.execute('DELETE FROM registrations WHERE event_id = ? AND user_id = ?', 
               (event_id, user_id))
    db.commit()
    db.close()
    
    flash('Successfully unregistered from the event.', 'success')
    return redirect(url_for('events.view_calendar'))

# ---------------------------------------------------------------------------
# Routes - Admin Dashboard
# ---------------------------------------------------------------------------
@events_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics."""
    db = _get_db()
    
    total_events = db.execute('SELECT COUNT(*) as count FROM events').fetchone()['count']
    total_registrations = db.execute('SELECT COUNT(*) as count FROM registrations').fetchone()['count']
    upcoming_events = db.execute(
        'SELECT COUNT(*) as count FROM events WHERE date >= ?', 
        (datetime.utcnow(),)
    ).fetchone()['count']
    
    db.close()
    
    return render_template('admin_dashboard.html',
                         total_events=total_events,
                         total_registrations=total_registrations,
                         upcoming_events=upcoming_events)

@events_bp.route('/admin/manage')
@admin_required
def manage_events():
    """Manage all events."""
    db = _get_db()
    events = db.execute('SELECT * FROM events ORDER BY created_at DESC').fetchall()
    db.close()
    
    return render_template('manage_events.html', events=[dict(e) for e in events])

@events_bp.route('/admin/events')
@admin_required
def admin_view_events():
    """Browse all events for admins."""
    sort_by = request.args.get('sort', 'newest')
    
    db = _get_db()
    if sort_by == 'oldest':
        events = db.execute('SELECT * FROM events ORDER BY date ASC').fetchall()
    elif sort_by == 'title':
        events = db.execute('SELECT * FROM events ORDER BY title ASC').fetchall()
    else:
        events = db.execute('SELECT * FROM events ORDER BY date DESC').fetchall()
    
    user_id = session.get('user_id')
    registrations = db.execute('SELECT event_id FROM registrations WHERE user_id = ?', 
                              (user_id,)).fetchall()
    registered_event_ids = [r['event_id'] for r in registrations]
    
    db.close()
    
    return render_template('admin_view_events.html',
                         events=[dict(e) for e in events],
                         sort_by=sort_by,
                         registered_event_ids=registered_event_ids)

@events_bp.route('/admin/calendar')
@admin_required
def admin_calendar():
    """Admin calendar view."""
    db = _get_db()
    user_id = session.get('user_id')
    
    registrations = db.execute('''
        SELECT e.* FROM events e
        JOIN registrations r ON e.id = r.event_id
        WHERE r.user_id = ?
        ORDER BY e.date ASC
    ''', (user_id,)).fetchall()
    
    db.close()
    
    return render_template('admin_calendar.html', events=[dict(e) for e in registrations])

@events_bp.route('/admin/create', methods=['GET', 'POST'])
@admin_required
def create_event():
    """Create a new event."""
    if request.method == 'POST':
        try:
            date_str = request.form.get('date')
            time_str = request.form.get('event_time')
            
            if date_str and time_str:
                event_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            else:
                event_datetime = datetime.utcnow()
            
            db = _get_db()
            cursor = db.execute('''
                INSERT INTO events (title, description, date, location, category, 
                                  event_type, tags, seat_amount, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.form.get('title'),
                request.form.get('description'),
                event_datetime,
                request.form.get('location'),
                request.form.get('category'),
                request.form.get('event_type', 'physical'),
                request.form.get('tags'),
                request.form.get('seat_amount'),
                session.get('user_id'),
                datetime.utcnow()
            ))
            
            event_id = cursor.lastrowid
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    filename = secure_filename(f"{event_id}_{file.filename}")
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    
                    db.execute('UPDATE events SET image_filename = ? WHERE id = ?', 
                             (filename, event_id))
            
            db.commit()
            db.close()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('events.manage_events'))
            
        except Exception as e:
            flash(f'Error creating event: {e}', 'danger')
    
    return render_template('create_event.html')

@events_bp.route('/admin/event/<int:event_id>')
@admin_required
def view_event_detail(event_id):
    """View event details for admin."""
    event = get_event(event_id)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events.manage_events'))
    
    return render_template('view_event_detail.html', event=event)

@events_bp.route('/admin/event/<int:event_id>/update', methods=['POST'])
@admin_required
def update_event_detail(event_id):
    """Update event details."""
    try:
        date_str = request.form.get('date')
        time_str = request.form.get('event_time')
        
        if date_str and time_str:
            event_datetime = datetime.strptime(f"{date_str.strip()} {time_str}", '%Y-%m-%d %H:%M')
        else:
            event = get_event(event_id)
            event_datetime = event['date']
        
        db = _get_db()
        db.execute('''
            UPDATE events 
            SET title = ?, description = ?, date = ?, location = ?, 
                category = ?, event_type = ?, tags = ?, seat_amount = ?
            WHERE id = ?
        ''', (
            request.form.get('title'),
            request.form.get('description'),
            event_datetime,
            request.form.get('location'),
            request.form.get('category'),
            request.form.get('event_type'),
            request.form.get('tags'),
            request.form.get('seat_amount'),
            event_id
        ))
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{event_id}_{file.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                
                db.execute('UPDATE events SET image_filename = ? WHERE id = ?', 
                         (filename, event_id))
        
        db.commit()
        db.close()
        
        flash('Event updated successfully!', 'success')
        return redirect(url_for('events.manage_events'))
        
    except Exception as e:
        flash(f'Error updating event: {e}', 'danger')
        return redirect(url_for('events.view_event_detail', event_id=event_id))

@events_bp.route('/admin/delete/<int:event_id>')
@admin_required
def delete_event(event_id):
    """Delete an event."""
    db = _get_db()
    db.execute('DELETE FROM registrations WHERE event_id = ?', (event_id,))
    db.execute('DELETE FROM events WHERE id = ?', (event_id,))
    db.commit()
    db.close()
    
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('events.manage_events'))

@events_bp.route('/admin/insights')
@admin_required
def attendee_insights():
    """View attendee insights."""
    db = _get_db()
    total_events = db.execute('SELECT COUNT(*) as count FROM events').fetchone()['count']
    total_registrations = db.execute('SELECT COUNT(*) as count FROM registrations').fetchone()['count']
    db.close()
    
    return render_template('attendee_insights.html',
                         total_events=total_events,
                         total_registrations=total_registrations)

# ---------------------------------------------------------------------------
# Routes - Registration Management
# ---------------------------------------------------------------------------
@events_bp.route('/admin/event/<int:event_id>/registrations')
@admin_required
def get_event_registrations(event_id):
    """Get registrations for an event (JSON)."""
    db = _get_db()
    registrations = db.execute('''
        SELECT r.*, u.full_name as username
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
    ''', (event_id,)).fetchall()
    db.close()
    
    registration_list = []
    for reg in registrations:
        registration_list.append({
            'user_id': reg['user_id'],
            'username': reg['username'],
            'special_requests': reg['special_requests'],
            'registered_at': reg['registered_at']
        })
    
    return jsonify({'registrations': registration_list})

@events_bp.route('/admin/event/<int:event_id>/unregister/<int:user_id>', methods=['POST'])
@admin_required
def admin_unregister_user(event_id, user_id):
    """Admin unregister a user from an event."""
    try:
        db = _get_db()
        db.execute('DELETE FROM registrations WHERE event_id = ? AND user_id = ?', 
                  (event_id, user_id))
        db.commit()
        db.close()
        
        return jsonify({'success': True, 'message': 'User unregistered successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@events_bp.route('/admin/event/<int:event_id>/registrations/export')
@admin_required
def export_event_registrations(event_id):
    """Export registrations to CSV."""
    event = get_event(event_id)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events.manage_events'))
    
    db = _get_db()
    registrations = db.execute('''
        SELECT r.*, u.full_name as username
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
    ''', (event_id,)).fetchall()
    db.close()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Username', 'Special Requests', 'Registered At'])
    
    for reg in registrations:
        writer.writerow([
            reg['username'],
            reg['special_requests'] or '',
            reg['registered_at']
        ])
    
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    
    filename = f"{event['title'].replace(' ', '_')}_registrations.csv"
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)

@events_bp.route('/export/events')
@admin_required
def export_events():
    """Export all events to CSV."""
    db = _get_db()
    events = db.execute('SELECT * FROM events').fetchall()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Title', 'Description', 'Date', 'Location', 'Category', 'Type', 'Capacity'])
    
    for event in events:
        reg_count = db.execute('SELECT COUNT(*) as count FROM registrations WHERE event_id = ?', 
                             (event['id'],)).fetchone()['count']
        writer.writerow([
            event['title'],
            event['description'],
            event['date'],
            event['location'],
            event['category'],
            event['event_type'],
            f"{reg_count}/{event['seat_amount']}"
        ])
    
    db.close()
    
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='events_export.csv')
