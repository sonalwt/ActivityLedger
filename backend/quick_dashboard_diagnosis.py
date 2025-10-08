# quick_dashboard_diagnosis.py
# Run this first to understand why your dashboard is empty

from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'timesheet_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

def diagnose_dashboard_issue():
    """Quick diagnosis of why dashboard shows empty data"""
    
    print("=== Dashboard Empty Data Diagnosis ===\n")
    
    with engine.connect() as conn:
        # 1. Check if data exists
        print("1. Checking if activity data exists...")
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT developer_id) as developers,
                   MIN(timestamp) as earliest,
                   MAX(timestamp) as latest
            FROM activity_records
        """))
        
        row = result.fetchone()
        if row[0] == 0:
            print("   ❌ No activity records found in database!")
            return
        
        print(f"   ✓ Found {row[0]} records")
        print(f"   ✓ {row[1]} developers")
        print(f"   ✓ Date range: {row[2]} to {row[3]}")
        
        # 2. Check developers
        print("\n2. Developers in database:")
        result = conn.execute(text("""
            SELECT DISTINCT developer_id, COUNT(*) as records
            FROM activity_records
            WHERE developer_id IS NOT NULL
            GROUP BY developer_id
            ORDER BY developer_id
        """))
        
        developers = result.fetchall()
        for dev_id, count in developers:
            print(f"   - {dev_id}: {count} records")
        
        # 3. Check data format
        print("\n3. Checking data format...")
        result = conn.execute(text("""
            SELECT 
                COUNT(CASE WHEN activity_data IS NOT NULL AND activity_data != '{}' THEN 1 END) as has_json,
                COUNT(CASE WHEN application_name IS NOT NULL THEN 1 END) as has_app_name,
                COUNT(CASE WHEN window_title IS NOT NULL THEN 1 END) as has_title
            FROM activity_records
        """))
        
        stats = result.fetchone()
        print(f"   Records with activity_data (JSON): {stats[0]}")
        print(f"   Records with application_name: {stats[1]}")
        print(f"   Records with window_title: {stats[2]}")
        
        if stats[0] > 0 and stats[1] == 0:
            print("\n   ⚠️ PROBLEM FOUND: Data is in JSON format but not extracted to columns!")
            print("   The dashboard expects data in individual columns.")
        
        # 4. Show sample JSON structure
        print("\n4. Sample activity_data JSON structure:")
        result = conn.execute(text("""
            SELECT activity_data 
            FROM activity_records 
            WHERE activity_data IS NOT NULL 
            AND activity_data != '{}' 
            AND activity_data != ''
            LIMIT 1
        """))
        
        row = result.fetchone()
        if row and row[0]:
            try:
                data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                print(json.dumps(data, indent=4))
                
                # Analyze structure
                print("\n5. JSON Structure Analysis:")
                if isinstance(data, dict):
                    print(f"   Top-level keys: {list(data.keys())}")
                    
                    # Check for app info
                    has_app = False
                    if 'app' in data or 'application' in data:
                        has_app = True
                        print("   ✓ Found app field at root level")
                    elif 'data' in data and isinstance(data['data'], dict):
                        if 'app' in data['data']:
                            has_app = True
                            print("   ✓ Found app field in nested 'data'")
                    elif 'file' in data or 'project' in data:
                        has_app = True
                        print("   ✓ Found file/project based structure")
                    
                    if not has_app:
                        print("   ❌ No recognizable app/file fields found!")
                
            except Exception as e:
                print(f"   Error parsing JSON: {e}")
        
        # 5. Check today's data specifically
        print("\n6. Checking today's data...")
        today = datetime.now().date()
        result = conn.execute(text("""
            SELECT COUNT(*) as count,
                   COUNT(DISTINCT developer_id) as devs,
                   SUM(duration) / 3600 as hours
            FROM activity_records
            WHERE DATE(timestamp) = :today
        """), {'today': today})
        
        row = result.fetchone()
        if row[0] > 0:
            print(f"   Today's records: {row[0]}")
            print(f"   Active developers: {row[1]}")
            print(f"   Total hours: {row[2]:.1f if row[2] else 0}")
        else:
            print("   ❌ No data for today!")
        
        # 6. Solution
        print("\n7. SOLUTION:")
        if stats[0] > 0 and stats[1] == 0:
            print("   ✅ Run the flexible_dashboard_fix.py script to extract JSON data")
            print("   This will populate the required columns for the dashboard")
        else:
            print("   ❓ Check your data collection/sync process")
            print("   ❓ Verify the dashboard API is connecting to the correct database")

if __name__ == "__main__":
    diagnose_dashboard_issue()
