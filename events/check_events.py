"""
Quick diagnostic - Run this to check your events folder structure
Save as: check_events.py and run: python check_events.py
"""

import os

print("Checking events folder structure...")
print("=" * 60)

events_path = "events"

# Check if events folder exists
if not os.path.exists(events_path):
    print("❌ ERROR: events folder not found!")
    exit(1)

print("✅ events/ folder exists")

# Required files
required_files = {
    '__init__.py': 'Blueprint initialization',
    'routes.py': 'Route definitions (or app.py renamed)',
    'models.py': 'Database models',
    'forms.py': 'WTForms'
}

print("\nChecking required files:")
for filename, description in required_files.items():
    filepath = os.path.join(events_path, filename)
    if os.path.exists(filepath):
        print(f"✅ {filename:<15} - {description}")
    else:
        print(f"❌ {filename:<15} - MISSING! ({description})")

# Check folders
print("\nChecking folders:")
for folder in ['templates', 'static']:
    folder_path = os.path.join(events_path, folder)
    if os.path.exists(folder_path):
        count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        print(f"✅ {folder}/ exists with {count} files")
    else:
        print(f"❌ {folder}/ MISSING!")

# Check __init__.py content
print("\nChecking __init__.py content:")
init_file = os.path.join(events_path, '__init__.py')
if os.path.exists(init_file):
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'events_bp' in content:
        print("✅ events_bp is defined")
    else:
        print("❌ events_bp NOT FOUND in __init__.py")
        print("   You need to add: events_bp = Blueprint(...)")
    
    if 'from events import routes' in content:
        print("✅ routes import found")
    else:
        print("⚠️  routes import not found")
        print("   Add: from events import routes")
else:
    print("❌ __init__.py not found")

print("\n" + "=" * 60)
print("If you see ❌, fix those issues first!")
