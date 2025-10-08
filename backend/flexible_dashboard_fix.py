# flexible_dashboard_fix.py
# This script can handle various JSON structures in activity_data

from sqlalchemy import create_engine, text, Column, String
import json
import os
from datetime import datetime
from dotenv import load_dotenv

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

def check_table_columns():
    """Check if the required columns exist in the activity_records table"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'activity_records'
            ORDER BY ordinal_position
        """))
        
        columns = [row[0] for row in result]
        print("Existing columns in activity_records table:")
        for col in columns:
            print(f"  - {col}")
        
        required_columns = ['application_name', 'window_title', 'category', 'project_name']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"\n⚠️ Missing columns: {missing_columns}")
            print("Creating missing columns...")
            
            for col in missing_columns:
                try:
                    if col in ['application_name', 'window_title', 'category', 'project_name', 'project_type']:
                        conn.execute(text(f"ALTER TABLE activity_records ADD COLUMN {col} VARCHAR(255)"))
                        print(f"  ✓ Added column: {col}")
                    elif col == 'url' or col == 'file_path':
                        conn.execute(text(f"ALTER TABLE activity_records ADD COLUMN {col} TEXT"))
                        print(f"  ✓ Added column: {col}")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"  - Column {col} already exists")
                    else:
                        print(f"  ❌ Error adding column {col}: {e}")
            
            conn.commit()
        
        return columns

def flexible_parse_activity_data(activity_data):
    """
    Flexible parser that can handle various JSON structures
    """
    try:
        # Parse JSON if it's a string
        if isinstance(activity_data, str):
            if activity_data.strip() in ['', '{}', 'null']:
                return {}
            data = json.loads(activity_data)
        else:
            data = activity_data
        
        extracted = {
            'application_name': 'Unknown',
            'window_title': '',
            'url': None,
            'file_path': None,
            'category': 'other',
            'project_name': None,
            'project_type': None
        }
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # Case 1: Direct app/title fields
            if 'app' in data or 'application' in data or 'application_name' in data:
                extracted['application_name'] = (
                    data.get('app') or 
                    data.get('application') or 
                    data.get('application_name', 'Unknown')
                )
            
            if 'title' in data or 'window_title' in data:
                extracted['window_title'] = data.get('title') or data.get('window_title', '')
            
            # Case 2: Nested data field (ActivityWatch style)
            if 'data' in data and isinstance(data['data'], dict):
                nested = data['data']
                if 'app' in nested:
                    extracted['application_name'] = nested['app']
                if 'title' in nested:
                    extracted['window_title'] = nested['title']
                if 'url' in nested:
                    extracted['url'] = nested['url']
            
            # Case 3: File/Project based structure (from your screenshot)
            if 'file' in data:
                file_path = data.get('file', '')
                if file_path and file_path != 'unknown':
                    extracted['file_path'] = file_path
                    # Extract application from file extension
                    if file_path.endswith('.php'):
                        extracted['application_name'] = 'PHP Development'
                        extracted['category'] = 'ide'
                    elif file_path.endswith('.py'):
                        extracted['application_name'] = 'Python Development'
                        extracted['category'] = 'ide'
                    elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                        extracted['application_name'] = 'JavaScript Development'
                        extracted['category'] = 'ide'
                    else:
                        extracted['application_name'] = 'Code Editor'
                        extracted['category'] = 'ide'
                    
                    # Use file as window title if no title exists
                    if not extracted['window_title']:
                        extracted['window_title'] = file_path
            
            # Extract project info
            if 'project' in data and data['project'] != 'unknown':
                extracted['project_name'] = data['project']
                extracted['project_type'] = 'Development'
            
            # Extract language info
            if 'language' in data and data['language'] != 'unknown':
                if not extracted['application_name'] or extracted['application_name'] == 'Unknown':
                    extracted['application_name'] = f"{data['language']} Development"
                    extracted['category'] = 'ide'
            
            # Case 4: URL-based activities
            if 'url' in data:
                extracted['url'] = data['url']
                extracted['application_name'] = 'Web Browser'
                extracted['category'] = 'browser'
                # Extract domain as project
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(data['url']).netloc
                    extracted['project_name'] = domain
                    extracted['project_type'] = 'Browsing'
                except:
                    pass
            
            # Case 5: Process/Program based
            if 'process' in data or 'program' in data:
                extracted['application_name'] = data.get('process') or data.get('program')
        
        # Final cleanup
        if extracted['application_name'] in [None, '', 'unknown']:
            extracted['application_name'] = 'Unknown Application'
        
        return extracted
        
    except Exception as e:
        print(f"Error parsing activity data: {e}")
        print(f"Data: {str(activity_data)[:200]}...")
        return {
            'application_name': 'Parse Error',
            'window_title': str(e)[:100],
            'category': 'error'
        }

def update_dashboard_data():
    """Main function to update the dashboard data"""
    
    print("=== Flexible Dashboard Data Fix ===\n")
    
    # Check table structure first
    print("1. Checking table structure...")
    check_table_columns()
    
    with engine.connect() as conn:
        # Analyze current state
        print("\n2. Analyzing current data...")
        
        # First, let's see a sample of the actual JSON structure
        result = conn.execute(text("""
            SELECT activity_data 
            FROM activity_records 
            WHERE activity_data IS NOT NULL 
            AND activity_data != '{}' 
            AND activity_data != ''
            LIMIT 5
        """))
        
        print("\n   Sample JSON structures:")
        for idx, (data,) in enumerate(result):
            try:
                parsed = json.loads(data) if isinstance(data, str) else data
                print(f"\n   Sample {idx + 1}:")
                print(f"   {json.dumps(parsed, indent=4)}")
            except:
                print(f"\n   Sample {idx + 1}: Unable to parse")
        
        # Get all records to update
        print("\n3. Processing records...")
        result = conn.execute(text("""
            SELECT id, activity_data, developer_id, timestamp, duration
            FROM activity_records
            WHERE activity_data IS NOT NULL 
            AND activity_data != '{}'
            AND activity_data != ''
            ORDER BY timestamp DESC
        """))
        
        updates = []
        sample_count = 0
        error_count = 0
        
        for record in result:
            record_id, activity_data, developer_id, timestamp, duration = record
            extracted = flexible_parse_activity_data(activity_data)
            
            if extracted:
                update_data = {
                    'id': record_id,
                    'developer_id': developer_id,
                    'timestamp': timestamp,
                    'duration': duration,
                    **extracted
                }
                updates.append(update_data)
                
                # Show samples
                if sample_count < 5 and extracted.get('application_name') != 'Unknown Application':
                    print(f"\n   Sample {sample_count + 1}:")
                    print(f"   Developer: {developer_id}")
                    print(f"   App: {extracted['application_name']}")
                    print(f"   Title: {extracted.get('window_title', 'N/A')[:80]}...")
                    print(f"   Category: {extracted.get('category', 'other')}")
                    if extracted.get('project_name'):
                        print(f"   Project: {extracted['project_name']}")
                    sample_count += 1
            else:
                error_count += 1
        
        print(f"\n4. Found {len(updates)} records to update ({error_count} errors)")
        
        # Perform updates
        if updates:
            print("\n5. Updating database...")
            
            trans = conn.begin()
            try:
                batch_size = 100
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i + batch_size]
                    
                    for record in batch:
                        # Build dynamic update query based on available columns
                        update_fields = []
                        params = {'id': record['id']}
                        
                        for field in ['application_name', 'window_title', 'url', 
                                     'file_path', 'category', 'project_name', 'project_type']:
                            if field in record and record[field] is not None:
                                update_fields.append(f"{field} = :{field}")
                                params[field] = record[field]
                        
                        if update_fields:
                            query = f"""
                                UPDATE activity_records
                                SET {', '.join(update_fields)}
                                WHERE id = :id
                            """
                            conn.execute(text(query), params)
                    
                    print(f"   Updated {min(i + batch_size, len(updates))}/{len(updates)} records...")
                
                trans.commit()
                print("\n✅ Successfully updated all records!")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during update: {e}")
                raise
        
        # Verify results
        print("\n6. Verification:")
        
        # Application distribution
        result = conn.execute(text("""
            SELECT application_name, COUNT(*) as count
            FROM activity_records
            WHERE application_name IS NOT NULL
            GROUP BY application_name
            ORDER BY count DESC
            LIMIT 10
        """))
        
        print("\n   Top applications:")
        apps = result.fetchall()
        if apps:
            for app, count in apps:
                print(f"   - {app}: {count} records")
        else:
            print("   ❌ No applications found!")
        
        # Developer summary
        result = conn.execute(text("""
            SELECT 
                developer_id,
                COUNT(DISTINCT application_name) as app_count,
                COUNT(*) as record_count,
                SUM(duration) / 3600 as hours
            FROM activity_records
            WHERE application_name IS NOT NULL
            AND application_name != 'Unknown Application'
            GROUP BY developer_id
        """))
        
        print("\n   Developer activity:")
        devs = result.fetchall()
        if devs:
            for dev_id, app_count, record_count, hours in devs:
                hours_val = hours if hours else 0
                print(f"   - {dev_id}: {app_count} apps, {record_count} records, {hours_val:.1f} hours")
        else:
            print("   ❌ No developer activity found!")
        
        print("\n✅ Dashboard fix completed!")
        print("\nNext steps:")
        print("1. Restart your dashboard API server")
        print("2. Clear your browser cache")
        print("3. Refresh the dashboard")

if __name__ == "__main__":
    update_dashboard_data()
