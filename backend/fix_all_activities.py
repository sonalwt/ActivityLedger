from sqlalchemy import create_engine, text
import json
import sys
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

# Application categorization rules
CATEGORIES = {
    'productivity': [
        'code.exe', 'code', 'cursor.exe', 'cursor', 'devenv.exe', 'notepad++.exe',
        'sublime_text.exe', 'atom.exe', 'brackets.exe', 'vim', 'emacs',
        'pycharm.exe', 'pycharm64.exe', 'idea.exe', 'idea64.exe', 'webstorm.exe',
        'phpstorm.exe', 'rubymine.exe', 'goland.exe', 'clion.exe', 'rider.exe',
        'datagrip.exe', 'studio64.exe', 'eclipse.exe', 'netbeans.exe',
        'word.exe', 'winword.exe', 'excel.exe', 'powerpnt.exe', 'outlook.exe',
        'teams.exe', 'slack.exe', 'discord.exe', 'zoom.exe', 'skype.exe',
        'notion.exe', 'obsidian.exe', 'onenote.exe', 'evernote.exe',
        'terminal', 'cmd.exe', 'powershell.exe', 'bash', 'git-bash.exe',
        'postman.exe', 'insomnia.exe', 'git.exe', 'python.exe', 'node.exe',
        'python3', 'npm', 'yarn', 'pip', 'pip3', 'gnome-terminal',
        'konsole', 'xterm', 'terminator', 'tilix', 'vscode', 'visual studio code'
    ],
    'browser': [
        'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe',
        'vivaldi.exe', 'safari', 'iexplore.exe', 'browser', 'chromium',
        'google-chrome', 'firefox', 'microsoft-edge', 'chrome', 'edge'
    ],
    'server': [
        'filezilla.exe', 'winscp.exe', 'putty.exe', 'mobaxterm.exe',
        'mysql.exe', 'psql.exe', 'pgadmin4.exe', 'phpmyadmin',
        'apache', 'nginx', 'httpd', 'ssh', 'sshd', 'systemctl',
        'docker', 'docker-compose', 'kubectl', 'mysql', 'postgresql'
    ],
    'non-work': [
        'spotify.exe', 'vlc.exe', 'mpv.exe', 'wmplayer.exe',
        'steam.exe', 'epicgameslauncher.exe', 'whatsapp.exe',
        'telegram.exe', 'signal.exe', 'messenger.exe',
        'spotify', 'vlc', 'mpv', 'rhythmbox', 'telegram-desktop',
        'youtube', 'netflix', 'discord'
    ]
}

def categorize_app(app_name):
    """Categorize an application based on its name"""
    if not app_name:
        return 'uncategorized'
    
    app_lower = app_name.lower()
    
    for category, apps in CATEGORIES.items():
        if any(app in app_lower for app in apps):
            return category
    
    return 'uncategorized'

def extract_app_info(activity_data):
    """Extract application name and window title from activity_data JSON"""
    try:
        if not activity_data:
            return None, None
            
        if isinstance(activity_data, str):
            data = json.loads(activity_data)
        else:
            data = activity_data
            
        app_name = None
        window_title = None
        
        # ActivityWatch event structure
        if isinstance(data, dict):
            # Check if data has 'data' field (ActivityWatch structure)
            if 'data' in data and isinstance(data['data'], dict):
                event_data = data['data']
                app_name = event_data.get('app') or event_data.get('application')
                window_title = event_data.get('title') or event_data.get('window_title')
            else:
                # Direct fields
                app_name = data.get('app') or data.get('application') or data.get('application_name')
                window_title = data.get('title') or data.get('window_title')
            
            # Check for URL (browser activity)
            if not window_title and 'url' in data:
                window_title = data['url']
                
        return app_name, window_title
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None, None

print("=== Comprehensive Fix for Activity Records ===")

