from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment files using absolute paths (works regardless of working directory)
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, '.env.local'), override=True)
load_dotenv(os.path.join(_base_dir, '.env.production'), override=False)
load_dotenv(os.path.join(_base_dir, '.env'), override=False)

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

print(f"DEBUG: DATABASE_URL starts with: {DATABASE_URL[:30] if DATABASE_URL else 'None'}")

# Create engine with appropriate settings
try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    elif DATABASE_URL.startswith("postgresql"):
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            connect_args={"sslmode": "require"},
        )
    else:
        engine = create_engine(DATABASE_URL)

except Exception as e:
    print(f"ERROR: Database engine creation failed: {e}")
    raise RuntimeError(f"Failed to create database engine: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Add function to get database connection for testing
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
