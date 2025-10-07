from sqlalchemy import create_engine, text
import json
import os
import re
from dotenv import load_dotenv
from config import Config

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

def extract_app_info_from_json(activity_data):
    """
    Extract application name and window title from activity JSON data
    """
    if not activity_data:
        return None, None
    
    try:
        # Parse JSON if it's a string
        if isinstance(activity_data, str):
            data = json.loads(activity_data)
        else:
            data = activity_data
        
        # Look for app info in different possible locations
        app_name = None
        window_title = None
        
        # Common patterns in ActivityWatch data
        if 'app' in data:
            app_name = data['app']
        elif 'application' in data:
            app_name = data['application']
        elif 'program' in data:
            app_name = data['program']
        elif 'process' in data:
            app_name = data['process']
        
        # Look for window title
        if 'title' in data:
            window_title = data['title']
        elif 'window' in data:
            window_title = data['window']
        elif 'window_title' in data:
            window_title = data['window_title']
        
        # Sometimes the data is nested
        if not app_name and 'data' in data:
            nested = data['data']
            if isinstance(nested, dict):
                app_name = nested.get('app') or nested.get('application')
                window_title = window_title or nested.get('title') or nested.get('window_title')
        
        return app_name, window_title
        
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing JSON: {e}")
        return None, None

def categorize_activity(app_name, window_title):
    """
    Categorize activity based on app name and window title
    """
    if not app_name:
        return 'other'
    
    app_lower = str(app_name).lower()
    title_lower = str(window_title).lower() if window_title else ""
    
    # Remove .exe extension for comparison
    app_base = app_lower.replace('.exe', '')
    
    # PRODUCTIVITY - Development and work tools
    productivity_apps = {
        'code', 'vscode', 'visual studio code', 'visualstudio', 'devenv',
        'pycharm', 'pycharm64', 'idea', 'idea64', 'intellij',
        'eclipse', 'notepad++', 'sublime_text', 'sublime', 'atom',
        'brackets', 'webstorm', 'phpstorm', 'rubymine', 'goland',
        'cursor', 'notepad', 'vim', 'gvim', 'emacs', 'nano',
        'windowsterminal', 'terminal', 'cmd', 'powershell',
        'bash', 'sh', 'zsh', 'terminus', 'iterm', 'wezterm',
        'conemu', 'cmder', 'hyper', 'mintty', 'konsole',
        'git', 'git-bash', 'github desktop', 'sourcetree',
        'gitkraken', 'tortoisegit', 'docker', 'docker desktop',
        'postman', 'insomnia', 'paw', 'soapui', 'thunder client',
        'dbeaver', 'mysql', 'mysqld', 'mysql workbench', 'pgadmin', 'pgadmin4',
        'mongodb compass', 'mongod', 'redis', 'redis-server',
        'tableplus', 'sequel pro', 'heidisql', 'navicat',
        'filezilla', 'winscp', 'putty', 'vnc', 'anydesk',
        'virtualbox', 'vmware', 'vagrant', 'parallels'
    }
    
    # Check if it's a productivity app
    if app_base in productivity_apps:
        return 'productivity'
    
    # System applications
    system_apps = {'explorer', 'finder', 'nautilus', 'thunar', 'dolphin', 'files'}
    if app_base in system_apps:
        return 'system'
    
    # Browsers - need to check window title
    browsers = {'chrome', 'firefox', 'msedge', 'edge', 'brave', 'opera', 
                'vivaldi', 'safari', 'chromium', 'waterfox'}
    
    if app_base in browsers:
        # SERVER patterns
        server_patterns = [
            # AWS
            r'console\.aws', r'aws\.amazon', r'amazonaws', r'\baws\b',
            r'\bec2\b', r'\bs3\b', r'lambda', r'cloudfront', r'elasticbeanstalk',
            r'cloudformation', r'route53', r'rds\b', r'dynamodb',
            
            # Google Cloud
            r'console\.cloud\.google', r'cloud\.google', r'\bgcp\b',
            r'compute engine', r'app engine', r'cloud storage', r'firebase',
            
            # Azure
            r'portal\.azure', r'azure\.microsoft', r'\bazure\b',
            r'azure devops', r'visualstudio\.com',
            
            # Other Cloud/Hosting
            r'digitalocean', r'heroku', r'netlify', r'vercel', r'render\.com',
            r'cloudflare', r'linode', r'vultr', r'railway\.app',
            
            # Development/DevOps
            r'github\.com', r'gitlab', r'bitbucket', r'jenkins', r'circleci',
            r'travis-ci', r'docker', r'kubernetes', r'k8s\.io',
            
            # Local Development
            r'localhost', r'127\.0\.0\.1', r'0\.0\.0\.0', r'192\.168\.',
            r':[0-9]{4}', r'localhost:[0-9]+',
            
            # Development Sites
            r'stackoverflow', r'developer\.', r'developers\.', r'docs\.',
            r'documentation', r'api\.', r'console\.', r'admin\.',
            r'dashboard', r'control panel',
            
            # Databases/Tools
            r'phpmyadmin', r'adminer', r'mongodb\.com', r'redis\.io',
            r'elastic\.co', r'grafana', r'kibana', r'prometheus'
        ]
        
        # UNPRODUCTIVE patterns
        unproductive_patterns = [
            # Social Media
            r'facebook', r'instagram', r'twitter', r'\bx\.com', r'tiktok',
            r'linkedin\.com', r'pinterest', r'tumblr', r'snapchat', r'threads',
            r'mastodon', r'discord\.com', r'whatsapp', r'telegram',
            
            # Video/Streaming
            r'youtube', r'youtu\.be', r'netflix', r'twitch\.tv', r'vimeo',
            r'dailymotion', r'hulu', r'disney', r'disneyplus', r'hbomax',
            r'primevideo', r'prime video', r'hotstar', r'sonyliv', r'zee5',
            r'crunchyroll', r'funimation',
            
            # Music
            r'spotify', r'soundcloud', r'pandora', r'deezer', r'apple music',
            r'jiosaavn', r'gaana', r'wynk', r'amazon music',
            
            # Shopping
            r'amazon\.com', r'amazon\.in', r'amazon\.', r'flipkart', r'ebay',
            r'alibaba', r'aliexpress', r'myntra', r'ajio', r'shopify',
            r'etsy', r'walmart', r'bestbuy', r'target\.com',
            
            # Entertainment/News
            r'reddit', r'9gag', r'imgur', r'buzzfeed', r'medium\.com',
            r'news\.', r'cnn\.', r'bbc\.', r'foxnews', r'ndtv', r'timesofindia',
            
            # Gaming
            r'steam', r'epicgames', r'origin', r'battle\.net', r'roblox',
            r'minecraft', r'fortnite', r'valorant', r'leagueoflegends',
            r'twitch', r'gaming', r'games\.', r'ign\.com'
        ]
        
        # Check patterns
        for pattern in server_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return 'server'
        
        for pattern in unproductive_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return 'unproductive'
        
        # Default browser is general browsing
        return 'browser'
    
    # Communication apps
    comm_apps = {'teams', 'slack', 'zoom', 'skype', 'discord', 'telegram', 'whatsapp'}
    if app_base in comm_apps:
        return 'communication'
    
    # Office apps
    office_apps = {'winword', 'excel', 'powerpnt', 'outlook', 'onenote', 
                   'msaccess', 'mspub', 'visio', 'word', 'powerpoint'}
    if app_base in office_apps:
        return 'office'
    
    # Default
    return 'other'

print("=== Categorizing Activities from JSON Data ===")

