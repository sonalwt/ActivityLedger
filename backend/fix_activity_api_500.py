# fix_activity_api_500.py
# Common fixes for 500 errors in activity data API

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

print("=== Fixing Common Causes of API 500 Errors ===\n")

with engine.connect() as conn:
    # 1. Fix case sensitivity issues
    print("1. Checking for case sensitivity issues...")
    result = conn.execute(text("""
        SELECT 
            CAST(developer_id AS VARCHAR) as original_id,
            LOWER(CAST(developer_id AS VARCHAR)) as lower_id,
            COUNT(*) as record_count
        FROM activity_records
        WHERE developer_id IS NOT NULL
        GROUP BY developer_id
        ORDER BY COUNT(*) DESC
    """))
    
    developers = result.fetchall()
    print("   Developer IDs in database:")
    for orig, lower, count in developers[:10]:
        print(f"   - '{orig}' (lowercase: '{lower}') - {count} records")
    
    # 2. Check for NULL values that might cause issues
    print("\n2. Checking for NULL values in critical columns...")
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN developer_id IS NULL THEN 1 END) as null_dev_id,
            COUNT(CASE WHEN timestamp IS NULL THEN 1 END) as null_timestamp,
            COUNT(CASE WHEN duration IS NULL THEN 1 END) as null_duration,
            COUNT(CASE WHEN application_name IS NULL THEN 1 END) as null_app_name,
            COUNT(CASE WHEN category IS NULL THEN 1 END) as null_category
        FROM activity_records
    """))
    
    stats = result.fetchone()
    print(f"   Total records: {stats[0]}")
    print(f"   NULL developer_id: {stats[1]}")
    print(f"   NULL timestamp: {stats[2]}")
    print(f"   NULL duration: {stats[3]}")
    print(f"   NULL application_name: {stats[4]}")
    print(f"   NULL category: {stats[5]}")
    
    # 3. Fix missing categories
    if stats[5] > 0:
        print("\n3. Fixing missing categories...")
        trans = conn.begin()
        try:
            # Set default category for NULL values
            result = conn.execute(text("""
                UPDATE activity_records
                SET category = 'other'
                WHERE category IS NULL
            """))
            
            updated = result.rowcount
            trans.commit()
            print(f"   ✓ Updated {updated} records with default category")
        except Exception as e:
            trans.rollback()
            print(f"   ❌ Error updating categories: {str(e)}")
    
    # 4. Create case-insensitive indexes
    print("\n4. Creating indexes for better performance...")
    try:
        # Check if indexes exist
        result = conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'activity_records'
        """))
        
        existing_indexes = [row[0] for row in result]
        print(f"   Existing indexes: {', '.join(existing_indexes)}")
        
        # Create lower case index if not exists
        if 'idx_developer_id_lower' not in existing_indexes:
            conn.execute(text("""
                CREATE INDEX idx_developer_id_lower 
                ON activity_records (LOWER(CAST(developer_id AS VARCHAR)))
            """))
            conn.commit()
            print("   ✓ Created lowercase developer_id index")
            
    except Exception as e:
        print(f"   ⚠️ Index creation: {str(e)}")
    
    # 5. Test problematic query
    print("\n5. Testing activity query with fixes...")
    
    # Test for RiddhiDhakhara
    test_dev_id = 'riddhidhakhara'
    start_date = '2025-09-30'
    end_date = '2025-10-08'
    
    try:
        # Case-insensitive query
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as count,
                MIN(DATE(timestamp)) as min_date,
                MAX(DATE(timestamp)) as max_date
            FROM activity_records
            WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
        """), {'dev_id': test_dev_id})
        
        row = result.fetchone()
        if row[0] > 0:
            print(f"   ✓ Found {row[0]} records for '{test_dev_id}'")
            print(f"   Date range: {row[1]} to {row[2]}")
            
            # Check specific date range
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM activity_records
                WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
                AND DATE(timestamp) BETWEEN :start_date AND :end_date
            """), {
                'dev_id': test_dev_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            count = result.fetchone()[0]
            if count > 0:
                print(f"   ✓ Found {count} records in date range {start_date} to {end_date}")
            else:
                print(f"   ⚠️ No records in date range {start_date} to {end_date}")
        else:
            print(f"   ❌ No records found for '{test_dev_id}'")
            
    except Exception as e:
        print(f"   ❌ Query error: {str(e)}")

print("\n6. RECOMMENDATIONS:")
print("   1. Update your API to use case-insensitive queries")
print("   2. Add proper error handling in the API endpoints")
print("   3. Set default values for NULL columns")
print("   4. Add appropriate indexes for performance")
print("   5. Check the API logs for the specific error message")

print("\n7. Quick Fix for your API:")
print("""
   In your API endpoint, change:
   WHERE developer_id = :dev_id
   
   To:
   WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(:dev_id)
""")
