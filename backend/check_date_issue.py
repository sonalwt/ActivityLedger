# check_date_issue.py
# Check if the issue is with date filtering

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import datetime, date, timedelta

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

def check_date_issues():
    """Check if the issue is with date filtering"""
    
    print("=== Checking Date-Related Issues ===\n")
    
    with engine.connect() as conn:
        # 1. Check date range of data
        print("1. Date range of activity data...")
        result = conn.execute(text("""
            SELECT 
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(DISTINCT DATE(timestamp)) as unique_days
            FROM activity_records
            WHERE developer_id IN ('ankita gholap', 'RiddhiDhakhara', 'ankita_gholap')
        """))
        
        row = result.fetchone()
        print(f"   Earliest: {row[0]}")
        print(f"   Latest: {row[1]}")
        print(f"   Unique days: {row[2]}")
        
        # 2. Check data by date
        print("\n2. Activity count by recent dates...")
        result = conn.execute(text("""
            SELECT 
                DATE(timestamp) as activity_date,
                COUNT(*) as record_count,
                COUNT(DISTINCT developer_id) as developers,
                SUM(duration) / 3600 as total_hours
            FROM activity_records
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(timestamp)
            ORDER BY activity_date DESC
        """))
        
        dates = result.fetchall()
        if dates:
            for act_date, count, devs, hours in dates:
                hours_val = hours if hours else 0
                print(f"   {act_date}: {count} records, {devs} developers, {hours_val:.1f} hours")
        else:
            print("   No data in the last 7 days!")
        
        # 3. Check specific developers for today
        today = date.today()
        print(f"\n3. Checking data for today ({today})...")
        
        for dev_id in ['ankita gholap', 'RiddhiDhakhara', 'ankita_gholap']:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as count,
                    SUM(duration) as total_duration,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity
                FROM activity_records
                WHERE developer_id = :dev_id
                AND DATE(timestamp) = :today
            """), {'dev_id': dev_id, 'today': today})
            
            row = result.fetchone()
            if row[0] > 0:
                dur = row[1] if row[1] else 0
                print(f"   {dev_id}: {row[0]} records, {dur:.0f} seconds")
                print(f"     First: {row[2]}, Last: {row[3]}")
            else:
                print(f"   {dev_id}: No data for today")
        
        # 4. Check timestamp format
        print("\n4. Sample timestamp values...")
        result = conn.execute(text("""
            SELECT 
                id,
                timestamp,
                DATE(timestamp) as date_part,
                activity_data
            FROM activity_records
            WHERE developer_id IN ('ankita gholap', 'RiddhiDhakhara')
            ORDER BY timestamp DESC
            LIMIT 5
        """))
        
        for record in result:
            print(f"   ID {record[0]}: {record[1]} (Date: {record[2]})")
            
        # 5. Solution
        print("\n5. ANALYSIS:")
        if not dates or (dates and dates[0][0] != today):
            print("   ⚠️ No data for today - the dashboard shows today's data by default")
            print("   Solutions:")
            print("   1. Click on a different date in the dashboard")
            print("   2. Sync today's activity data")
            print("   3. Modify dashboard to show the latest available date")
        else:
            print("   ✓ Data exists for today")
            print("   Check if duration values are properly set")

if __name__ == "__main__":
    check_date_issues()
