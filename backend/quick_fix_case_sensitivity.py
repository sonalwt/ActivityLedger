# quick_fix_case_sensitivity.py
# Quick fix for case sensitivity causing 500 errors

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

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

print("=== Quick Fix for Case Sensitivity ===\n")

with engine.connect() as conn:
    # Find all variations of RiddhiDhakhara
    print("1. Finding all case variations of developer IDs...")
    result = conn.execute(text("""
        SELECT DISTINCT 
            CAST(developer_id AS VARCHAR) as original_id,
            LOWER(CAST(developer_id AS VARCHAR)) as lower_id,
            COUNT(*) as records
        FROM activity_records
        WHERE LOWER(CAST(developer_id AS VARCHAR)) IN ('riddhidhakhara', 'ankita gholap', 'ankita_gholap')
        GROUP BY developer_id
        ORDER BY lower_id, original_id
    """))
    
    variations = result.fetchall()
    if variations:
        print("   Found these variations:")
        for orig, lower, count in variations:
            print(f"   - '{orig}' ({count} records)")
        
        # Option 1: Standardize to lowercase
        print("\n2. Option 1: Standardize all developer IDs to lowercase...")
        print("   This would update:")
        for orig, lower, count in variations:
            if orig != lower:
                print(f"   - '{orig}' -> '{lower}'")
        
        print("\n   Run this SQL to fix:")
        print("   UPDATE activity_records")
        print("   SET developer_id = LOWER(developer_id)")
        print("   WHERE developer_id != LOWER(developer_id);")
        
        # Option 2: Update API queries
        print("\n3. Option 2: Update your API to handle case-insensitive queries")
        print("   Change your API queries from:")
        print("   WHERE developer_id = :dev_id")
        print("\n   To:")
        print("   WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)")
        
    else:
        print("   No records found for these developers!")

print("\n4. RECOMMENDED FIX FOR YOUR API:")
print("""
In your activity data API endpoint, update the query to be case-insensitive:

Example for Python/SQLAlchemy:
    query = '''
        SELECT * FROM activity_records
        WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
        AND DATE(timestamp) BETWEEN :start_date AND :end_date
    '''
    
Example for raw SQL:
    WHERE LOWER(developer_id::varchar) = LOWER($1)
    
This will match 'riddhidhakhara' with 'RiddhiDhakhara' or any other case variation.
""")
