# debug_api_error.py
# Debug the 500 error in the activity data API

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import datetime, date

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

print("=== Debugging Activity API Error ===\n")

# The date range from your screenshot
start_date = "2025-09-30"
end_date = "2025-10-08"
developer_id = "riddhidhakhara"  # From the URL

print(f"Date range: {start_date} to {end_date}")
print(f"Developer: {developer_id}")

with engine.connect() as conn:
    # 1. Check if the developer exists (case-sensitive check)
    print("\n1. Checking developer variations...")
    result = conn.execute(text("""
        SELECT DISTINCT CAST(developer_id AS VARCHAR) as dev_id, COUNT(*) as count
        FROM activity_records
        WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
        GROUP BY developer_id
    """), {'dev_id': developer_id})
    
    developers = result.fetchall()
    if developers:
        print("   Found developer(s):")
        for dev, count in developers:
            print(f"   - '{dev}' ({count} records)")
            actual_dev_id = dev  # Use the actual case from DB
    else:
        print("   ❌ Developer not found!")
        print("\n   All developers in database:")
        result = conn.execute(text("""
            SELECT DISTINCT CAST(developer_id AS VARCHAR) as dev_id
            FROM activity_records
            ORDER BY 1
        """))
        for (dev,) in result:
            print(f"   - {dev}")
    
    # 2. Check date range data
    print(f"\n2. Checking data in date range {start_date} to {end_date}...")
    result = conn.execute(text("""
        SELECT 
            DATE(timestamp) as activity_date,
            COUNT(*) as records,
            SUM(duration) / 3600 as hours
        FROM activity_records
        WHERE DATE(timestamp) BETWEEN :start_date AND :end_date
        GROUP BY DATE(timestamp)
        ORDER BY activity_date
    """), {'start_date': start_date, 'end_date': end_date})
    
    dates = result.fetchall()
    if dates:
        print("   Data found:")
        for act_date, records, hours in dates:
            hours_val = hours if hours else 0
            print(f"   {act_date}: {records} records, {hours_val:.1f} hours")
    else:
        print("   ❌ No data in this date range!")
        
        # Find actual date range
        result = conn.execute(text("""
            SELECT MIN(DATE(timestamp)), MAX(DATE(timestamp))
            FROM activity_records
        """))
        min_date, max_date = result.fetchone()
        print(f"\n   Actual data range: {min_date} to {max_date}")
    
    # 3. Test the actual query that might be failing
    if developers:
        print("\n3. Testing activity query...")
        try:
            result = conn.execute(text("""
                SELECT 
                    CAST(developer_id AS VARCHAR) as dev_id,
                    application_name,
                    window_title,
                    duration,
                    timestamp,
                    category
                FROM activity_records
                WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
                AND DATE(timestamp) BETWEEN :start_date AND :end_date
                AND application_name IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 10
            """), {
                'dev_id': developer_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            records = result.fetchall()
            if records:
                print(f"   ✓ Query successful, found {len(records)} records")
                for i, record in enumerate(records[:3]):
                    print(f"   Sample {i+1}: {record[1]} - {record[2][:50]}...")
            else:
                print("   ⚠️ Query successful but no records found")
                
        except Exception as e:
            print(f"   ❌ Query failed: {str(e)}")
            print("   This might be the cause of your 500 error!")

print("\n4. LIKELY ISSUES:")
print("   1. Case sensitivity: Database might have 'RiddhiDhakhara' but API uses 'riddhidhakhara'")
print("   2. Date range: Your data might be outside Sep 30 - Oct 8, 2025")
print("   3. Missing columns: application_name or category might be NULL")
print("   4. Database connection issues in production")
