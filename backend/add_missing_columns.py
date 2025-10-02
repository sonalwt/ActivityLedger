"""
Add missing columns to PostgreSQL database
Run this script to update your database schema
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the PostgreSQL database URL from config
DATABASE_URL = Config.get_database_url()
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_missing_columns():
    with SessionLocal() as db:
        try:
            # Check which columns exist
            logger.info("Checking existing columns in activity_records...")
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'activity_records'
            """))
            existing_columns = {row[0] for row in result}
            logger.info(f"Existing columns: {existing_columns}")
            
            # List of columns that might be missing
            columns_to_add = [
                ("developer_name", "VARCHAR(255)"),
                ("developer_hostname", "VARCHAR(255)"),
                ("activity_timestamp", "TIMESTAMP WITH TIME ZONE")
            ]
            
            # Add missing columns
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    logger.info(f"Adding column {col_name}...")
                    db.execute(text(f"""
                        ALTER TABLE activity_records 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                    """))
                    db.commit()
                    logger.info(f"✓ Added column {col_name}")
                else:
                    logger.info(f"✓ Column {col_name} already exists")
            
            # Create indexes for better performance
            logger.info("Creating indexes...")
            indexes = [
                ("idx_activity_developer_name", "activity_records", "developer_name"),
                ("idx_activity_developer_hostname", "activity_records", "developer_hostname"),
                ("idx_activity_timestamp", "activity_records", "activity_timestamp"),
            ]
            
            for idx_name, table_name, col_name in indexes:
                try:
                    db.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON {table_name}({col_name})
                    """))
                    db.commit()
                    logger.info(f"✓ Created index {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create index {idx_name}: {e}")
            
            logger.info("✓ Database schema update completed!")
            
        except Exception as e:
            logger.error(f"Error updating schema: {e}")
            db.rollback()
            raise

if __name__ == "__main__":
    add_missing_columns()
