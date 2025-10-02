from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import os

# Use the PostgreSQL database URL from config
DATABASE_URL = Config.get_database_url()
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

with SessionLocal() as db:
    # Check columns in activity_records table
    print("\n=== ACTIVITY_RECORDS TABLE COLUMNS ===")
    result = db.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'activity_records'
        ORDER BY ordinal_position
    """))
    
    columns = result.fetchall()
    if columns:
        print("Columns in activity_records table:")
        for col_name, col_type in columns:
            print(f"  - {col_name} ({col_type})")
    else:
        print("No columns found or table doesn't exist")
    
    # Check columns in developers table
    print("\n=== DEVELOPERS TABLE COLUMNS ===")
    result = db.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'developers'
        ORDER BY ordinal_position
    """))
    
    columns = result.fetchall()
    if columns:
        print("Columns in developers table:")
        for col_name, col_type in columns:
            print(f"  - {col_name} ({col_type})")
    else:
        print("No columns found or table doesn't exist")
    
    # Check sample data
    print("\n=== SAMPLE DATA ===")
    print("Sample developers:")
    developers = db.execute(text("SELECT id, developer_id, name FROM developers LIMIT 5")).fetchall()
    for dev in developers:
        print(f"  - ID: {dev[0]}, Developer ID: {dev[1]}, Name: {dev[2]}")
    
    print("\nSample activity records:")
    activities = db.execute(text("SELECT id, developer_id, application_name FROM activity_records LIMIT 5")).fetchall()
    for act in activities:
        print(f"  - ID: {act[0]}, Developer ID: {act[1]}, App: {act[2]}")
