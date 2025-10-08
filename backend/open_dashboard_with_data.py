# open_dashboard_with_data.py
# Opens the dashboard with the latest date that has data

from sqlalchemy import create_engine, text
import os
import webbrowser
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

print("=== Opening Dashboard with Correct Date ===\n")

with engine.connect() as conn:
    # Get the latest date with data
    result = conn.execute(text("""
        SELECT MAX(DATE(timestamp)) as latest_date
        FROM activity_records
        WHERE duration > 0
    """))
    
    row = result.fetchone()
    if row and row[0]:
        latest_date = row[0]
        print(f"Latest date with data: {latest_date}")
        
        # Build dashboard URL with date parameter
        dashboard_url = f"http://localhost:5001/?date={latest_date}"
        
        print(f"\nOpening dashboard with date: {latest_date}")
        print(f"URL: {dashboard_url}")
        
        # Open in browser
        webbrowser.open(dashboard_url)
        
        print("\n✅ Dashboard should open in your browser with the correct date!")
        print("\nIf it doesn't work automatically:")
        print("1. Go to http://localhost:5001")
        print("2. Click the date picker (top-right)")
        print(f"3. Select: {latest_date}")
    else:
        print("❌ No data found in database!")
