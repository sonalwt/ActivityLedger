# add_category_columns.py
"""
Add category-related columns to activity_data table
"""
from sqlalchemy import text
from database import SessionLocal

def add_category_columns():
    """Add category, subcategory, and confidence columns to activity_data table"""
    db = SessionLocal()
    
    try:
        # Add columns if they don't exist
        columns_to_add = [
            "ALTER TABLE activity_data ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
            "ALTER TABLE activity_data ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100)",
            "ALTER TABLE activity_data ADD COLUMN IF NOT EXISTS category_confidence FLOAT DEFAULT 0.0",
            
            # Create index for better query performance
            "CREATE INDEX IF NOT EXISTS idx_activity_category ON activity_data(category)",
            "CREATE INDEX IF NOT EXISTS idx_activity_developer_category ON activity_data(developer_id, category)",
            "CREATE INDEX IF NOT EXISTS idx_activity_timestamp_category ON activity_data(timestamp, category)"
        ]
        
        for sql in columns_to_add:
            print(f"Executing: {sql}")
            db.execute(text(sql))
        
        db.commit()
        print("✅ Successfully added category columns to activity_data table")
        
        # Show current table structure
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'activity_data'
            AND column_name IN ('category', 'subcategory', 'category_confidence')
            ORDER BY ordinal_position
        """)).fetchall()
        
        print("\nNew columns:")
        for col in result:
            print(f"  - {col[0]} ({col[1]}) NULL: {col[2]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding category columns: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    add_category_columns()
