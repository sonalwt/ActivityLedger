# find_data_dates.py
# Simple script to find which dates have data

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import date

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

print("=== Finding Dates with Activity Data ===\n")

with engine.connect() as conn:
    # Get all dates with data
    result = conn.execute(text("""
        SELECT 
            DATE(timestamp) as activity_date,
            COUNT(DISTINCT developer_id) as developers,
            COUNT(*) as total_records,
            SUM(duration) / 3600 as total_hours
        FROM activity_records
        WHERE duration > 0
        GROUP BY DATE(timestamp)
        ORDER BY activity_date DESC
    """))
    
    dates = result.fetchall()
    if dates:
        print("Dates with activity data:")
        print("=" * 50)
        print("Date       | Developers | Records | Total Hours")
        print("-" * 50)
        
        for act_date, devs, records, hours in dates:
            hours_val = hours if hours else 0
            print(f"{act_date} | {devs:10} | {records:7} | {hours_val:10.1f}")
        
        # Highlight the latest and today
        latest_date = dates[0][0]
        today = date.today()
        
        print("\n" + "=" * 50)
        print(f"📅 Today's date: {today}")
        print(f"📊 Latest data: {latest_date}")
        
        if latest_date < today:
            days_diff = (today - latest_date).days
            print(f"\n⚠️ Your data is {days_diff} days old!")
            print("\n🔧 TO FIX THE DASHBOARD:")
            print(f"1. Click the date picker in the top-right corner")
            print(f"2. Select: {latest_date}")
            print(f"3. Your hours will appear immediately!")
        else:
            print("\n✅ You have data for today!")
    else:
        print("❌ No activity data found in the database!")
