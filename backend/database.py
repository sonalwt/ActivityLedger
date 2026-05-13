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


if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

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
        )
    else:
        engine = create_engine(DATABASE_URL)

    # Test connection
    with engine.connect() as conn:
        pass

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
