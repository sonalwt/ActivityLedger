# quick_dashboard_test.py
# Quick test to see what's happening with a specific developer

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

print("=== Quick Dashboard Test ===\n")

with engine.connect() as conn:
    # Get the exact developer IDs and their data
    result = conn.execute(text("""
        SELECT 
            CAST(developer_id AS VARCHAR) as dev_id,
            DATE(timestamp) as activity_date,
            COUNT(*) as records,
            SUM(duration) / 3600 as hours,
            COUNT(DISTINCT application_name) as apps
        FROM activity_records
        WHERE duration > 0
        AND application_name IS NOT NULL
        GROUP BY developer_id, DATE(timestamp)
        ORDER BY activity_date DESC, dev_id
        LIMIT 20
    """))
    
    print("Developer Activity Summary:")
    print("Developer ID         | Date       | Records | Hours | Apps")
    print("-" * 60)
    
    data_found = False
    for row in result:
        dev_id, act_date, records, hours, apps = row
        # Handle None values
        dev_id_str = str(dev_id) if dev_id else "Unknown"
        hours_val = hours if hours else 0
        data_found = True
        print(f"{dev_id_str:<20} | {act_date} | {records:7} | {hours_val:5.1f} | {apps:4}")
    
    if not data_found:
        print("No data found!")
    else:
        print("\n⚠️ KEY INSIGHT:")
        print("The dashboard is showing '0h worked' because it's looking at TODAY's date")
        print("but your data is from the dates shown above.")
        print("\n✅ SOLUTION: Select one of the dates above in your dashboard's date picker!")
        
    # Also check today's data
    print("\n" + "=" * 60)
    print("Checking today's data specifically...")
    today = date.today()
    
    result = conn.execute(text("""
        SELECT 
            CAST(developer_id AS VARCHAR) as dev_id,
            COUNT(*) as records,
            SUM(duration) / 3600 as hours
        FROM activity_records
        WHERE DATE(timestamp) = :today
        AND duration > 0
        GROUP BY developer_id
    """), {'today': today})
    
    today_data = result.fetchall()
    if today_data:
        print(f"\nData for today ({today}):")
        for dev_id, records, hours in today_data:
            dev_id_str = str(dev_id) if dev_id else "Unknown"
            hours_val = hours if hours else 0
            print(f"  {dev_id_str}: {records} records, {hours_val:.1f} hours")
    else:
        print(f"\n❌ No data for today ({today})")
        print("This is why the dashboard shows 0 hours!")
