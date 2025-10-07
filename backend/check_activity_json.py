from sqlalchemy import create_engine, text
import json
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

print("=== Checking Activity Data JSON Field ===")

with engine.connect() as conn:
    # Get sample records with activity_data
    print("\n1. Sample activity_data content:")
    result = conn.execute(text("""
        SELECT 
            id,
            developer_id,
            activity_data,
            duration,
            timestamp
        FROM activity_records 
        WHERE activity_data IS NOT NULL
        AND activity_data != '{}'
        LIMIT 5
    """))
    
    records = result.fetchall()
    if records:
        for record in records:
            print(f"\n   Record ID: {record[0]}")
            print(f"   Developer: {record[1]}")
            print(f"   Timestamp: {record[4]}")
            print(f"   Duration: {record[2]} seconds")
            
            # Parse and display activity_data
            try:
                data = json.loads(record[2]) if isinstance(record[2], str) else record[2]
                print(f"   Activity Data:")
                print(f"      {json.dumps(data, indent=6)[:500]}...")
                
                # Check if app/title info is in the JSON
                if 'app' in data:
                    print(f"   ✓ Found 'app' field: {data['app']}")
                if 'title' in data:
                    print(f"   ✓ Found 'title' field: {data['title']}")
                if 'data' in data and isinstance(data['data'], dict):
                    if 'app' in data['data']:
                        print(f"   ✓ Found 'data.app' field: {data['data']['app']}")
                    if 'title' in data['data']:
                        print(f"   ✓ Found 'data.title' field: {data['data']['title']}")
                        
            except Exception as e:
                print(f"   Error parsing JSON: {e}")
    else:
        print("   No records with activity_data found!")
    
    # Check if activity_data is empty for all records
    print("\n2. Activity data statistics:")
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN activity_data IS NULL THEN 1 END) as null_data,
            COUNT(CASE WHEN activity_data = '{}' THEN 1 END) as empty_data,
            COUNT(CASE WHEN activity_data IS NOT NULL AND activity_data != '{}' THEN 1 END) as has_data
        FROM activity_records
    """))
    
    stats = result.fetchone()
    print(f"   Total records: {stats[0]}")
    print(f"   NULL activity_data: {stats[1]}")
    print(f"   Empty JSON ('{{}}'): {stats[2]}")
    print(f"   Has data: {stats[3]}")

print("\n3. Checking data structure in activity_data...")
# Get a few records to analyze structure
result = conn.execute(text("""
    SELECT activity_data 
    FROM activity_records 
    WHERE activity_data IS NOT NULL 
    AND activity_data != '{}'
    AND activity_data != ''
    LIMIT 10
"""))

unique_keys = set()
for (data_str,) in result:
    try:
        data = json.loads(data_str) if isinstance(data_str, str) else data_str
        if isinstance(data, dict):
            unique_keys.update(data.keys())
    except:
        pass

if unique_keys:
    print(f"   Found keys in activity_data: {unique_keys}")
else:
    print("   No valid JSON data found in activity_data")
