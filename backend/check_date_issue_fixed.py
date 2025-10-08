# check_date_issue_fixed.py
# Check if the issue is with date filtering - Fixed for VARCHAR developer_id

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
        # 1. Get actual developer IDs
        print("1. Getting actual developer IDs...")
        result = conn.execute(text("""
            SELECT DISTINCT CAST(developer_id AS VARCHAR) as dev_id
            FROM activity_records
            WHERE developer_id IS NOT NULL
            ORDER BY 1
        """))
        
        dev_ids = [row[0] for row in result]
        print(f"   Found developers: {dev_ids}")
        
        # 2. Check date range of data
        print("\n2. Date range of activity data...")
        result = conn.execute(text("""
            SELECT 
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(DISTINCT DATE(timestamp)) as unique_days
            FROM activity_records
        """))
        
        row = result.fetchone()
        if row[0]:
            print(f"   Earliest: {row[0]}")
            print(f"   Latest: {row[1]}")
            print(f"   Unique days: {row[2]}")
            
            # Check if latest date is today
            latest_date = row[1].date() if row[1] else None
            today = date.today()
            if latest_date and latest_date < today:
                days_ago = (today - latest_date).days
                print(f"\n   ⚠️ IMPORTANT: Latest data is from {days_ago} days ago!")
                print(f"   The dashboard defaults to today ({today}) but your data ends on {latest_date}")
        
        # 3. Check data by date
        print("\n3. Activity count by recent dates...")
        result = conn.execute(text("""
            SELECT 
                DATE(timestamp) as activity_date,
                COUNT(*) as record_count,
                COUNT(DISTINCT CAST(developer_id AS VARCHAR)) as developers,
                SUM(duration) / 3600 as total_hours
            FROM activity_records
            GROUP BY DATE(timestamp)
            ORDER BY activity_date DESC
            LIMIT 10
        """))
        
        dates = result.fetchall()
        if dates:
            print("   Date        | Records | Developers | Hours")
            print("   " + "-" * 45)
            for act_date, count, devs, hours in dates:
                hours_val = hours if hours else 0
                print(f"   {act_date} | {count:7} | {devs:10} | {hours_val:5.1f}")
                
            # Highlight the issue
            latest_data_date = dates[0][0]
            today = date.today()
            if latest_data_date < today:
                print(f"\n   ⚠️ PROBLEM FOUND!")
                print(f"   - Dashboard is looking for: {today} (today)")
                print(f"   - Your latest data is from: {latest_data_date}")
                print(f"   - Gap: {(today - latest_data_date).days} days")
        else:
            print("   No data found!")
        
        # 4. Check specific developers for today vs latest date
        today = date.today()
        latest_date = dates[0][0] if dates else today
        
        print(f"\n4. Comparing today vs latest date with data...")
        print(f"   Today: {today}")
        print(f"   Latest: {latest_date}")
        
        if dev_ids:
            # Check first developer
            dev_id = dev_ids[0]
            
            # Today's data
            result = conn.execute(text("""
                SELECT COUNT(*) as count, SUM(duration) / 3600 as hours
                FROM activity_records
                WHERE CAST(developer_id AS VARCHAR) = :dev_id
                AND DATE(timestamp) = :check_date
            """), {'dev_id': dev_id, 'check_date': today})
            
            today_row = result.fetchone()
            
            # Latest date's data
            result = conn.execute(text("""
                SELECT COUNT(*) as count, SUM(duration) / 3600 as hours
                FROM activity_records
                WHERE CAST(developer_id AS VARCHAR) = :dev_id
                AND DATE(timestamp) = :check_date
            """), {'dev_id': dev_id, 'check_date': latest_date})
            
            latest_row = result.fetchone()
            
            print(f"\n   Developer: {dev_id}")
            print(f"   - Today ({today}): {today_row[0]} records, {today_row[1]:.1f if today_row[1] else 0} hours")
            print(f"   - Latest ({latest_date}): {latest_row[0]} records, {latest_row[1]:.1f if latest_row[1] else 0} hours")
        
        # 5. Solution
        print("\n5. SOLUTION:")
        if dates and dates[0][0] < today:
            print("   ✅ YOUR ISSUE: Dashboard is showing today's date but your data is older!")
            print("\n   IMMEDIATE FIX:")
            print("   1. In the dashboard, look for a date picker/calendar widget")
            print(f"   2. Select the date: {latest_date}")
            print("   3. You should immediately see hours and productivity data")
            print("\n   PERMANENT FIXES:")
            print("   - Update your data sync to include today's activities")
            print("   - Modify the dashboard to default to the latest available date")
            print("   - Add a 'Show Latest Data' button to the dashboard")
        elif dates and dates[0][0] == today:
            print("   ✓ Data exists for today")
            print("   If still showing 0 hours, check:")
            print("   - Application name extraction")
            print("   - Dashboard query logic")
        else:
            print("   ❌ No data found in the database")

if __name__ == "__main__":
    check_date_issues()
