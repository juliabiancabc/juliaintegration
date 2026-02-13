"""
BridgeGen - Intergenerational Connection Platform
Main Flask Application File
Author: BridgeGen Team
Date: January 2026

This application implements a web-based platform for connecting youth and seniors
through shared experiences, storytelling, and collaborative activities.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import re

# Initializing Flask application
app = Flask(__name__)
app.secret_key = 'bridgegen_secret_key_2026_change_in_production'  # Change this in production!
app.permanent_session_lifetime = timedelta(hours=2)  # Session expires after 2 hours

# Enable CSRF protection (required by stories module)
# Don't auto-check on all routes — Mukesh's forms don't have tokens yet
from flask_wtf.csrf import CSRFProtect
app.config['WTF_CSRF_CHECK_DEFAULT'] = False
csrf = CSRFProtect(app)

# Database configuration
DATABASE = 'bridgegen.db'

# ---------------------------------------------------------------------------
# Register Stories & Posts Management Blueprint
# ---------------------------------------------------------------------------
import sys as _sys
_stories_module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storiesandpostsmanagement')
if _stories_module_path not in _sys.path:
    _sys.path.insert(0, _stories_module_path)

from storiesandpostsmanagement.app import stories_bp
app.register_blueprint(stories_bp, url_prefix='/stories')

# ---------------------------------------------------------------------------
# Register Messaging Blueprint
# ---------------------------------------------------------------------------
_messaging_module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Messaging')
if _messaging_module_path not in _sys.path:
    _sys.path.insert(0, _messaging_module_path)

from Messaging.messaging_bp import messaging_bp, register_socketio_events
app.register_blueprint(messaging_bp, url_prefix='/messaging')

# SocketIO for real-time group chat
from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins='*')
register_socketio_events(socketio)

# Initialise messaging DB tables on startup
from Messaging.models import init_db as _msg_init_db, seed_platform_groups as _msg_seed

# ---------------------------------------------------------------------------
# Register Events Blueprint
# ---------------------------------------------------------------------------
_events_module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'events')
if _events_module_path not in _sys.path:
    _sys.path.insert(0, _events_module_path)

from events import events_bp
app.register_blueprint(events_bp, url_prefix='/events')

# DB fns

def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    Uses Row factory to access columns by name.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Column/Name access
    return conn

def init_db():
    """
    Initializes the database with all required tables.
    Creates tables for users, stories, events, communities, and messages.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # User Info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            user_type TEXT NOT NULL CHECK(user_type IN ('youth', 'senior', 'moderator')),
            age INTEGER NOT NULL,
            phone TEXT,
            bio TEXT,
            location TEXT,
            languages TEXT,
            emergency_contact TEXT,
            emergency_phone TEXT,
            profile_verified INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            phone_verified INTEGER DEFAULT 0,
            moderator_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            deletion_scheduled_date TIMESTAMP
        )
    ''')
    
    # Stories table 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            is_public INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Events table (Enhanced for events module)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TIMESTAMP NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            event_type TEXT DEFAULT 'physical',
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            seat_amount INTEGER NOT NULL,
            available_seats INTEGER,
            expected_attendance INTEGER,
            is_closed INTEGER DEFAULT 0,
            special_requests TEXT,
            image TEXT,
            image_filename TEXT,
            max_participants INTEGER,
            creator_id INTEGER,
            event_date TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (creator_id) REFERENCES users (id)
        )
    ''')
    
    # Event registrations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            special_requests TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id),
            UNIQUE(user_id, event_id)
        )
    ''')
    
    # Communities/Groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS communities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            creator_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users (id)
        )
    ''')
    
    # Community memberships
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS community_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            community_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (community_id) REFERENCES communities (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(community_id, user_id)
        )
    ''')
    
    # Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            subject TEXT,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
    ''')
    
    # Interest tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, tag)
        )
    ''')
    
    # Notifications settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id INTEGER PRIMARY KEY,
            new_messages INTEGER DEFAULT 1,
            event_reminders INTEGER DEFAULT 1,
            story_comments INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Profile change history (for moderator review)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            field_changed TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            flagged INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ==================== HELPER FUNCTIONS ====================

def hash_password(password):
    """
    Hashes a password using SHA-256.
    In production, use bcrypt or argon2 for better security.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """
    Validates email format using regex.
    Returns True if valid, False otherwise.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """
    Validates Singapore phone format (+65 XXXX XXXX).
    Returns True if valid, False otherwise.
    """
    # Remove spaces and check if it matches Singapore format
    phone_clean = phone.replace(' ', '').replace('+', '')
    return len(phone_clean) >= 8 and phone_clean.isdigit()

def login_required(f):
    """
    Decorator to protect routes that require authentication.
    Redirects to login page if user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def moderator_required(f):
    """
    Decorator to protect routes that require moderator access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_type') != 'moderator':
            flash('Access denied. Moderator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    """
    Home page route.
    Shows different content based on whether user is logged in.
    """
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.
    Handles account type selection and initial registration.
    """
    if request.method == 'POST':
        account_type = request.form.get('account_type')
        
        # Store account type in session for next step
        session['registration_type'] = account_type
        
        # Redirect to appropriate registration form
        return redirect(url_for('register_form'))
    
    return render_template('register.html')

@app.route('/register/form', methods=['GET', 'POST'])
def register_form():
    """
    Registration form route.
    Handles the actual user registration with validation.
    """
    if 'registration_type' not in session:
        return redirect(url_for('register'))
    
    account_type = session['registration_type']
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        age = request.form.get('age', '').strip()
        phone = request.form.get('phone', '').strip()
        moderator_key = request.form.get('moderator_key', '').strip()
        
        # Validation
        errors = []
        
        if not email or not validate_email(email):
            errors.append('Please enter a valid email address.')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if not full_name:
            errors.append('Full name is required.')
        
        if not age or not age.isdigit():
            errors.append('Please enter a valid age.')
        else:
            age_int = int(age)
            if account_type == 'youth' and (age_int < 13 or age_int > 25):
                errors.append('Youth members must be between 13-25 years old.')
            elif account_type == 'senior' and age_int < 60:
                errors.append('Senior members must be 60+ years old.')
        
        if phone and not validate_phone(phone):
            errors.append('Please enter a valid phone number.')
        
        # Moderator key validation
        if account_type == 'moderator':
            if moderator_key != 'BRIDGEGEN2026':  # In production, use secure verification
                errors.append('Invalid moderator key.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register_form.html', account_type=account_type)
        
        # Check if email already exists
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            flash('An account with this email already exists.', 'danger')
            conn.close()
            return render_template('register_form.html', account_type=account_type)
        
        # Create new user
        try:
            hashed_password = hash_password(password)
            cursor = conn.execute('''
                INSERT INTO users (email, password, full_name, user_type, age, phone, moderator_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (email, hashed_password, full_name, account_type, int(age), phone, 
                  moderator_key if account_type == 'moderator' else None))
            
            user_id = cursor.lastrowid
            
            # Create default notification settings
            conn.execute('''
                INSERT INTO notification_settings (user_id)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please log in.', 'success')
            session.pop('registration_type', None)
            return redirect(url_for('login'))
            
        except Exception as e:
            conn.close()
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('register_form.html', account_type=account_type)
    
    return render_template('register_form.html', account_type=account_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route.
    Handles user authentication for all account types.
    """
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        account_type = request.form.get('account_type')
        
        if account_type:
            # Store account type selection
            session['login_type'] = account_type
            return redirect(url_for('login_form'))
    
    return render_template('login.html')

@app.route('/login/form', methods=['GET', 'POST'])
def login_form():
    """
    Login form route.
    Processes login credentials and creates session.
    """
    if 'login_type' not in session:
        return redirect(url_for('login'))
    
    account_type = session['login_type']
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        moderator_key = request.form.get('moderator_key', '').strip()
        phone = request.form.get('phone', '').strip()
        
        conn = get_db_connection()
        
        # Different login methods for different account types
        if account_type == 'youth':
            # Youth login with email
            user = conn.execute('''
                SELECT * FROM users 
                WHERE email = ? AND user_type = 'youth' AND is_deleted = 0
            ''', (email,)).fetchone()
            
        elif account_type == 'senior':
            # Senior login with phone
            user = conn.execute('''
                SELECT * FROM users 
                WHERE phone = ? AND user_type = 'senior' AND is_deleted = 0
            ''', (phone,)).fetchone()
            
        else:  # moderator
            # Moderator login with key
            user = conn.execute('''
                SELECT * FROM users 
                WHERE moderator_key = ? AND user_type = 'moderator' AND is_deleted = 0
            ''', (moderator_key,)).fetchone()
        
        conn.close()
        
        if user and hash_password(password) == user['password']:
            # Successful login
            session.permanent = True
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            session.pop('login_type', None)
            
            # Redirect based on user type
            if user['user_type'] == 'moderator':
                return redirect(url_for('moderator_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template('login_form.html', account_type=account_type)

@app.route('/logout')
def logout():
    """
    Logout route.
    Clears session and redirects to home page.
    """
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard for regular users (youth/senior).
    Shows personalized content and statistics.
    """
    conn = get_db_connection()
    
    # Get unread message count
    unread_count = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE recipient_id = ? AND is_read = 0
    ''', (session['user_id'],)).fetchone()['count']
    
    # Get user's communities
    communities = conn.execute('''
        SELECT c.* FROM communities c
        JOIN community_members cm ON c.id = cm.community_id
        WHERE cm.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    # Get upcoming events
    upcoming_events = conn.execute('''
        SELECT * FROM events 
        WHERE datetime(date) > datetime('now')
        ORDER BY date ASC
        LIMIT 3
    ''', ()).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         unread_count=unread_count,
                         communities=communities,
                         upcoming_events=upcoming_events)

@app.route('/moderator/dashboard')
@moderator_required
def moderator_dashboard():
    """
    Moderator dashboard.
    Shows platform statistics and flagged content.
    """
    conn = get_db_connection()
    
    # Get statistics
    total_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_deleted = 0').fetchone()['count']
    flagged_users = conn.execute('SELECT COUNT(DISTINCT user_id) as count FROM profile_history WHERE flagged = 1').fetchone()['count']
    pending_reports = 15  # Placeholder - would come from reports table
    
    # Get recent flagged changes
    recent_activity = conn.execute('''
        SELECT ph.*, u.full_name, u.email 
        FROM profile_history ph
        JOIN users u ON ph.user_id = u.id
        WHERE ph.flagged = 1 OR ph.changed_at > datetime('now', '-1 day')
        ORDER BY ph.changed_at DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('moderator_dashboard.html',
                         total_users=total_users,
                         flagged_users=flagged_users,
                         pending_reports=pending_reports,
                         recent_activity=recent_activity)

# ==================== PROFILE MANAGEMENT ROUTES ====================

@app.route('/profile')
@login_required
def profile():
    """
    View user's own profile.
    Shows both public and private information.
    """
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get user's interests
    interests = conn.execute('''
        SELECT tag FROM interests WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, interests=interests)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Edit user profile.
    Includes validation and change tracking for moderator review.
    """
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name', '').strip()
        age = request.form.get('age', '').strip()
        bio = request.form.get('bio', '').strip()
        location = request.form.get('location', '').strip()
        languages = request.form.get('languages', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()
        emergency_phone = request.form.get('emergency_phone', '').strip()
        
        # Validation
        errors = []
        
        if not full_name:
            errors.append('Full name is required.')
        
        if not age or not age.isdigit():
            errors.append('Please enter a valid age.')
        else:
            age_int = int(age)
            # Check for suspicious age changes (more than 2 years)
            if abs(age_int - user['age']) > 2:
                # Flag for moderator review
                conn.execute('''
                    INSERT INTO profile_history (user_id, field_changed, old_value, new_value, flagged)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session['user_id'], 'age', str(user['age']), str(age_int), 1))
                flash('Age change flagged for moderator review.', 'warning')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            conn.close()
            return render_template('edit_profile.html', user=user)
        
        # Track changes
        changes = []
        if full_name != user['full_name']:
            changes.append(('full_name', user['full_name'], full_name))
        if bio != (user['bio'] or ''):
            changes.append(('bio', user['bio'], bio))
        if location != (user['location'] or ''):
            changes.append(('location', user['location'], location))
        
        # Log changes to history
        for field, old_val, new_val in changes:
            conn.execute('''
                INSERT INTO profile_history (user_id, field_changed, old_value, new_value)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], field, old_val, new_val))
        
        # Update user profile
        try:
            conn.execute('''
                UPDATE users 
                SET full_name = ?, age = ?, bio = ?, location = ?, 
                    languages = ?, emergency_contact = ?, emergency_phone = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (full_name, int(age), bio, location, languages, 
                  emergency_contact, emergency_phone, session['user_id']))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
        
        conn.close()
        return redirect(url_for('profile'))
    
    conn.close()
    return render_template('edit_profile.html', user=user)

@app.route('/profile/interests', methods=['GET', 'POST'])
@login_required
def manage_interests():
    """
    Manage user interest tags.
    Allows adding and removing interests.
    """
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        tag = request.form.get('tag', '').strip()
        
        if action == 'add' and tag:
            try:
                conn.execute('''
                    INSERT INTO interests (user_id, tag) VALUES (?, ?)
                ''', (session['user_id'], tag))
                conn.commit()
                flash(f'Added interest: {tag}', 'success')
            except sqlite3.IntegrityError:
                flash('You already have this interest.', 'warning')
        
        elif action == 'remove' and tag:
            conn.execute('''
                DELETE FROM interests WHERE user_id = ? AND tag = ?
            ''', (session['user_id'], tag))
            conn.commit()
            flash(f'Removed interest: {tag}', 'success')
    
    # Get user's current interests
    interests = conn.execute('''
        SELECT tag FROM interests WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    # Popular interest suggestions
    popular_interests = ['Photography', 'Technology', 'Cooking', 'Hiking', 
                        'Gardening', 'Arts & Crafts', 'Fitness', 'Reading',
                        'Volunteering', 'Language Learning', 'History', 'Gaming']
    
    return render_template('interests.html', 
                         interests=interests,
                         popular_interests=popular_interests)

@app.route('/profile/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """
    Manage notification preferences.
    Allows users to control what notifications they receive.
    """
    conn = get_db_connection()
    settings = conn.execute('''
        SELECT * FROM notification_settings WHERE user_id = ?
    ''', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        new_messages = 1 if request.form.get('new_messages') else 0
        event_reminders = 1 if request.form.get('event_reminders') else 0
        story_comments = 1 if request.form.get('story_comments') else 0
        
        conn.execute('''
            UPDATE notification_settings 
            SET new_messages = ?, event_reminders = ?, story_comments = ?
            WHERE user_id = ?
        ''', (new_messages, event_reminders, story_comments, session['user_id']))
        
        conn.commit()
        flash('Notification settings updated!', 'success')
        
        # Refresh settings
        settings = conn.execute('''
            SELECT * FROM notification_settings WHERE user_id = ?
        ''', (session['user_id'],)).fetchone()
    
    conn.close()
    return render_template('notifications.html', settings=settings)

@app.route('/profile/verify')
@login_required
def verify_profile():
    """
    Profile verification page.
    Shows verification steps and status.
    """
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('verify_profile.html', user=user)

@app.route('/profile/verify/email', methods=['POST'])
@login_required
def verify_email():
    """
    Email verification endpoint.
    In production, would send verification email.
    """
    conn = get_db_connection()
    conn.execute('''
        UPDATE users SET email_verified = 1 WHERE id = ?
    ''', (session['user_id'],))
    conn.commit()
    conn.close()
    
    flash('Email verified successfully!', 'success')
    return redirect(url_for('verify_profile'))

@app.route('/profile/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    """
    Account deletion with confirmation.
    Implements 30-day grace period before permanent deletion.
    """
    if request.method == 'POST':
        confirmation = request.form.get('confirmation')
        password = request.form.get('password', '')
        
        if confirmation != 'DELETE':
            flash('Please type DELETE to confirm account deletion.', 'danger')
            return render_template('delete_account.html')
        
        # Verify password
        conn = get_db_connection()
        user = conn.execute('SELECT password FROM users WHERE id = ?', 
                          (session['user_id'],)).fetchone()
        
        if hash_password(password) != user['password']:
            flash('Incorrect password.', 'danger')
            conn.close()
            return render_template('delete_account.html')
        
        # Schedule deletion (30-day grace period)
        deletion_date = datetime.now() + timedelta(days=30)
        conn.execute('''
            UPDATE users 
            SET is_deleted = 1, deletion_scheduled_date = ?
            WHERE id = ?
        ''', (deletion_date, session['user_id']))
        
        conn.commit()
        conn.close()
        
        flash('Your account has been scheduled for deletion in 30 days. You can restore it by logging in within this period.', 'warning')
        
        # Log out user
        session.clear()
        return redirect(url_for('index'))
    
    return render_template('delete_account.html')

# ==================== MESSAGES ROUTES ====================

@app.route('/messages')
@login_required
def messages():
    """
    Redirect to the integrated messaging module (group messaging hub).
    """
    return redirect(url_for('messaging.home'))

@app.route('/messages/send', methods=['GET', 'POST'])
@login_required
def send_message():
    """
    Send a new message.
    Includes recipient validation.
    """
    if request.method == 'POST':
        recipient_email = request.form.get('recipient_email', '').strip()
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not recipient_email or not content:
            flash('Recipient and message content are required.', 'danger')
            return render_template('send_message.html')
        
        conn = get_db_connection()
        
        # Find recipient
        recipient = conn.execute('''
            SELECT id FROM users WHERE email = ? AND is_deleted = 0
        ''', (recipient_email,)).fetchone()
        
        if not recipient:
            flash('Recipient not found.', 'danger')
            conn.close()
            return render_template('send_message.html')
        
        # Send message
        conn.execute('''
            INSERT INTO messages (sender_id, recipient_id, subject, content)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], recipient['id'], subject, content))
        
        conn.commit()
        conn.close()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('messages'))
    
    return render_template('send_message.html')

