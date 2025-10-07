import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Parse connection string
conn_parts = DATABASE_URL.replace("postgresql://", "").split("@")
user_pass = conn_parts[0].split(":")
host_db = conn_parts[1].split("/")
host_port = host_db[0].split(":")

conn = psycopg2.connect(
    host=host_port[0],
    port=host_port[1] if len(host_port) > 1 else "5432",
    database=host_db[1],
    user=user_pass[0],
    password=user_pass[1]
)

cur = conn.cursor()

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
        'postman.exe', 'insomnia.exe', 'git.exe', 'python.exe', 'node.exe'
    ],
    'browser': [
        'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe',
        'vivaldi.exe', 'safari', 'iexplore.exe', 'browser'
    ],
    'server': [
        'filezilla.exe', 'winscp.exe', 'putty.exe', 'mobaxterm.exe',
        'mysql.exe', 'psql.exe', 'pgadmin4.exe', 'phpmyadmin',
        'apache', 'nginx', 'httpd'
    ],
    'non-work': [
        'spotify.exe', 'vlc.exe', 'mpv.exe', 'wmplayer.exe',
        'steam.exe', 'epicgameslauncher.exe', 'whatsapp.exe',
        'telegram.exe', 'signal.exe', 'messenger.exe'
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

# First, show current state
print("\n1. Current category distribution:")
cur.execute("""
    SELECT 
        CASE 
            WHEN category IS NULL OR category = '' THEN 'NULL/Empty'
            ELSE category 
        END as cat,
        COUNT(*) as count
    FROM activity_records
    GROUP BY cat
    ORDER BY count DESC
""")

for cat, count in cur.fetchall():
    print(f"   {cat}: {count} records")

# Update all records with proper categories
print("\n2. Updating categories based on application names...")

cur.execute("""
    SELECT DISTINCT application_name
    FROM activity_records
    WHERE application_name IS NOT NULL
""")

app_names = cur.fetchall()
total_updated = 0

for (app_name,) in app_names:
    category = categorize_app(app_name)
    
    # Update all records with this app name
    cur.execute("""
        UPDATE activity_records
        SET category = %s
        WHERE application_name = %s
    """, (category, app_name))
    
    updated = cur.rowcount
    total_updated += updated
    
    if updated > 0:
        print(f"   {app_name} -> {category} ({updated} records)")

conn.commit()

print(f"\n✅ Total records updated: {total_updated}")

# Show new distribution
print("\n3. New category distribution:")
cur.execute("""
    SELECT category, COUNT(*) as count
    FROM activity_records
    GROUP BY category
    ORDER BY count DESC
""")

for cat, count in cur.fetchall():
    print(f"   {cat}: {count} records")

# Show sample categorized apps
print("\n4. Sample categorized applications:")
for category in ['productivity', 'browser', 'server', 'non-work', 'uncategorized']:
    print(f"\n   {category.upper()}:")
    cur.execute("""
        SELECT DISTINCT application_name, COUNT(*) as count
        FROM activity_records
        WHERE category = %s
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 5
    """, (category,))
    
    apps = cur.fetchall()
    if apps:
        for app, count in apps:
            print(f"      - {app}: {count} records")
    else:
        print("      (no applications)")

cur.close()
conn.close()

print("\n✅ Categorization complete! Your dashboard should now show proper categories.")
