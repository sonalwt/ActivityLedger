from sqlalchemy import create_engine, text
from config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

try:
    with engine.connect() as conn:
        print("✅ Connected to database")
        
        # Check data types
        print("\n=== Checking column data types ===")
        
        # Check developers.developer_id type
        result = conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'developers' AND column_name = 'developer_id'
        """)).fetchone()
        
        if result:
            print(f"developers.developer_id: {result[1]} (max length: {result[2]})")
        
        # Check activity_records.developer_id type
        result = conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'activity_records' AND column_name = 'developer_id'
        """)).fetchone()
        
        if result:
            print(f"activity_records.developer_id: {result[1]} (max length: {result[2]})")
        
        # Check sample data
        print("\n=== Sample data from developers ===")
        result = conn.execute(text("""
            SELECT id, developer_id, name, pg_typeof(developer_id) as type
            FROM developers
            LIMIT 5
        """))
        
        for row in result:
            print(f"ID: {row[0]}, developer_id: '{row[1]}', name: {row[2]}, type: {row[3]}")
        
        print("\n=== Sample data from activity_records ===")
        result = conn.execute(text("""
            SELECT id, developer_id, pg_typeof(developer_id) as type
            FROM activity_records
            WHERE developer_id IS NOT NULL
            LIMIT 5
        """))
        
        for row in result:
            print(f"ID: {row[0]}, developer_id: '{row[1]}', type: {row[2]}")
            
        # Check if there are any numeric developer_ids
        print("\n=== Checking for problematic data ===")
        
        # Check for numeric-looking developer_ids in activity_records
        result = conn.execute(text("""
            SELECT COUNT(*), developer_id
            FROM activity_records
            WHERE developer_id ~ '^[0-9]+$'
            GROUP BY developer_id
            LIMIT 5
        """))
        
        numeric_ids = list(result)
        if numeric_ids:
            print(f"Found {len(numeric_ids)} numeric developer_ids in activity_records:")
            for count, dev_id in numeric_ids:
                print(f"  developer_id '{dev_id}' appears {count} times")
        else:
            print("No numeric developer_ids found in activity_records")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
