#!/usr/bin/env python3
"""
Fix all event templates - removes {% extends "base.html" %} and adds full navigation
Run this script in the events_templates_complete folder
"""

import re
import os

# Full navigation header to insert
FULL_NAV_HEADER = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BridgeGen - Events</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
'''

NAV_BAR = '''<header>
    <div class="logo">
        <a href="/" style="color:inherit; text-decoration:none;">
            <i class="fa-solid fa-asterisk"></i>
        </a>
    </div>
    
    <div class="input-group input-group-sm" style="width: 200px; margin-left: 20px;">
        <span class="input-group-text bg-light border-0">
            <i class="fa-solid fa-search text-muted"></i>
        </span>
        <input type="text" class="form-control bg-light border-0" placeholder="Search">
    </div>
    
    <nav class="nav-links">
        <a href="/">Home</a>
        <a href="/messaging/home">Messaging</a>
        <a href="/stories">LazarusStories</a>
        <a href="/events/list" style="color: var(--primary-color);">Events</a>
        <a href="/community">Community</a>
        {% if session.user_type == 'moderator' %}
            <a href="/stories/gamification/admin">Badges</a>
        {% else %}
            <a href="/stories/gamification/catalog">Badges</a>
        {% endif %}
    </nav>
    
    <div style="display: flex; align-items: center; gap: 15px;">
        <a href="#" style="text-decoration: none; color: #444; font-size: 14px;">FAQ</a>
        
        {% if session.user_id %}
            {% if session.user_type == 'moderator' %}
                <a href="/moderator/dashboard" class="btn btn-outline-secondary btn-sm px-3 d-flex align-items-center gap-2">
                    <i class="fa-solid fa-shield"></i> {{ session.full_name or 'staff' }}
                </a>
            {% else %}
                <a href="/profile" class="btn btn-outline-secondary btn-sm px-3 d-flex align-items-center gap-2">
                    <i class="fa-solid fa-user"></i> {{ session.full_name or 'User' }}
                </a>
            {% endif %}
            
            <a href="/logout" class="btn btn-outline-danger btn-sm px-3">
                <i class="fa-solid fa-right-from-bracket"></i> Logout
            </a>
        {% endif %}
    </div>
</header>
'''

# Files that need fixing (extend base.html)
FILES_TO_FIX = [
    'attendee_insights.html',
    'create_event.html',
    'edit_event.html',
    'view_event_detail.html',
    'user_event_detail.html',
]

def fix_template(filename):
    """Remove extends base.html and add full navigation"""
    print(f"Processing {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove {% extends "base.html" %} and {% block %} tags
    content = re.sub(r'{%\s*extends\s+"base\.html"\s*%}', '', content)
    content = re.sub(r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*%}', '', content, flags=re.DOTALL)
    content = re.sub(r'{%\s*block\s+content\s*%}', '', content)
    content = re.sub(r'{%\s*endblock\s*%}', '', content)
    
    # Wrap in HTML structure if not already wrapped
    if not content.strip().startswith('<!DOCTYPE html>'):
        # Extract styles
        style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
        styles = style_match.group(1) if style_match else ''
        
        # Remove the old style tag
        content = re.sub(r'<style>.*?</style>', '', content, flags=re.DOTALL)
        
        # Build new file
        new_content = FULL_NAV_HEADER
        
        # Add common header styles
        new_content += '''    <style>
        :root { --primary-color: #5b5FEF; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { min-height: 100vh; display: flex; flex-direction: column; background: white; }
        
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px 40px;
            background: white;
            border-bottom: 1px solid #eee;
            height: 70px;
            gap: 20px;
        }
        .logo { font-size: 24px; color: var(--primary-color); }
        .nav-links {
            display: flex;
            gap: 30px;
            align-items: center;
        }
        .nav-links a {
            text-decoration: none;
            color: #444;
            font-weight: 500;
            font-size: 14px;
        }
        .nav-links a:hover { color: var(--primary-color); }
'''
        
        # Add original styles
        new_content += styles
        new_content += '''    </style>
</head>
<body>
'''
        
        # Add navigation
        new_content += NAV_BAR
        
        # Add the rest of the content
        new_content += '\n' + content.strip()
        
        # Close HTML
        new_content += '''
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''
        
        content = new_content
    
    # Write back
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filename}")

def fix_calendar():
    """Fix view_calendar.html - just replace header section"""
    filename = 'view_calendar.html'
    print(f"Processing {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the header section
    # Old header is from <header> to </header>
    old_header_pattern = r'<header>.*?</header>'
    content = re.sub(old_header_pattern, NAV_BAR.strip(), content, flags=re.DOTALL)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filename}")

if __name__ == '__main__':
    for filename in FILES_TO_FIX:
        if os.path.exists(filename):
            fix_template(filename)
    
    if os.path.exists('view_calendar.html'):
        fix_calendar()
    
    print("\n✅ All templates fixed!")
    print("Copy these files to your events/templates/ folder")
