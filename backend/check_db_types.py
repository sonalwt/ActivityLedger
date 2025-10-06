import psycopg2
from config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())

# Parse database URL
if DATABASE_URL.startswith("postgresql://"):
    # Parse the connection string
    parts = DATABASE_URL.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    database = host_db[1]
else:
    print("Invalid database URL")
    exit(1)

# Connect to database
conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password
)

cur = conn.cursor()

# Check developers table schema
print("=== DEVELOPERS TABLE SCHEMA ===")
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'developers'
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2] if row[2] else 'N/A'})")

print("\n=== ACTIVITY_RECORDS TABLE SCHEMA ===")
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'activity_records'
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2] if row[2] else 'N/A'})")

# Check if there are any integer developer_ids stored as strings
print("\n=== CHECKING DEVELOPER_ID VALUES ===")
cur.execute("""
    SELECT DISTINCT developer_id, pg_typeof(developer_id) 
    FROM activity_records 
    WHERE developer_id IS NOT NULL 
    LIMIT 10
""")
print("Sample developer_id values from activity_records:")
for row in cur.fetchall():
    print(f"  Value: '{row[0]}', Type: {row[1]}")

cur.execute("""
    SELECT DISTINCT developer_id, pg_typeof(developer_id) 
    FROM developers 
    WHERE developer_id IS NOT NULL 
    LIMIT 10
""")
print("\nSample developer_id values from developers:")
for row in cur.fetchall():
    print(f"  Value: '{row[0]}', Type: {row[1]}")

# Check if there are any numeric-looking developer_ids
print("\n=== CHECKING FOR NUMERIC DEVELOPER_IDS ===")
cur.execute("""
    SELECT COUNT(*) 
    FROM activity_records 
    WHERE developer_id IS NOT NULL 
    AND developer_id ~ '^[0-9]+$'
""")
numeric_count = cur.fetchone()[0]
print(f"Activity records with numeric developer_ids: {numeric_count}")

cur.close()
conn.close()
