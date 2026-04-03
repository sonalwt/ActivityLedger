from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment files explicitly
load_dotenv('.env.local', override=True)  # Load local first
load_dotenv('.env.production', override=False)  # Fallback to production
load_dotenv()  # Load default .env if exists

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug print
print(f"DEBUG: DATABASE_URL from env: {repr(DATABASE_URL)}")
print(f"DEBUG: ENVIRONMENT from env: {repr(os.getenv('ENVIRONMENT'))}")

# Use SQLite as default if no DATABASE_URL or if there's an issue
if not DATABASE_URL or DATABASE_URL == "":
    DATABASE_URL="postgresql://postgres:asdf1234@localhost:5432/timesheet"
    print(f"DEBUG: Using default Postgres: {DATABASE_URL}")

# Create engine with appropriate settings
try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        print("DEBUG: Using SQLite engine")
    elif DATABASE_URL.startswith("postgresql"):
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
        print("DEBUG: Using PostgreSQL engine")
    else:
        engine = create_engine(DATABASE_URL)
        print("DEBUG: Using generic engine")
    
    # Test connection
    with engine.connect() as conn:
        print(f"DEBUG: Database connection successful!")

except Exception as e:
    print(f"ERROR: Database connection failed: {e}")
    print(f"ERROR: Please check your DATABASE_URL and ensure PostgreSQL is running")
    raise RuntimeError(f"Failed to connect to database: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Add function to get database connection for testing
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
