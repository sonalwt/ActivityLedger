# diagnostic_endpoint.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

router = APIRouter()

@router.get("/api/diagnostic/table-check")
async def check_tables(db: Session = Depends(get_db)):
    """Check which tables exist and their structure"""
    try:
        # Check if tables exist
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('activity_data', 'activity_records')
        """)
        
        tables = db.execute(tables_query).fetchall()
        existing_tables = [t[0] for t in tables]
        
        # Check columns in activity_records
        columns_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'activity_records'
            ORDER BY ordinal_position
        """)
        
        columns = db.execute(columns_query).fetchall()
        
        # Count records
        count_query = text("SELECT COUNT(*) FROM activity_records")
        record_count = db.execute(count_query).scalar()
        
        # Check categorized records
        category_query = text("""
            SELECT category, COUNT(*) as count
            FROM activity_records
            WHERE category IS NOT NULL
            GROUP BY category
        """)
        
        categories = db.execute(category_query).fetchall()
        
        return {
            "existing_tables": existing_tables,
            "activity_records_exists": "activity_records" in existing_tables,
            "activity_data_exists": "activity_data" in existing_tables,
            "columns": [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2]
                }
                for col in columns
            ],
            "total_records": record_count,
            "categories": {
                cat[0]: cat[1] for cat in categories
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }
