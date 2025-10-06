from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
print(f"Database URL: {DATABASE_URL}")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    # Test connection
    with engine.connect() as conn:
        print("✅ Database connection successful!")
        
        # Check if tables exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('developers', 'activity_records')
        """))
        
        tables = [row[0] for row in result]
        print(f"\nExisting tables: {tables}")
        
        # Check developers table
        dev_count = conn.execute(text("SELECT COUNT(*) FROM developers")).scalar()
        print(f"\nDevelopers in database: {dev_count}")
        
        # Check activity_records table
        act_count = conn.execute(text("SELECT COUNT(*) FROM activity_records")).scalar()
        print(f"Activity records in database: {act_count}")
        
        # Test a simple join query
        print("\n Testing join query...")
        test_query = text("""
            SELECT 
                d.developer_id,
                d.name,
                COUNT(ar.id) as activity_count
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id
            WHERE d.active = true
            GROUP BY d.developer_id, d.name
            LIMIT 5
        """)
        
        result = conn.execute(test_query)
        print("Join query successful!")
        for row in result:
            print(f"  Developer: {row[1]} (ID: {row[0]}) - Activities: {row[2]}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
