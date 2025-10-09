from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL","postgresql://postgres:asdf1234@localhost:5432/timesheet")
engine = create_engine(DATABASE_URL)

def extract_app_name_from_json(activity_data):
    """Extract application name from activity_data JSON"""
    try:
        if isinstance(activity_data, str):
            data = json.loads(activity_data)
        else:
            data = activity_data
        
        # Try different possible locations for app name
        app_name = None
        
        # Common patterns in activity_data
        if 'app' in data:
            app_name = data['app']
        elif 'data' in data and isinstance(data['data'], dict):
            if 'app' in data['data']:
                app_name = data['data']['app']
            elif 'current_window' in data['data']:
                # ActivityWatch format
                window_data = data['data']['current_window']
                if 'app' in window_data:
                    app_name = window_data['app']
        elif 'current_window' in data:
            if 'app' in data['current_window']:
                app_name = data['current_window']['app']
        
        return app_name
    except:
        return None

def categorize_activity(app_name, window_title):
    """Categorize activity based on app name and window title"""
    app_name = (app_name or '').lower()
    window_title = (window_title or '').lower()
    
    # Productivity apps (IDEs, terminals, etc.)
    productivity_apps = [
        'code.exe', 'code', 'vscode', 'cursor.exe', 'cursor',
        'terminal', 'cmd.exe', 'powershell', 'bash',
        'pycharm', 'idea', 'eclipse', 'sublime', 'notepad++',
        'git', 'docker', 'postman', 'mysql', 'pgadmin'
    ]
    
    # Server-related keywords
    server_keywords = [
        'aws', 'amazon', 'ec2', 's3', 'lambda',
        'azure', 'gcp', 'google cloud',
        'digitalocean', 'heroku', 'vercel', 'netlify',
        'github', 'gitlab', 'bitbucket',
        'localhost:', '127.0.0.1:', ':3000', ':8000', ':5000',
        'phpmyadmin', 'database', 'server'
    ]
    
    # Unproductive keywords
    unproductive_keywords = [
        'youtube', 'facebook', 'instagram', 'twitter',
        'netflix', 'reddit', 'whatsapp', 'telegram',
        'gaming', 'twitch', 'discord'
    ]
    
    # Determine category
    if any(app in app_name for app in productivity_apps):
        return 'productivity'
    elif any(browser in app_name for browser in ['chrome', 'firefox', 'edge', 'brave']):
        # Check window title for browser categorization
        if any(keyword in window_title for keyword in server_keywords):
            return 'server'
        elif any(keyword in window_title for keyword in unproductive_keywords):
            return 'unproductive'
        else:
            return 'browser'
    elif 'explorer' in app_name:
        return 'system'
    else:
        return 'other'

print("=== Fixing Categories from activity_data JSON ===")

with engine.connect() as conn:
    # First check if we have application_name column
    check_columns = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'activity_records' 
        AND column_name IN ('application_name', 'category')
    """))
    
    columns = [row[0] for row in check_columns]
    has_app_name_column = 'application_name' in columns
    has_category_column = 'category' in columns
    
    print(f"\nDatabase schema check:")
    print(f"  Has application_name column: {has_app_name_column}")
    print(f"  Has category column: {has_category_column}")
    
    if not has_category_column:
        print("\n⚠️  Warning: 'category' column not found in activity_records table!")
        print("Adding category column...")
        conn.execute(text("ALTER TABLE activity_records ADD COLUMN category VARCHAR(50)"))
        conn.commit()
    
    # Get sample records to understand JSON structure
    print("\n1. Analyzing activity_data structure:")
    result = conn.execute(text("""
        SELECT id, activity_data, window_title
        FROM activity_records 
        WHERE activity_data IS NOT NULL 
        LIMIT 5
    """))
    
    for row in result:
        try:
            app_name = extract_app_name_from_json(row.activity_data)
            print(f"\nRecord {row.id}:")
            print(f"  Extracted app: {app_name}")
            print(f"  Window title: {row.window_title[:50]}...")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Now update all records
    print("\n2. Updating categories for all records...")
    
    # Process in batches to avoid memory issues
    batch_size = 1000
    offset = 0
    total_updated = 0
    
    while True:
        records = conn.execute(text("""
            SELECT id, activity_data, window_title
            FROM activity_records 
            WHERE activity_data IS NOT NULL
            ORDER BY id
            LIMIT :batch_size OFFSET :offset
        """), {'batch_size': batch_size, 'offset': offset})
        
        batch_records = list(records)
        if not batch_records:
            break
        
        for record in batch_records:
            try:
                # Extract app name from JSON
                app_name = extract_app_name_from_json(record.activity_data)
                
                if app_name:
                    # Determine category
                    category = categorize_activity(app_name, record.window_title or '')
                    
                    # Update the record
                    if has_app_name_column:
                        conn.execute(text("""
                            UPDATE activity_records 
                            SET application_name = :app_name, 
                                category = :category 
                            WHERE id = :id
                        """), {
                            'app_name': app_name,
                            'category': category,
                            'id': record.id
                        })
                    else:
                        conn.execute(text("""
                            UPDATE activity_records 
                            SET category = :category 
                            WHERE id = :id
                        """), {
                            'category': category,
                            'id': record.id
                        })
                    total_updated += 1
            except Exception as e:
                print(f"Error updating record {record.id}: {e}")
        
        conn.commit()
        offset += batch_size
        print(f"  Processed {offset} records...")
    
    print(f"\n✓ Updated {total_updated} records with categories")
    
    # Show final statistics
    print("\n3. Final Statistics:")
    
    # Today's data
    result = conn.execute(text("""
        SELECT 
            category,
            COUNT(*) as count,
            COUNT(DISTINCT developer_id) as developers,
            SUM(duration) / 3600.0 as hours
        FROM activity_records
        WHERE timestamp >= CURRENT_DATE
        GROUP BY category
        ORDER BY hours DESC
    """))
    
    print("\nToday's Category Distribution:")
    today_total_hours = 0
    for row in result:
        print(f"  {row.category or 'uncategorized'}: {row.count} records, {row.hours:.2f} hours, {row.developers} developers")
        today_total_hours += row.hours or 0
    print(f"\nTotal hours today: {today_total_hours:.2f}")
    
    # All-time data
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT developer_id) as total_developers,
            COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as categorized_records,
            COUNT(CASE WHEN category IS NULL THEN 1 END) as uncategorized_records
        FROM activity_records
    """))
    
    row = result.fetchone()
    print(f"\nAll-time Statistics:")
    print(f"  Total records: {row.total_records}")
    print(f"  Total developers: {row.total_developers}")
    print(f"  Categorized records: {row.categorized_records}")
    print(f"  Uncategorized records: {row.uncategorized_records}")
    
    # Sample uncategorized records
    if row.uncategorized_records > 0:
        print(f"\n⚠️  Found {row.uncategorized_records} uncategorized records")
        print("Sample uncategorized records:")
        uncategorized = conn.execute(text("""
            SELECT id, window_title, activity_data
            FROM activity_records 
            WHERE category IS NULL
            LIMIT 5
        """))
        
        for record in uncategorized:
            app = extract_app_name_from_json(record.activity_data)
            print(f"  ID {record.id}: app='{app}', title='{record.window_title[:50] if record.window_title else 'None'}'")

print("\n✅ Script completed! Now restart your dashboard API:")
print("   pkill -f dashboard_api")
print("   python dashboard_api.py")