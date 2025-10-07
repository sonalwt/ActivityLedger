from sqlalchemy import create_engine, text
import json
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
engine = create_engine(DATABASE_URL)

def extract_app_info(activity_data):
    """Extract application name and window title from activity_data JSON"""
    try:
        if isinstance(activity_data, str):
            data = json.loads(activity_data)
        else:
            data = activity_data
            
        app_name = None
        window_title = None
        
        # Common structures in ActivityWatch data
        if isinstance(data, dict):
            # Check direct fields
            app_name = data.get('app') or data.get('application') or data.get('application_name')
            window_title = data.get('title') or data.get('window_title')
            
            # Check nested data field
            if 'data' in data and isinstance(data['data'], dict):
                if not app_name:
                    app_name = data['data'].get('app') or data['data'].get('application')
                if not window_title:
                    window_title = data['data'].get('title') or data['data'].get('window_title')
            
            # Check other possible fields
            if not app_name and 'program' in data:
                app_name = data['program']
            if not app_name and 'process' in data:
                app_name = data['process']
                
        return app_name, window_title
    except:
        return None, None

print("=== Extracting and Updating Application Data ===")

with engine.connect() as conn:
    # First, let's see what we're working with
    print("\n1. Analyzing activity_data structure...")
    
    result = conn.execute(text("""
        SELECT id, activity_data
        FROM activity_records
        WHERE activity_data IS NOT NULL 
        AND activity_data != '{}'
        AND (application_name IS NULL OR application_name = '')
        LIMIT 10
    """))
    
    sample_data = []
    for record_id, data_str in result:
        app_name, window_title = extract_app_info(data_str)
        if app_name or window_title:
            sample_data.append((record_id, app_name, window_title))
            print(f"   ID {record_id}: app='{app_name}', title='{window_title[:50] if window_title else 'None'}'")
    
    if not sample_data:
        print("   Could not extract app info from sample records.")
        print("   Let me check the actual structure...")
        
        # Get one record to inspect
        result = conn.execute(text("""
            SELECT activity_data 
            FROM activity_records 
            WHERE activity_data IS NOT NULL 
            AND activity_data != '{}'
            LIMIT 1
        """))
        
        record = result.fetchone()
        if record:
            try:
                data = json.loads(record[0]) if isinstance(record[0], str) else record[0]
                print(f"\n   Sample activity_data structure:")
                print(json.dumps(data, indent=4))
            except Exception as e:
                print(f"   Error parsing: {e}")
    
    # Now update all records
    print("\n2. Updating records with extracted app data...")
    
    # Get all records that need updating
    result = conn.execute(text("""
        SELECT id, activity_data
        FROM activity_records
        WHERE activity_data IS NOT NULL 
        AND activity_data != '{}'
        AND (application_name IS NULL OR application_name = '')
    """))
    
    updates = []
    for record_id, data_str in result:
        app_name, window_title = extract_app_info(data_str)
        if app_name or window_title:
            updates.append((record_id, app_name, window_title))
    
    print(f"   Found {len(updates)} records to update")
    
    # Update in batches
    if updates:
        trans = conn.begin()
        try:
            updated_count = 0
            for record_id, app_name, window_title in updates:
                conn.execute(text("""
                    UPDATE activity_records
                    SET application_name = :app_name,
                        window_title = :window_title
                    WHERE id = :id
                """), {
                    "id": record_id,
                    "app_name": app_name,
                    "window_title": window_title
                })
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"   Updated {updated_count} records...")
            
            trans.commit()
            print(f"\n✅ Successfully updated {updated_count} records")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Error during update: {e}")
            raise
    
    # Show results
    print("\n3. New application distribution:")
    result = conn.execute(text("""
        SELECT application_name, COUNT(*) as count
        FROM activity_records
        WHERE application_name IS NOT NULL
        GROUP BY application_name
        ORDER BY count DESC
        LIMIT 20
    """))
    
    apps = result.fetchall()
    if apps:
        for app, count in apps:
            print(f"   {app}: {count} records")
    else:
        print("   No applications found after update")
        
print("\n4. Next step: Run the categorization script to categorize these applications")
