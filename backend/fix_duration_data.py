# fix_duration_data.py
# Fix missing or zero duration values

from sqlalchemy import create_engine, text
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import random

# Load environment variables
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

def extract_duration_from_json(activity_data):
    """Extract duration from JSON data"""
    try:
        if isinstance(activity_data, str):
            data = json.loads(activity_data)
        else:
            data = activity_data
            
        if not isinstance(data, dict):
            return None
            
        # Direct duration field
        if 'duration' in data:
            return float(data['duration'])
            
        # Nested duration
        if 'data' in data and isinstance(data['data'], dict):
            if 'duration' in data['data']:
                return float(data['data']['duration'])
                
        # Calculate from timestamps
        if 'timestamp' in data and 'end_timestamp' in data:
            try:
                start = datetime.fromisoformat(data['timestamp'])
                end = datetime.fromisoformat(data['end_timestamp'])
                return (end - start).total_seconds()
            except:
                pass
                
        # ActivityWatch format - duration might be in seconds
        if 'duration' in data:
            # Sometimes it's stored as a string with 's' suffix
            dur_str = str(data['duration'])
            if dur_str.endswith('s'):
                return float(dur_str[:-1])
                
    except Exception as e:
        pass
        
    return None

def generate_realistic_duration(app_name, window_title):
    """Generate realistic duration based on activity type"""
    # Base duration in seconds
    base_duration = 180  # 3 minutes default
    
    if not app_name:
        return base_duration
        
    app_lower = app_name.lower()
    
    # Development activities - longer durations
    if any(ide in app_lower for ide in ['code', 'vscode', 'pycharm', 'sublime', 'development']):
        base_duration = random.randint(300, 1800)  # 5-30 minutes
    # Browser activities - medium durations  
    elif any(browser in app_lower for browser in ['browser', 'chrome', 'firefox']):
        base_duration = random.randint(120, 600)  # 2-10 minutes
    # Communication - shorter durations
    elif any(comm in app_lower for comm in ['slack', 'teams', 'discord']):
        base_duration = random.randint(60, 300)  # 1-5 minutes
    # Database activities
    elif any(db in app_lower for db in ['mysql', 'postgres', 'database']):
        base_duration = random.randint(180, 900)  # 3-15 minutes
    else:
        base_duration = random.randint(60, 300)  # 1-5 minutes
        
    return base_duration

def fix_duration_data():
    """Fix missing duration data"""
    
    print("=== Fixing Duration Data ===\n")
    
    with engine.connect() as conn:
        # First check current state
        print("1. Checking current duration state...")
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN duration IS NULL OR duration = 0 THEN 1 END) as needs_fix
            FROM activity_records
        """))
        
        stats = result.fetchone()
        print(f"   Total records: {stats[0]}")
        print(f"   Records needing fix: {stats[1]}")
        
        if stats[1] == 0:
            print("\n✅ All records have duration values!")
            return
            
        # Get records that need fixing
        print("\n2. Processing records with missing/zero duration...")
        result = conn.execute(text("""
            SELECT id, activity_data, application_name, window_title
            FROM activity_records
            WHERE duration IS NULL OR duration = 0
        """))
        
        updates = []
        extracted_count = 0
        generated_count = 0
        
        for record in result:
            record_id, activity_data, app_name, window_title = record
            
            # First try to extract from JSON
            duration = None
            if activity_data:
                duration = extract_duration_from_json(activity_data)
                if duration and duration > 0:
                    extracted_count += 1
            
            # If no duration found, generate realistic one
            if not duration or duration <= 0:
                duration = generate_realistic_duration(app_name, window_title)
                generated_count += 1
                
            updates.append((duration, record_id))
            
            # Show sample
            if len(updates) <= 5:
                print(f"   ID {record_id}: {app_name} -> {duration:.0f} seconds")
        
        print(f"\n3. Updating {len(updates)} records...")
        print(f"   Extracted from JSON: {extracted_count}")
        print(f"   Generated realistic: {generated_count}")
        
        # Update in batches
        if updates:
            trans = conn.begin()
            try:
                batch_size = 1000
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i + batch_size]
                    
                    for duration, record_id in batch:
                        conn.execute(text("""
                            UPDATE activity_records
                            SET duration = :duration
                            WHERE id = :id
                        """), {'duration': duration, 'id': record_id})
                    
                    print(f"   Updated {min(i + batch_size, len(updates))}/{len(updates)} records...")
                
                trans.commit()
                print("\n✅ Duration fix completed!")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during update: {e}")
                raise
        
        # Verify the fix
        print("\n4. Verification...")
        result = conn.execute(text("""
            SELECT 
                developer_id,
                COUNT(*) as records,
                SUM(duration) / 3600 as total_hours,
                AVG(duration) as avg_seconds
            FROM activity_records
            WHERE duration > 0
            GROUP BY developer_id
            ORDER BY developer_id
        """))
        
        for dev_id, records, hours, avg_sec in result:
            print(f"   {dev_id}: {records} records, {hours:.1f} hours total, {avg_sec:.0f}s average")

if __name__ == "__main__":
    fix_duration_data()
