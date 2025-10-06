import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Parse connection string
conn_parts = DATABASE_URL.replace("postgresql://", "").split("@")
user_pass = conn_parts[0].split(":")
host_db = conn_parts[1].split("/")
host_port = host_db[0].split(":")

conn = psycopg2.connect(
    host=host_port[0],
    port=host_port[1] if len(host_port) > 1 else "5432",
    database=host_db[1],
    user=user_pass[0],
    password=user_pass[1]
)

cur = conn.cursor()

print("=== Checking activity_records structure ===")

# Get column info
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'activity_records'
    ORDER BY ordinal_position
""")

print("\nColumns in activity_records:")
for col in cur.fetchall():
    print(f"  {col[0]}: {col[1]}")

# Get sample data
print("\n=== Sample activity data ===")
cur.execute("""
    SELECT 
        id,
        developer_id,
        application_name,
        window_title,
        category,
        activity_data,
        duration,
        timestamp
    FROM activity_records 
    WHERE developer_id IS NOT NULL
    LIMIT 5
""")

for row in cur.fetchall():
    print(f"\nRecord ID: {row[0]}")
    print(f"  Developer: {row[1]}")
    print(f"  App: {row[2]}")
    print(f"  Title: {row[3]}")
    print(f"  Category: {row[4]}")
    print(f"  Duration: {row[6]}")
    
    # Parse activity_data JSON if exists
    if row[5]:
        try:
            data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            print(f"  Activity Data: {json.dumps(data, indent=4)[:200]}...")
        except:
            print(f"  Activity Data: {row[5]}")

cur.close()
conn.close()
