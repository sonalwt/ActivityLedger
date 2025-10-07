from sqlalchemy import create_engine, text
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
        'python3', 'npm', 'yarn', 'pip', 'pip3'
    ],
    'browser': [
        'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe',
        'vivaldi.exe', 'safari', 'iexplore.exe', 'browser', 'chromium',
        'google-chrome', 'firefox', 'microsoft-edge'
    ],
    'server': [
        'filezilla.exe', 'winscp.exe', 'putty.exe', 'mobaxterm.exe',
        'mysql.exe', 'psql.exe', 'pgadmin4.exe', 'phpmyadmin',
        'apache', 'nginx', 'httpd', 'ssh', 'sshd', 'systemctl',
        'docker', 'docker-compose', 'kubectl'
    ],
    'non-work': [
        'spotify.exe', 'vlc.exe', 'mpv.exe', 'wmplayer.exe',
        'steam.exe', 'epicgameslauncher.exe', 'whatsapp.exe',
        'telegram.exe', 'signal.exe', 'messenger.exe',
        'spotify', 'vlc', 'mpv', 'rhythmbox', 'telegram-desktop'
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

print("=== Categorizing All Activity Records ===")

with engine.connect() as conn:
    # First, show current state
    print("\n1. Current category distribution:")
    result = conn.execute(text("""
        SELECT 
            CASE 
                WHEN category IS NULL OR category = '' THEN 'NULL/Empty'
                ELSE category 
            END as cat,
            COUNT(*) as count
        FROM activity_records
        GROUP BY cat
        ORDER BY count DESC
    """))
    
    for row in result:
        print(f"   {row[0]}: {row[1]} records")

    # Get all unique app names
    print("\n2. Updating categories based on application names...")
    
    result = conn.execute(text("""
        SELECT DISTINCT application_name
        FROM activity_records
        WHERE application_name IS NOT NULL
    """))
    
    app_names = result.fetchall()
    total_updated = 0
    
    # Start transaction
    trans = conn.begin()
    
    try:
        for (app_name,) in app_names:
            category = categorize_app(app_name)
            
            # Update all records with this app name
            result = conn.execute(text("""
                UPDATE activity_records
                SET category = :category
                WHERE application_name = :app_name
            """), {"category": category, "app_name": app_name})
            
            updated = result.rowcount
            total_updated += updated
            
            if updated > 0:
                print(f"   {app_name} -> {category} ({updated} records)")
        
        trans.commit()
        print(f"\n✅ Total records updated: {total_updated}")
        
    except Exception as e:
        trans.rollback()
        print(f"\n❌ Error during update: {e}")
        raise

    # Show new distribution
    print("\n3. New category distribution:")
    result = conn.execute(text("""
        SELECT category, COUNT(*) as count
        FROM activity_records
        GROUP BY category
        ORDER BY count DESC
    """))
    
    for row in result:
        print(f"   {row[0]}: {row[1]} records")

    # Show sample categorized apps
    print("\n4. Sample categorized applications:")
    for category in ['productivity', 'browser', 'server', 'non-work', 'uncategorized']:
        print(f"\n   {category.upper()}:")
        result = conn.execute(text("""
            SELECT DISTINCT application_name, COUNT(*) as count
            FROM activity_records
            WHERE category = :category
            GROUP BY application_name
            ORDER BY count DESC
            LIMIT 5
        """), {"category": category})
        
        apps = result.fetchall()
        if apps:
            for app, count in apps:
                print(f"      - {app}: {count} records")
        else:
            print("      (no applications)")

print("\n✅ Categorization complete! Your dashboard should now show proper categories.")
