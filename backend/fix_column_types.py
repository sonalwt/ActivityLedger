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

try:
    # Check current types
    print("Checking current column types...")
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'activity_records' AND column_name = 'developer_id'
    """)
    result = cur.fetchone()
    
    if result and result[1] != 'character varying':
        print(f"Found issue: activity_records.developer_id is {result[1]}, should be VARCHAR")
        
        # Fix it
        print("\nConverting developer_id to VARCHAR...")
        cur.execute("""
            ALTER TABLE activity_records 
            ALTER COLUMN developer_id TYPE VARCHAR USING developer_id::VARCHAR
        """)
        conn.commit()
        print("✅ Fixed activity_records.developer_id type")
    else:
        print("✅ activity_records.developer_id is already VARCHAR")
    
    # Check developers table too
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'developers' AND column_name = 'developer_id'
    """)
    result = cur.fetchone()
    
    if result and result[1] != 'character varying':
        print(f"\nFound issue: developers.developer_id is {result[1]}, should be VARCHAR")
        cur.execute("""
            ALTER TABLE developers 
            ALTER COLUMN developer_id TYPE VARCHAR USING developer_id::VARCHAR
        """)
        conn.commit()
        print("✅ Fixed developers.developer_id type")
    else:
        print("✅ developers.developer_id is already VARCHAR")
        
    print("\n✅ All developer_id columns are now VARCHAR type!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
