import psycopg2
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

print("=== Activity Records Analysis ===")

# 1. Get all unique developer_ids
print("\n1. Unique developer_ids in activity_records:")
cur.execute("""
    SELECT DISTINCT developer_id, COUNT(*) as record_count
    FROM activity_records 
    WHERE developer_id IS NOT NULL
    GROUP BY developer_id
    ORDER BY record_count DESC
""")

developers = cur.fetchall()
for dev_id, count in developers:
    print(f"   {dev_id}: {count} records")

# 2. Get all unique application names
print("\n2. Top 20 Application Names:")
cur.execute("""
    SELECT application_name, COUNT(*) as count
    FROM activity_records 
    WHERE application_name IS NOT NULL
    GROUP BY application_name
    ORDER BY count DESC
    LIMIT 20
""")

apps = cur.fetchall()
for app, count in apps:
    print(f"   {app}: {count} records")

# 3. Check categories
print("\n3. Current Categories Distribution:")
cur.execute("""
    SELECT category, COUNT(*) as count
    FROM activity_records 
    GROUP BY category
    ORDER BY count DESC
""")

categories = cur.fetchall()
for cat, count in categories:
    print(f"   {cat or 'NULL'}: {count} records")

# 4. Get sample records for a developer
if developers:
    sample_dev_id = developers[0][0]
    print(f"\n4. Sample records for developer '{sample_dev_id}':")
    
    # Today's data
    today = datetime.now().date()
    cur.execute("""
        SELECT 
            id,
            application_name,
            window_title,
            category,
            duration,
            timestamp
        FROM activity_records 
        WHERE developer_id = %s
          AND DATE(timestamp) = %s
        ORDER BY timestamp DESC
        LIMIT 10
    """, (sample_dev_id, today))
    
    records = cur.fetchall()
    if records:
        print(f"   Today's activities ({today}):")
        for record in records:
            print(f"      ID: {record[0]}")
            print(f"      App: {record[1]}")
            print(f"      Title: {record[2][:50]}...")
            print(f"      Category: {record[3] or 'NULL'}")
            print(f"      Duration: {record[4]} seconds")
            print(f"      Time: {record[5]}")
            print("      ---")
    else:
        print(f"   No activities found for today. Checking last 7 days...")
        
        # Last 7 days
        week_ago = today - timedelta(days=7)
        cur.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as activity_count,
                SUM(duration) as total_duration
            FROM activity_records 
            WHERE developer_id = %s
              AND DATE(timestamp) >= %s
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (sample_dev_id, week_ago))
        
        daily_stats = cur.fetchall()
        for date, count, duration in daily_stats:
            hours = duration / 3600 if duration else 0
            print(f"      {date}: {count} activities, {hours:.2f} hours")

# 5. Check for uncategorized records
print("\n5. Uncategorized Records:")
cur.execute("""
    SELECT COUNT(*) 
    FROM activity_records 
    WHERE category IS NULL OR category = ''
""")
uncategorized_count = cur.fetchone()[0]
print(f"   Total uncategorized: {uncategorized_count}")

if uncategorized_count > 0:
    print("   Sample uncategorized apps:")
    cur.execute("""
        SELECT DISTINCT application_name, COUNT(*) as count
        FROM activity_records 
        WHERE category IS NULL OR category = ''
        AND application_name IS NOT NULL
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 10
    """)
    
    for app, count in cur.fetchall():
        print(f"      {app}: {count} records")

cur.close()
conn.close()