# ==================== STORIES ROUTES ====================
# Now handled by storiesandpostsmanagement Blueprint at /stories

# ==================== EVENTS ROUTES ====================
# Now handled by Events Blueprint at /events

@app.route('/events')
@login_required  
def events():
    """Redirect to events blueprint."""
    return redirect('/events/') 
# ==================== COMMUNITY ROUTES ====================

@app.route('/community')
@login_required
def community():
    """
    Community/groups listing page.
    Shows all available communities.
    """
    conn = get_db_connection()
    
    communities = conn.execute('''
        SELECT c.*, u.full_name as creator_name,
               (SELECT COUNT(*) FROM community_members WHERE community_id = c.id) as member_count
        FROM communities c
        JOIN users u ON c.creator_id = u.id
        ORDER BY c.created_at DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('community.html', communities=communities)

@app.route('/community/join/<int:community_id>', methods=['POST'])
@login_required
def join_community(community_id):
    """
    Join a community.
    Prevents duplicate memberships.
    """
    conn = get_db_connection()
    
    try:
        conn.execute('''
            INSERT INTO community_members (community_id, user_id)
            VALUES (?, ?)
        ''', (community_id, session['user_id']))
        conn.commit()
        flash('Successfully joined the community!', 'success')
    except sqlite3.IntegrityError:
        flash('You are already a member of this community.', 'warning')
    
    conn.close()
    return redirect(url_for('community'))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    # Initialize databases
    init_db()
    _msg_init_db()
    _msg_seed()
    
    # Run the application (use socketio.run for WebSocket support)
    print("🚀 Starting BridgeGen Flask Application...")
    print("📍 Access the application at: http://127.0.0.1:5000")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