with engine.connect() as conn:
    # 1. First, let's check what's in the JSON
    print("\n1. Analyzing JSON structure:")
    result = conn.execute(text("""
        SELECT activity_data
        FROM activity_records
        WHERE activity_data IS NOT NULL
        LIMIT 5
    """))
    
    sample_count = 0
    for row in result:
        sample_count += 1
        app, title = extract_app_info_from_json(row[0])
        if app or title:
            print(f"   Sample {sample_count}: app='{app}', title='{title}'")
            if sample_count == 1:
                # Show the full structure of first record
                data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                print(f"   JSON structure: {json.dumps(data, indent=2)[:500]}...")
    
    # 2. Update application_name and window_title from JSON
    print("\n2. Extracting app info from JSON and updating records...")
    
    # Get records with JSON data but missing app info
    result = conn.execute(text("""
        SELECT id, activity_data, application_name, window_title
        FROM activity_records
        WHERE activity_data IS NOT NULL
        AND (application_name IS NULL OR application_name = '')
    """))
    
    records_to_update = list(result)
    print(f"   Found {len(records_to_update)} records with JSON but no app name")
    
    # Update in batches
    batch_size = 500
    updated_count = 0
    
    for i in range(0, len(records_to_update), batch_size):
        batch = records_to_update[i:i+batch_size]
        
        for record in batch:
            app_name, window_title = extract_app_info_from_json(record.activity_data)
            
            if app_name:
                # Update the record
                conn.execute(text("""
                    UPDATE activity_records
                    SET application_name = :app_name,
                        window_title = COALESCE(:window_title, window_title)
                    WHERE id = :id
                """), {
                    'id': record.id,
                    'app_name': app_name,
                    'window_title': window_title
                })
                updated_count += 1
        
        conn.commit()
        print(f"   Updated {min(i + batch_size, len(records_to_update))}/{len(records_to_update)} records")
    
    print(f"   Total records updated with app info: {updated_count}")
    
    # 3. Now categorize all records
    print("\n3. Categorizing all records based on app and title...")
    
    result = conn.execute(text("""
        SELECT id, application_name, window_title
        FROM activity_records
        WHERE application_name IS NOT NULL
        AND (category IS NULL OR category = '')
    """))
    
    records_to_categorize = list(result)
    print(f"   Found {len(records_to_categorize)} records to categorize")
    
    # Categorize in batches
    category_stats = {}
    
    for i in range(0, len(records_to_categorize), batch_size):
        batch = records_to_categorize[i:i+batch_size]
        
        for record in batch:
            category = categorize_activity(record.application_name, record.window_title)
            
            # Update category
            conn.execute(text("""
                UPDATE activity_records
                SET category = :category
                WHERE id = :id
            """), {
                'id': record.id,
                'category': category
            })
            
            category_stats[category] = category_stats.get(category, 0) + 1
        
        conn.commit()
        print(f"   Categorized {min(i + batch_size, len(records_to_categorize))}/{len(records_to_categorize)} records")
    
    # 4. Show final results
    print("\n4. Final Results:")
    print("\n   Category Distribution:")
    result = conn.execute(text("""
        SELECT category, COUNT(*) as count
        FROM activity_records
        GROUP BY category
        ORDER BY count DESC
    """))
    
    for cat, count in result:
        print(f"   {cat or 'NULL':<15} {count:>7} records")
    
    print("\n   Top Applications by Category:")
    categories = ['productivity', 'server', 'unproductive', 'browser', 'system']
    
    for cat in categories:
        print(f"\n   {cat.upper()}:")
        result = conn.execute(text("""
            SELECT application_name, COUNT(*) as count
            FROM activity_records
            WHERE category = :category
            GROUP BY application_name
            ORDER BY count DESC
            LIMIT 5
        """), {"category": cat})
        
        for app, count in result:
            print(f"      {app:<25} {count:>6} records")
    
    # 5. Show sample categorized activities
    print("\n5. Sample Categorized Activities:")
    result = conn.execute(text("""
        SELECT application_name, window_title, category
        FROM activity_records
        WHERE category IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
    """))
    
    for app, title, cat in result:
        title_preview = (title[:60] + '...') if title and len(title) > 60 else (title or 'No title')
        print(f"   [{cat:<12}] {app:<20} | {title_preview}")

print("\n✅ Categorization complete!")
print("\nNote: If some records still lack categories, it may be because:")
print("- The JSON doesn't contain app information")
print("- The app is not in our categorization rules")
print("- The JSON structure is different than expected")