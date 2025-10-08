# debug_duration_issue_fixed.py
# Debug why durations are 0 - Fixed for VARCHAR developer_id

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
        
        # Get actual developer IDs first
        print("\n2. Finding actual developer IDs...")
        result = conn.execute(text("""
            SELECT DISTINCT CAST(developer_id AS VARCHAR) as dev_id
            FROM activity_records
            WHERE developer_id IS NOT NULL
            ORDER BY 1
        """))
        
        dev_ids = [row[0] for row in result]
        print(f"   Found developers: {dev_ids}")
        
        # 3. Check sample records using actual developer IDs
        print("\n3. Sample records with duration data...")
        if dev_ids:
            # Use the first few developer IDs found
            for dev_id in dev_ids[:3]:
                result = conn.execute(text("""
                    SELECT 
                        CAST(developer_id AS VARCHAR) as dev_id,
                        application_name,
                        duration,
                        timestamp,
                        activity_data
                    FROM activity_records
                    WHERE CAST(developer_id AS VARCHAR) = :dev_id
                    ORDER BY timestamp DESC
                    LIMIT 3
                """), {'dev_id': dev_id})
                
                records = result.fetchall()
                if records:
                    print(f"\n   Developer: {dev_id}")
                    for i, record in enumerate(records):
                        print(f"   - Record {i+1}:")
                        print(f"     App: {record[1]}")
                        print(f"     Duration: {record[2]} seconds")
                        print(f"     Timestamp: {record[3]}")
        
        # 4. Check today's data specifically
        print("\n4. Checking today's data...")
        today = date.today()
        result = conn.execute(text("""
            SELECT 
                CAST(developer_id AS VARCHAR) as dev_id,
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
                hours = total_s / 3600
                print(f"   {dev_id}: {count} records, {hours:.2f} hours, {avg_s:.0f}s average")
        else:
            print("   ❌ No data for today!")
            
            # Check the latest date with data
            print("\n5. Checking latest dates with data...")
            result = conn.execute(text("""
                SELECT 
                    DATE(timestamp) as activity_date,
                    COUNT(DISTINCT CAST(developer_id AS VARCHAR)) as developers,
                    COUNT(*) as records,
                    SUM(duration) / 3600 as total_hours
                FROM activity_records
                GROUP BY DATE(timestamp)
                ORDER BY activity_date DESC
                LIMIT 7
            """))
            
            dates = result.fetchall()
            if dates:
                print("   Recent activity dates:")
                for act_date, devs, records, hours in dates:
                    hours_val = hours if hours else 0
                    print(f"   {act_date}: {devs} developers, {records} records, {hours_val:.1f} hours")
                    
                print(f"\n   ⚠️ Latest data is from {dates[0][0]}")
                print("   The dashboard is looking for today's data by default.")
                print("   You need to select this date in the dashboard!")
        
        # 6. Solution
        print("\n6. SOLUTION:")
        if today_data:
            print("   ✓ Data exists for today with positive durations")
            print("   Check if the dashboard is properly querying the data")
        else:
            print("   ⚠️ No data for today - this is why the dashboard shows 0 hours!")
            print("   Options:")
            print("   1. Select a different date in the dashboard (use the date picker)")
            print("   2. Sync today's activity data")
            print("   3. Modify the dashboard to show the latest available date")

if __name__ == "__main__":
    debug_duration_issue()
