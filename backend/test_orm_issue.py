import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", Config.get_database_url())
print(f"Database URL: {DATABASE_URL}")

# Create engine with echo to see SQL queries
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test 1: Simple connection
print("\n=== Test 1: Simple Connection ===")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Connection successful")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# Test 2: Import models
print("\n=== Test 2: Import Models ===")
try:
    import models
    print("✅ Models imported successfully")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Create tables (if not exist)
print("\n=== Test 3: Create Tables ===")
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Tables created/verified")
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Simple ORM query
print("\n=== Test 4: Simple ORM Query ===")
try:
    db = SessionLocal()
    # Simple query without joins
    developers = db.query(models.Developer).filter(models.Developer.active == True).limit(5).all()
    print(f"✅ Found {len(developers)} active developers")
    db.close()
except Exception as e:
    print(f"❌ ORM query failed: {e}")
    import traceback
    traceback.print_exc()
    
# Test 5: Test the problematic join
print("\n=== Test 5: Test Join Query ===")
try:
    from sqlalchemy import func
    db = SessionLocal()
    
    # This is the query that's failing
    subquery = db.query(
        models.ActivityRecord.developer_id,
        func.count(models.ActivityRecord.id).label('activity_count'),
        func.max(models.ActivityRecord.timestamp).label('last_activity')
    ).group_by(models.ActivityRecord.developer_id).subquery()
    
    query = db.query(
        models.Developer,
        func.coalesce(subquery.c.activity_count, 0).label('activity_count'),
        subquery.c.last_activity
    ).outerjoin(
        subquery,
        models.Developer.developer_id == subquery.c.developer_id
    ).filter(
        models.Developer.active == True
    )
    
    # Try to execute
    result = query.all()
    print(f"✅ Join query successful, found {len(result)} results")
    db.close()
except Exception as e:
    print(f"❌ Join query failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All tests completed ===")
