"""
Run this script to fix all activity data issues
Usage: python3 run_all_fixes.py
"""

from sqlalchemy import create_engine, text
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import Config

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

def categorize_activity(app_name, window_title):
    """Categorize activity based on app and title"""
    if not app_name:
        return 'other'
    
    app_lower = str(app_name).lower()
    title_lower = str(window_title).lower() if window_title else ""
    
    # Remove .exe
    app_base = app_lower.replace('.exe', '')
    
    # Productivity apps
    if app_base in ['code', 'cursor', 'windowsterminal', 'terminus', 'notepad',
                    'cmd', 'powershell', 'git', 'python', 'node', 'npm',
                    'pycharm', 'intellij', 'sublime', 'atom', 'vim']:
        return 'productivity'
    
    # System
    if app_base in ['explorer', 'finder', 'nautilus']:
        return 'system'
    
    # Browsers
    if app_base in ['chrome', 'firefox', 'edge', 'msedge', 'brave', 'opera']:
        # Server keywords
        if any(kw in title_lower for kw in ['aws', 'azure', 'gcp', 'localhost', 
                                            'github', ':3000', ':8000', ':5000']):
            return 'server'
        # Unproductive
        if any(kw in title_lower for kw in ['youtube', 'facebook', 'instagram', 
                                            'twitter', 'reddit', 'netflix']):
            return 'unproductive'
        return 'browser'
    
    # Communication
    if app_base in ['teams', 'slack', 'zoom', 'skype']:
        return 'communication'
    
    return 'other'

print("=== FIXING ALL ACTIVITY DATA ISSUES ===\n")

# Step 1: Categorize all activities
print("STEP 1: Categorizing all activities...")
print("-" * 50)

with engine.connect() as conn:
    # Get uncategorized records
    result = conn.execute(text("""
        SELECT id, application_name, window_title
        FROM activity_records
        WHERE category IS NULL OR category = ''
    """))
    
    records = list(result)
    print(f"Found {len(records)} uncategorized records")
    
    # Categorize in batches
    batch_size = 500
    categorized = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        
        for record in batch:
            category = categorize_activity(record.application_name, record.window_title)
            
            conn.execute(text("""
                UPDATE activity_records
                SET category = :category
                WHERE id = :id
            """), {
                'id': record.id,
                'category': category
            })
            categorized += 1
        
        conn.commit()
        print(f"Progress: {categorized}/{len(records)}")
    
    print(f"✅ Categorized {categorized} records\n")

# Step 2: Verify data
print("STEP 2: Verifying data...")
print("-" * 50)

with engine.connect() as conn:
    # Overall stats
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT developer_id) as developers,
            COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as categorized
        FROM activity_records
    """))
    
    stats = result.first()
    print(f"Total records: {stats.total}")
    print(f"Total developers: {stats.developers}")
    print(f"Categorized: {stats.categorized} ({stats.categorized/stats.total*100:.1f}%)")
    
    # Category breakdown
    print("\nCategory breakdown:")
    result = conn.execute(text("""
        SELECT category, COUNT(*) as count
        FROM activity_records
        GROUP BY category
        ORDER BY count DESC
    """))
    
    for cat, count in result:
        pct = count / stats.total * 100
        print(f"  {(cat or 'NULL'):<15} {count:>7} ({pct:>5.1f}%)")
    
    print()

# Step 3: Test specific developer
print("STEP 3: Testing developer 'ankita_gholap'...")
print("-" * 50)

developer_id = "ankita_gholap"
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=7)

with engine.connect() as conn:
    # Check data
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN category = 'productivity' THEN 1 END) as prod,
            COUNT(CASE WHEN category = 'server' THEN 1 END) as server,
            COUNT(CASE WHEN category = 'unproductive' THEN 1 END) as unprod,
            COUNT(CASE WHEN category = 'browser' THEN 1 END) as browser
        FROM activity_records
        WHERE developer_id = :dev_id
        AND timestamp >= :start_date
        AND timestamp <= :end_date
    """), {
        'dev_id': developer_id,
        'start_date': start_date,
        'end_date': end_date
    })
    
    data = result.first()
    print(f"Records in last 7 days: {data.total}")
    print(f"  Productivity: {data.prod}")
    print(f"  Server: {data.server}")
    print(f"  Unproductive: {data.unprod}")
    print(f"  Browser: {data.browser}")
    
    # Sample activities
    print("\nRecent activities:")
    result = conn.execute(text("""
        SELECT application_name, category, window_title, timestamp
        FROM activity_records
        WHERE developer_id = :dev_id
        ORDER BY timestamp DESC
        LIMIT 5
    """), {'dev_id': developer_id})
    
    for app, cat, title, ts in result:
        title_short = (title[:40] + '...') if title and len(title) > 40 else title
        print(f"  [{cat:<12}] {app:<20} {title_short}")

# Step 4: Instructions
print("\n" + "="*60)
print("✅ DATABASE FIXES COMPLETE!")
print("="*60)

print("\nNOW YOU NEED TO:")
print("\n1. Add the API endpoint to your main.py:")
print("   - Copy the code from 'working_api_endpoint.py'")
print("   - Add it to your FastAPI application")

print("\n2. Restart your backend server:")
print("   cd /var/www/html/timesheet/backend")
print("   # Kill existing process if running")
print("   # Then start:")
print("   python3 main.py")
print("   # or")
print("   uvicorn main:app --reload --host 0.0.0.0 --port 5000")

print("\n3. Test the API:")
print("   curl http://localhost:5000/api/activity-data/ankita_gholap?start_date=2025-09-30T00:00:00Z&end_date=2025-10-07T23:59:59Z")

print("\n4. Clear browser cache and reload dashboard")

print("\nIf you still see the 'other' error:")
print("- The API endpoint code might not be updated")
print("- Check if the endpoint is returning 'other' as an error message")
print("- Look at the server logs for the actual error")

print("\n✅ Script complete!")