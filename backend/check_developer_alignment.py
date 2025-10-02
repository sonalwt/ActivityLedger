"""
Script to check and optionally fix developer_id alignment between tables
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = Config.get_database_url()
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_developer_alignment():
    with SessionLocal() as db:
        print("\n=== CHECKING DEVELOPER ID ALIGNMENT ===")
        
        # 1. Get all developers from developers table
        developers = db.execute(text("""
            SELECT id, developer_id, name 
            FROM developers 
            ORDER BY id
        """)).fetchall()
        
        print("\nDevelopers in 'developers' table:")
        for dev in developers:
            print(f"  ID: {dev[0]}, developer_id: '{dev[1]}', name: '{dev[2]}'")
        
        # 2. Get unique developer_ids from activity_records
        activity_devs = db.execute(text("""
            SELECT DISTINCT developer_id, COUNT(*) as count
            FROM activity_records
            WHERE developer_id IS NOT NULL
            GROUP BY developer_id
            ORDER BY count DESC
        """)).fetchall()
        
        print(f"\nUnique developer_ids in 'activity_records' table:")
        for dev_id, count in activity_devs:
            print(f"  developer_id: '{dev_id}', activities: {count}")
        
        # 3. Check for mismatches
        dev_table_ids = {dev[1] for dev in developers}  # developer_id column
        activity_table_ids = {dev[0] for dev in activity_devs}
        
        print("\n=== ALIGNMENT CHECK ===")
        
        # Developer IDs in activity_records but not in developers table
        orphaned = activity_table_ids - dev_table_ids
        if orphaned:
            print(f"\n⚠️  Developer IDs in activity_records but NOT in developers table:")
            for dev_id in orphaned:
                count = next(c for d, c in activity_devs if d == dev_id)
                print(f"  - '{dev_id}' ({count} activities)")
                
                # Suggest a fix
                print(f"    Suggested fix: Check if this matches any developer name in the developers table")
                
        # Developer IDs in developers table but no activities
        no_activities = dev_table_ids - activity_table_ids
        if no_activities:
            print(f"\n⚠️  Developers with no activities:")
            for dev_id in no_activities:
                dev_name = next(dev[2] for dev in developers if dev[1] == dev_id)
                print(f"  - '{dev_id}' (name: '{dev_name}')")
        
        if not orphaned and not no_activities:
            print("\n✅ All developer IDs are properly aligned!")
        
        # 4. Sample join test
        print("\n=== SAMPLE JOIN TEST ===")
        join_test = db.execute(text("""
            SELECT 
                d.developer_id,
                d.name,
                COUNT(ar.id) as activity_count
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id
            WHERE d.active = true
            GROUP BY d.developer_id, d.name
        """)).fetchall()
        
        print("Join results:")
        for dev_id, name, count in join_test:
            print(f"  {name} (developer_id: {dev_id}): {count} activities")

def suggest_fixes():
    """Suggest SQL commands to fix alignment issues"""
    with SessionLocal() as db:
        # Get orphaned developer_ids
        result = db.execute(text("""
            SELECT DISTINCT ar.developer_id, COUNT(*) as count
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            WHERE d.developer_id IS NULL 
                AND ar.developer_id IS NOT NULL
            GROUP BY ar.developer_id
        """)).fetchall()
        
        if result:
            print("\n=== SUGGESTED FIXES ===")
            print("To fix orphaned activity records, you can either:")
            print("\n1. Add missing developers to the developers table:")
            
            for dev_id, count in result:
                print(f"\n-- For developer_id '{dev_id}' with {count} activities:")
                print(f"INSERT INTO developers (developer_id, name, email, active, created_at)")
                print(f"VALUES ('{dev_id}', '{dev_id}', '{dev_id}@company.com', true, NOW());")
            
            print("\n2. OR update activity_records to use existing developer_ids from the developers table")
            print("   (only if you know the correct mapping)")

if __name__ == "__main__":
    check_developer_alignment()
    suggest_fixes()
