# debug_duration_issue.py
# Debug why durations are 0

from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv
from datetime import datetime, date

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

def debug_duration_issue():
    """Debug why durations are showing as 0"""
    
    print("=== Debugging Duration Issue ===\n")
    
    with engine.connect() as conn:
        # 1. Check duration values
        print("1. Checking duration values in database...")
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN duration IS NULL THEN 1 END) as null_durations,
                COUNT(CASE WHEN duration = 0 THEN 1 END) as zero_durations,
                COUNT(CASE WHEN duration > 0 THEN 1 END) as positive_durations,
                AVG(duration) as avg_duration,
                MAX(duration) as max_duration
            FROM activity_records
        """))
        
        stats = result.fetchone()
        print(f"   Total records: {stats[0]}")
        print(f"   NULL durations: {stats[1]}")
        print(f"   Zero durations: {stats[2]}")
        print(f"   Positive durations: {stats[3]}")
        avg_dur = stats[4] if stats[4] else 0
        max_dur = stats[5] if stats[5] else 0
        print(f"   Average duration: {avg_dur:.2f} seconds")
        print(f"   Max duration: {max_dur:.2f} seconds")
        
        # 2. Check sample records
        print("\n2. Sample records with duration data...")
        result = conn.execute(text("""
            SELECT 
                developer_id,
                application_name,
                duration,
                timestamp,
                activity_data
            FROM activity_records
            WHERE developer_id IN ('ankita gholap', 'RiddhiDhakhara', 'ankita_gholap')
            ORDER BY timestamp DESC
            LIMIT 10
        """))
        
        records = result.fetchall()
        for i, record in enumerate(records):
            print(f"\n   Record {i+1}:")
            print(f"   Developer: {record[0]}")
            print(f"   App: {record[1]}")
            print(f"   Duration: {record[2]} seconds")
            print(f"   Timestamp: {record[3]}")
            
            # Check if duration is in JSON
            if record[4]:
                try:
                    data = json.loads(record[4]) if isinstance(record[4], str) else record[4]
                    if 'duration' in data:
                        print(f"   Duration in JSON: {data['duration']}")
                    if 'timestamp' in data and 'start_time' in data:
                        # Calculate duration from timestamps
                        print(f"   Timestamps in JSON - can calculate duration")
                except:
                    pass
        
        # 3. Check today's data specifically
        print("\n3. Checking today's data...")
        today = date.today()
        result = conn.execute(text("""
            SELECT 
                developer_id,
                COUNT(*) as count,
                SUM(duration) as total_duration,
                AVG(duration) as avg_duration
            FROM activity_records
            WHERE DATE(timestamp) = :today
            GROUP BY developer_id
        """), {'today': today})
        
        today_data = result.fetchall()
        if today_data:
            for dev_id, count, total_dur, avg_dur in today_data:
                total_s = total_dur if total_dur else 0
                avg_s = avg_dur if avg_dur else 0
                print(f"   {dev_id}: {count} records, {total_s:.0f} total seconds, {avg_s:.0f} avg seconds")
        else:
            print("   No data for today!")
        
        # 4. Check if we need to extract duration from JSON
        print("\n4. Checking if duration needs to be extracted from activity_data...")
        result = conn.execute(text("""
            SELECT activity_data
            FROM activity_records
            WHERE activity_data IS NOT NULL
            AND activity_data != '{}'
            LIMIT 5
        """))
        
        for (data_str,) in result:
            try:
                data = json.loads(data_str) if isinstance(data_str, str) else data_str
                if isinstance(data, dict):
                    # Look for duration fields
                    duration_found = False
                    if 'duration' in data:
                        print(f"   Found 'duration' in JSON: {data['duration']}")
                        duration_found = True
                    if 'data' in data and isinstance(data['data'], dict) and 'duration' in data['data']:
                        print(f"   Found 'duration' in nested data: {data['data']['duration']}")
                        duration_found = True
                    
                    # Check for timestamp fields to calculate duration
                    if 'timestamp' in data and 'end_timestamp' in data:
                        print(f"   Found timestamp fields - can calculate duration")
                        duration_found = True
                    
                    if not duration_found:
                        print(f"   No duration info in this JSON record")
                        print(f"   Keys available: {list(data.keys())}")
            except:
                pass
        
        # 5. Fix suggestion
        print("\n5. SOLUTION:")
        if stats[1] > 0 or stats[2] > 0:
            print("   ✅ Need to extract/calculate duration from activity_data JSON")
            print("   Run: python fix_duration_data.py")
        else:
            print("   ❓ Duration data exists but may not be for today")
            print("   Check your data sync process")

if __name__ == "__main__":
    debug_duration_issue()
