"""
Events Routes - BridgeGen Platform
Handles all event-related routes and logic
Author: BridgeGen Team
Date: February 2026
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import csv
from io import StringIO, BytesIO
from werkzeug.utils import secure_filename
import os
from events import events_bp

# Database configuration
DATABASE = 'bridgegen.db'

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def moderator_required(f):
    """Decorator to require moderator privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_type') != 'moderator':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_schema_info():
    """
    Determine which schema is being used by checking column names
    Returns dict with column mappings
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get column info for events table
    cursor.execute("PRAGMA table_info(events)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    # Determine schema based on columns present
    schema = {
        'date_column': 'date' if 'date' in columns else 'event_date',
        'creator_column': 'created_by' if 'created_by' in columns else 'creator_id',
        'has_status': 'status' in columns,
        'has_category': 'category' in columns
    }
    
    return schema

# Get schema info once when module loads
SCHEMA = get_schema_info()

# ==================== MAIN EVENTS ROUTES ====================

@events_bp.route('/list')
@login_required
def view_events():
    """
    Main events dashboard - shows three action cards
    For moderators: Shows admin view with statistics
    For users: Shows standard view
    """
    stats = {}
    
    if session.get('user_type') == 'moderator':
        # Get statistics for moderators
        conn = get_db_connection()
        
        # Total events
        total_events = conn.execute('SELECT COUNT(*) as count FROM events').fetchone()['count']
        
        # Upcoming events (using correct date column)
        upcoming_events = conn.execute(
            f'SELECT COUNT(*) as count FROM events WHERE {SCHEMA["date_column"]} >= datetime("now")'
        ).fetchone()['count']
        
        # Pending approvals (if status column exists)
        if SCHEMA['has_status']:
            pending_approvals = conn.execute(
                'SELECT COUNT(*) as count FROM events WHERE status = ?', ('pending',)
            ).fetchone()['count']
        else:
            pending_approvals = 0
        
        # Total participants
        total_participants = conn.execute(
            'SELECT COUNT(*) as count FROM event_registrations'
        ).fetchone()['count']
        
        conn.close()
        
        stats = {
            'total_events': total_events,
            'upcoming_events': upcoming_events,
            'pending_approvals': pending_approvals,
            'total_participants': total_participants
        }
    
    return render_template('view_events.html', **stats)

@events_bp.route('/manage')
@login_required
def manage_events():
    """
    Manage events page
    Moderators: See all events
    Users: See only their created events
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    
    if session.get('user_type') == 'moderator':
        # Moderators see all events
        query = f'''
            SELECT e.*, u.full_name as creator_name,
                   (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count
            FROM events e
            LEFT JOIN users u ON e.{creator_col} = u.id
            ORDER BY e.{date_col} DESC
        '''
        events = conn.execute(query).fetchall()
    else:
        # Regular users see only their events
        query = f'''
            SELECT e.*,
                   (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count
            FROM events e
            WHERE e.{creator_col} = ?
            ORDER BY e.{date_col} DESC
        '''
        events = conn.execute(query, (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('manage_events.html', events=events)

@events_bp.route('/browse')
@login_required
def browse_events():
    """
    Browse and join events page
    Shows all upcoming public events
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    
    # Build query based on schema
    status_filter = 'AND (e.status = "approved" OR e.status IS NULL)' if SCHEMA['has_status'] else ''
    
    query = f'''
        SELECT e.*, u.full_name as creator_name,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id AND user_id = ?) as user_registered
        FROM events e
        LEFT JOIN users u ON e.{creator_col} = u.id
        WHERE e.{date_col} >= datetime("now")
        {status_filter}
        ORDER BY e.{date_col} ASC
    '''
    
    events = conn.execute(query, (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('user_event_detail.html', events=events)

@events_bp.route('/admin-browse')
@login_required
def admin_view_events():
    """
    Admin view of browse events - renders admin_view_events.html
    Same as browse_events but uses different template
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    
    # Build query based on schema
    status_filter = 'AND (e.status = "approved" OR e.status IS NULL)' if SCHEMA['has_status'] else ''
    
    query = f'''
        SELECT e.*, u.full_name as creator_name,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id AND user_id = ?) as user_registered
        FROM events e
        LEFT JOIN users u ON e.{creator_col} = u.id
        WHERE e.{date_col} >= datetime("now")
        {status_filter}
        ORDER BY e.{date_col} ASC
    '''
    
    events = conn.execute(query, (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('admin_view_events.html', events=events)

@events_bp.route('/calendar')
@login_required
def view_calendar():
    """
    Calendar view of all events
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    category_col = ', e.category' if SCHEMA['has_category'] else ', "" as category'
    
    # Get all events for calendar
    query = f'''
        SELECT e.id, e.title, e.{date_col} as date, e.location{category_col},
               u.full_name as creator_name
        FROM events e
        LEFT JOIN users u ON e.{creator_col} = u.id
        WHERE e.{date_col} >= datetime("now", "-30 days")
        ORDER BY e.{date_col} ASC
    '''
    
    events = conn.execute(query).fetchall()
    
    conn.close()
    
    # Convert to list of dicts for JSON serialization
    events_list = []
    for event in events:
        events_list.append({
            'id': event['id'],
            'title': event['title'],
            'date': event['date'],
            'location': event['location'],
            'category': event.get('category', ''),
            'creator_name': event['creator_name']
        })
    
    return render_template('view_calendar.html', events=events_list)

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_event():
    """
    Create a new event
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_date = request.form.get('date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        category = request.form.get('category', '').strip() if SCHEMA['has_category'] else None
        seat_amount = request.form.get('seat_amount', '').strip()
        event_type = request.form.get('event_type', 'physical').strip()
        tags = request.form.get('tags', '').strip()
        
        required_fields = [title, description, event_date, event_time, location, seat_amount]
        if SCHEMA['has_category']:
            required_fields.append(category)
        
        if not all(required_fields):
            flash('All required fields must be filled.', 'danger')
            return render_template('create_event.html')
        
        # Validate date is in the future
        try:
            datetime_str = f"{event_date} {event_time}"
            event_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            if event_datetime <= datetime.now():
                flash('Event date must be in the future.', 'danger')
                return render_template('create_event.html')
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('create_event.html')
        
        conn = get_db_connection()
        
        # Build insert query based on schema
        date_col = SCHEMA['date_column']
        creator_col = SCHEMA['creator_column']
        
        if SCHEMA['has_status'] and SCHEMA['has_category']:
            # New schema with status and category
            status = 'approved' if session.get('user_type') == 'moderator' else 'pending'
            query = f'''
                INSERT INTO events ({creator_col}, title, description, {date_col}, location, category, seat_amount, event_type, tags, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (session['user_id'], title, description, event_datetime, location, category,
                     int(seat_amount) if seat_amount else None, event_type, tags, status, datetime.now())
        elif SCHEMA['has_category']:
            # Has category but no status
            query = f'''
                INSERT INTO events ({creator_col}, title, description, {date_col}, location, category, seat_amount, event_type, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (session['user_id'], title, description, event_datetime, location, category,
                     int(seat_amount) if seat_amount else None, event_type, tags, datetime.now())
        else:
            # Old schema - no category, no status
            query = f'''
                INSERT INTO events ({creator_col}, title, description, {date_col}, location, seat_amount, event_type, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (session['user_id'], title, description, event_datetime, location,
                     int(seat_amount) if seat_amount else None, event_type, tags, datetime.now())
        
        conn.execute(query, params)
        
        # Get the inserted event ID
        event_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{event_id}_{file.filename}")
                upload_path = os.path.join('static', 'uploads', 'events')
                os.makedirs(upload_path, exist_ok=True)
                filepath = os.path.join(upload_path, filename)
                file.save(filepath)
                
                conn.execute('UPDATE events SET image_filename = ? WHERE id = ?', 
                           (filename, event_id))
        
        conn.commit()
        conn.close()
        
        if SCHEMA['has_status'] and status == 'pending':
            flash('Event created successfully! It will be visible after moderator approval.', 'success')
        else:
            flash('Event created successfully!', 'success')
        
        return redirect(url_for('events.manage_events'))
    
    return render_template('create_event.html')

@events_bp.route('/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """
    Edit an existing event
    Only creator or moderator can edit
    """
    conn = get_db_connection()
    creator_col = SCHEMA['creator_column']
    
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    
    if not event:
        flash('Event not found.', 'danger')
        conn.close()
        return redirect(url_for('events.manage_events'))
    
    # Check permissions
    if event[creator_col] != session['user_id'] and session.get('user_type') != 'moderator':
        flash('You do not have permission to edit this event.', 'danger')
        conn.close()
        return redirect(url_for('events.manage_events'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_date = request.form.get('date', '').strip()
        location = request.form.get('location', '').strip()
        category = request.form.get('category', '').strip() if SCHEMA['has_category'] else None
        seat_amount = request.form.get('seat_amount', '').strip()
        
        required_fields = [title, description, event_date, location]
        if SCHEMA['has_category']:
            required_fields.append(category)
            
        if not all(required_fields):
            flash('All required fields must be filled.', 'danger')
            return render_template('edit_event.html', event=event)
        
        date_col = SCHEMA['date_column']
        
        if SCHEMA['has_category']:
            query = f'''
                UPDATE events 
                SET title = ?, description = ?, {date_col} = ?, location = ?, category = ?, seat_amount = ?
                WHERE id = ?
            '''
            params = (title, description, event_date, location, category,
                     int(seat_amount) if seat_amount else None, event_id)
        else:
            query = f'''
                UPDATE events 
                SET title = ?, description = ?, {date_col} = ?, location = ?, seat_amount = ?
                WHERE id = ?
            '''
            params = (title, description, event_date, location,
                     int(seat_amount) if seat_amount else None, event_id)
        
        conn.execute(query, params)
        conn.commit()
        conn.close()
        
        flash('Event updated successfully!', 'success')
        return redirect(url_for('events.manage_events'))
    
    conn.close()
    return render_template('edit_event.html', event=event)

@events_bp.route('/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """
    Delete an event
    Only creator or moderator can delete
    """
    conn = get_db_connection()
    creator_col = SCHEMA['creator_column']
    
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    
    if not event:
        flash('Event not found.', 'danger')
        conn.close()
        return redirect(url_for('events.manage_events'))
    
    # Check permissions
    if event[creator_col] != session['user_id'] and session.get('user_type') != 'moderator':
        flash('You do not have permission to delete this event.', 'danger')
        conn.close()
        return redirect(url_for('events.manage_events'))
    
    # Delete event and registrations
    conn.execute('DELETE FROM event_registrations WHERE event_id = ?', (event_id,))
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    
    conn.commit()
    conn.close()
    
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('events.manage_events'))

@events_bp.route('/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    """
    Register for an event
    """
    conn = get_db_connection()
    
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    
    if not event:
        flash('Event not found.', 'danger')
        conn.close()
        return redirect(url_for('events.browse_events'))
    
    # Check if already registered
    existing = conn.execute('''
        SELECT * FROM event_registrations WHERE event_id = ? AND user_id = ?
    ''', (event_id, session['user_id'])).fetchone()
    
    if existing:
        flash('You are already registered for this event.', 'warning')
        conn.close()
        return redirect(url_for('events.browse_events'))
    
    # Check max participants (seat_amount)
    if event.get('seat_amount'):
        current_count = conn.execute('''
            SELECT COUNT(*) as count FROM event_registrations WHERE event_id = ?
        ''', (event_id,)).fetchone()['count']
        
        if current_count >= event['seat_amount']:
            flash('This event is full.', 'warning')
            conn.close()
            return redirect(url_for('events.browse_events'))
    
    # Register user
    conn.execute('''
        INSERT INTO event_registrations (event_id, user_id)
        VALUES (?, ?)
    ''', (event_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('events.browse_events'))

@events_bp.route('/unregister/<int:event_id>', methods=['POST'])
@login_required
def unregister_event(event_id):
    """
    Unregister from an event
    """
    conn = get_db_connection()
    
    conn.execute('''
        DELETE FROM event_registrations WHERE event_id = ? AND user_id = ?
    ''', (event_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash('Successfully unregistered from the event.', 'success')
    return redirect(url_for('events.browse_events'))

@events_bp.route('/my-events')
@login_required
def my_events():
    """
    View user's registered events
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    
    query = f'''
        SELECT e.*, u.full_name as creator_name,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count
        FROM events e
        LEFT JOIN users u ON e.{creator_col} = u.id
        INNER JOIN event_registrations er ON e.id = er.event_id
        WHERE er.user_id = ?
        ORDER BY e.{date_col} ASC
    '''
    
    events = conn.execute(query, (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('user_event_detail.html', events=events, my_events=True)

# ==================== MODERATOR ROUTES ====================

@events_bp.route('/admin/approve/<int:event_id>', methods=['POST'])
@moderator_required
def approve_event(event_id):
    """
    Approve a pending event (moderator only)
    """
    if not SCHEMA['has_status']:
        flash('Event approval not supported with current schema.', 'warning')
        return redirect(url_for('events.manage_events'))
    
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE events SET status = 'approved' WHERE id = ?
    ''', (event_id,))
    
    conn.commit()
    conn.close()
    
    flash('Event approved successfully!', 'success')
    return redirect(url_for('events.manage_events'))

@events_bp.route('/admin/reject/<int:event_id>', methods=['POST'])
@moderator_required
def reject_event(event_id):
    """
    Reject a pending event (moderator only)
    """
    if not SCHEMA['has_status']:
        flash('Event rejection not supported with current schema.', 'warning')
        return redirect(url_for('events.manage_events'))
    
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE events SET status = 'rejected' WHERE id = ?
    ''', (event_id,))
    
    conn.commit()
    conn.close()
    
    flash('Event rejected.', 'warning')
    return redirect(url_for('events.manage_events'))

@events_bp.route('/admin/insights')
@moderator_required
def attendee_insights():
    """
    View attendee insights and analytics (moderator only)
    """
    conn = get_db_connection()
    
    # Get various statistics
    stats = {}
    
    if SCHEMA['has_category']:
        # Events by category
        stats['by_category'] = conn.execute('''
            SELECT category, COUNT(*) as count
            FROM events
            GROUP BY category
            ORDER BY count DESC
        ''').fetchall()
    else:
        stats['by_category'] = []
    
    # Participation by user type
    stats['by_user_type'] = conn.execute('''
        SELECT u.user_type, COUNT(er.id) as count
        FROM event_registrations er
        JOIN users u ON er.user_id = u.id
        GROUP BY u.user_type
    ''').fetchall()
    
    # Most popular events
    stats['popular_events'] = conn.execute('''
        SELECT e.title, COUNT(er.id) as participant_count
        FROM events e
        LEFT JOIN event_registrations er ON e.id = er.event_id
        GROUP BY e.id
        ORDER BY participant_count DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('attendee_insights.html', stats=stats)

@events_bp.route('/export')
@moderator_required
def export_events():
    """
    Export events to CSV (moderator only)
    """
    conn = get_db_connection()
    
    date_col = SCHEMA['date_column']
    creator_col = SCHEMA['creator_column']
    
    query = f'''
        SELECT e.*, u.full_name as creator_name,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count
        FROM events e
        LEFT JOIN users u ON e.{creator_col} = u.id
        ORDER BY e.{date_col} DESC
    '''
    
    events = conn.execute(query).fetchall()
    conn.close()
    
    # Create CSV in memory
    si = StringIO()
    writer = csv.writer(si)
    
    # Write headers
    writer.writerow(['ID', 'Title', 'Description', 'Date', 'Location', 'Category', 'Participants', 'Creator'])
    
    # Write data
    for event in events:
        writer.writerow([
            event['id'],
            event['title'],
            event['description'],
            event[date_col],
            event['location'],
            event.get('category', 'N/A'),
            event['participant_count'],
            event['creator_name']
        ])
    
    # Convert to bytes
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'events_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )
