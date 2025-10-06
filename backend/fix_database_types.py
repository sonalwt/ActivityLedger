from sqlalchemy import create_engine, text
from config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())

# Create engine
engine = create_engine(DATABASE_URL)

def fix_developer_ids():
    """Fix any integer developer_ids in activity_records table"""
    with engine.connect() as conn:
        # First, check if there are any integer developer_ids
        print("Checking for integer developer_ids in activity_records...")
        
        result = conn.execute(text("""
            SELECT DISTINCT developer_id, pg_typeof(developer_id) as type
            FROM activity_records
            WHERE developer_id IS NOT NULL
              AND developer_id ~ '^[0-9]+$'
            LIMIT 10
        """))
        
        numeric_ids = list(result)
        
        if not numeric_ids:
            print("✅ No numeric developer_ids found. Database looks good!")
            return
        
        print(f"Found {len(numeric_ids)} numeric developer_ids that need fixing:")
        for dev_id, dtype in numeric_ids:
            print(f"  - '{dev_id}' (type: {dtype})")
        
        # Ask for confirmation
        response = input("\nDo you want to fix these by converting to string format? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Cancelled.")
            return
        
        # Create a backup first
        print("\nCreating backup of activity_records...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activity_records_backup AS 
                SELECT * FROM activity_records
            """))
            conn.commit()
            print("✅ Backup created as 'activity_records_backup'")
        except Exception as e:
            print(f"⚠️ Backup might already exist: {e}")
        
        # Fix the data - convert numeric developer_ids to proper string format
        print("\nFixing developer_ids...")
        
        # Option 1: Prefix numeric IDs with 'dev_'
        update_query = text("""
            UPDATE activity_records
            SET developer_id = CONCAT('dev_', developer_id)
            WHERE developer_id ~ '^[0-9]+$'
        """)
        
        result = conn.execute(update_query)
        conn.commit()
        
        print(f"✅ Updated {result.rowcount} records")
        
        # Verify the fix
        print("\nVerifying fix...")
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM activity_records
            WHERE developer_id ~ '^[0-9]+$'
        """)).scalar()
        
        if result == 0:
            print("✅ All developer_ids are now properly formatted!")
        else:
            print(f"⚠️ Still found {result} numeric developer_ids")

def check_data_consistency():
    """Check data consistency between tables"""
    with engine.connect() as conn:
        print("\n=== Checking data consistency ===")
        
        # Check for activity_records without matching developers
        result = conn.execute(text("""
            SELECT DISTINCT ar.developer_id, COUNT(*) as count
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            WHERE ar.developer_id IS NOT NULL
              AND d.developer_id IS NULL
            GROUP BY ar.developer_id
            LIMIT 10
        """))
        
        orphaned = list(result)
        if orphaned:
            print(f"\n⚠️ Found activity records for {len(orphaned)} non-existent developers:")
            for dev_id, count in orphaned:
                print(f"  - '{dev_id}': {count} records")
        else:
            print("\n✅ All activity records have matching developers")
        
        # Check for developers without activity
        result = conn.execute(text("""
            SELECT d.developer_id, d.name
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id
            WHERE d.active = true
              AND ar.id IS NULL
            LIMIT 10
        """))
        
        inactive = list(result)
        if inactive:
            print(f"\n⚠️ Found {len(inactive)} active developers without any activity:")
            for dev_id, name in inactive:
                print(f"  - {name} (ID: {dev_id})")
        else:
            print("\n✅ All active developers have activity records")

if __name__ == "__main__":
    print("=== Timesheet Database Fix Tool ===\n")
    
    try:
        # Run checks
        check_data_consistency()
        
        # Fix developer IDs if needed
        fix_developer_ids()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
