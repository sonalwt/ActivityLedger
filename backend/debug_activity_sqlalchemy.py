from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from config import Config

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

print("=== Activity Records Analysis (SQLAlchemy) ===")

with engine.connect() as conn:
    # 1. Get all unique developer_ids
    print("\n1. Unique developer_ids in activity_records:")
    result = conn.execute(text("""
        SELECT DISTINCT developer_id, COUNT(*) as record_count
        FROM activity_records 
        WHERE developer_id IS NOT NULL
        GROUP BY developer_id
        ORDER BY record_count DESC
    """))
    
    developers = result.fetchall()
    for dev_id, count in developers:
        print(f"   {dev_id}: {count} records")

    # 2. Get all unique application names
    print("\n2. Top 20 Application Names:")
    result = conn.execute(text("""
        SELECT application_name, COUNT(*) as count
        FROM activity_records 
        WHERE application_name IS NOT NULL
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 20
    """))
    
    apps = result.fetchall()
    for app, count in apps:
        print(f"   {app}: {count} records")

    # 3. Check categories
    print("\n3. Current Categories Distribution:")
    result = conn.execute(text("""
        SELECT category, COUNT(*) as count
        FROM activity_records 
        GROUP BY category
        ORDER BY count DESC
    """))
    
    categories = result.fetchall()
    for cat, count in categories:
        print(f"   {cat or 'NULL'}: {count} records")

    # 4. Get sample records for a developer
    if developers:
        sample_dev_id = developers[0][0]
        print(f"\n4. Sample records for developer '{sample_dev_id}':")
        
        # Today's data
        today = datetime.now().date()
        result = conn.execute(text("""
            SELECT 
                id,
                application_name,
                window_title,
                category,
                duration,
                timestamp
            FROM activity_records 
            WHERE developer_id = :dev_id
              AND DATE(timestamp) = :today
            ORDER BY timestamp DESC
            LIMIT 10
        """), {"dev_id": sample_dev_id, "today": today})
        
        records = result.fetchall()
        if records:
            print(f"   Today's activities ({today}):")
            for record in records:
                print(f"      ID: {record[0]}")
                print(f"      App: {record[1]}")
                print(f"      Title: {record[2][:50] if record[2] else 'None'}...")
                print(f"      Category: {record[3] or 'NULL'}")
                print(f"      Duration: {record[4]} seconds")
                print(f"      Time: {record[5]}")
                print("      ---")
        else:
            print(f"   No activities found for today. Checking last 7 days...")
            
            # Last 7 days
            week_ago = today - timedelta(days=7)
            result = conn.execute(text("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as activity_count,
                    SUM(duration) as total_duration
                FROM activity_records 
                WHERE developer_id = :dev_id
                  AND DATE(timestamp) >= :week_ago
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """), {"dev_id": sample_dev_id, "week_ago": week_ago})
            
            daily_stats = result.fetchall()
            for date, count, duration in daily_stats:
                hours = duration / 3600 if duration else 0
                print(f"      {date}: {count} activities, {hours:.2f} hours")

    # 5. Check for uncategorized records
    print("\n5. Uncategorized Records:")
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM activity_records 
        WHERE category IS NULL OR category = ''
    """))
    uncategorized_count = result.fetchone()[0]
    print(f"   Total uncategorized: {uncategorized_count}")

    if uncategorized_count > 0:
        print("   Sample uncategorized apps:")
        result = conn.execute(text("""
            SELECT DISTINCT application_name, COUNT(*) as count
            FROM activity_records 
            WHERE category IS NULL OR category = ''
            AND application_name IS NOT NULL
            GROUP BY application_name
            ORDER BY count DESC
            LIMIT 10
        """))
        
        for app, count in result.fetchall():
            print(f"      {app}: {count} records")

print("\nDone!")