with engine.connect() as conn:
    print("\n1. Checking current state...")
    
    # Check how many records need fixing
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN application_name IS NULL THEN 1 END) as null_app,
            COUNT(CASE WHEN category IS NULL OR category = '' THEN 1 END) as null_category
        FROM activity_records
    """))
    
    stats = result.fetchone()
    print(f"   Total records: {stats[0]}")
    print(f"   Records with NULL application: {stats[1]}")
    print(f"   Records without category: {stats[2]}")
    
    if stats[1] == 0 and stats[2] == 0:
        print("\n✅ All records already have application names and categories!")
        sys.exit(0)
    
    # First, let's examine the activity_data structure
    print("\n2. Examining activity_data structure...")
    result = conn.execute(text("""
        SELECT activity_data 
        FROM activity_records 
        WHERE activity_data IS NOT NULL 
        AND activity_data != ''
        AND activity_data != '{}'
        LIMIT 5
    """))
    
    sample_count = 0
    for (data_str,) in result:
        try:
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
            sample_count += 1
            print(f"\n   Sample {sample_count}:")
            print(f"   Structure: {json.dumps(data, indent=4)[:300]}...")
            
            app, title = extract_app_info(data_str)
            print(f"   Extracted: app='{app}', title='{title[:50] if title else None}'")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Update records with extracted data
    print("\n3. Extracting application data from JSON...")
    
    # Get all records that need updating
    result = conn.execute(text("""
        SELECT id, activity_data
        FROM activity_records
        WHERE (application_name IS NULL OR application_name = '')
        AND activity_data IS NOT NULL 
        AND activity_data != '{}'
    """))
    
    trans = conn.begin()
    try:
        updated_count = 0
        categorized_count = 0
        
        for record_id, data_str in result:
            app_name, window_title = extract_app_info(data_str)
            
            if app_name:
                # Categorize the app
                category = categorize_app(app_name)
                
                # Update the record
                conn.execute(text("""
                    UPDATE activity_records
                    SET application_name = :app_name,
                        window_title = COALESCE(:window_title, window_title),
                        category = :category
                    WHERE id = :id
                """), {
                    "id": record_id,
                    "app_name": app_name[:255],
                    "window_title": window_title[:500] if window_title else None,
                    "category": category
                })
                
                updated_count += 1
                categorized_count += 1
                
                if updated_count % 100 == 0:
                    print(f"   Processed {updated_count} records...")
        
        # Also update any remaining uncategorized records
        print("\n4. Categorizing remaining records...")
        result = conn.execute(text("""
            SELECT id, application_name
            FROM activity_records
            WHERE (category IS NULL OR category = '')
            AND application_name IS NOT NULL
        """))
        
        for record_id, app_name in result:
            category = categorize_app(app_name)
            
            conn.execute(text("""
                UPDATE activity_records
                SET category = :category
                WHERE id = :id
            """), {
                "id": record_id,
                "category": category
            })
            
            categorized_count += 1
        
        trans.commit()
        
        print(f"\n✅ Successfully processed records:")
        print(f"   - Extracted app data: {updated_count} records")
        print(f"   - Categorized: {categorized_count} records")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ Error during processing: {e}")
        raise
    
    # Show final results
    print("\n5. Final Results:")
    
    # Application distribution
    print("\n   Top Applications:")
    result = conn.execute(text("""
        SELECT application_name, COUNT(*) as count
        FROM activity_records
        WHERE application_name IS NOT NULL
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 15
    """))
    
    for app, count in result:
        print(f"      {app}: {count} records")
    
    # Category distribution
    print("\n   Category Distribution:")
    result = conn.execute(text("""
        SELECT category, COUNT(*) as count
        FROM activity_records
        GROUP BY category
        ORDER BY count DESC
    """))
    
    for cat, count in result:
        print(f"      {cat or 'NULL'}: {count} records")
    
    # Sample categorized data
    print("\n   Sample Categorized Activities:")
    result = conn.execute(text("""
        SELECT application_name, category, window_title
        FROM activity_records
        WHERE category IS NOT NULL
        AND application_name IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 10
    """))
    
    for app, cat, title in result:
        print(f"      [{cat}] {app}: {title[:60] if title else 'No title'}...")

print("\n✅ Fix complete! Your dashboard should now show proper categories.")
print("\n📝 Note: If some records still have NULL applications, it means:")
print("   - The activity_data JSON doesn't contain app information")
print("   - The sync script needs to be updated to properly capture this data")
