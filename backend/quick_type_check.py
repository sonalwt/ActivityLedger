import psycopg2
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

print("=== Column Types ===")
cur.execute("""
    SELECT 
        'developers' as table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_name = 'developers' AND column_name = 'developer_id'
    UNION ALL
    SELECT 
        'activity_records' as table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_name = 'activity_records' AND column_name = 'developer_id'
""")

for row in cur.fetchall():
    print(f"{row[0]}.{row[1]}: {row[2]}")

print("\n=== Sample Data ===")
cur.execute("SELECT developer_id, pg_typeof(developer_id) FROM developers LIMIT 2")
print("Developers table:")
for row in cur.fetchall():
    print(f"  Value: '{row[0]}', Type: {row[1]}")

cur.execute("SELECT developer_id, pg_typeof(developer_id) FROM activity_records WHERE developer_id IS NOT NULL LIMIT 2")
print("\nActivity_records table:")
for row in cur.fetchall():
    print(f"  Value: '{row[0]}', Type: {row[1]}")

cur.close()
conn.close()
