# Test endpoint to directly query developers table
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/test/developers-direct")
async def get_developers_direct(db: Session = Depends(get_db)):
    """Direct query to developers table for testing"""
    try:
        # Query developers table directly
        result = db.execute(text("SELECT * FROM developers"))
        developers = []
        
        for row in result:
            developers.append({
                "id": row.id,
                "developer_id": row.developer_id,
                "name": row.name,
                "email": row.email,
                "active": row.active,
                "api_token": row.api_token[:10] + "..." if row.api_token else None,  # Hide most of token
                "created_at": str(row.created_at) if row.created_at else None,
                "last_sync": str(row.last_sync) if row.last_sync else None
            })
        
        # Also check activity_records
        activity_count = db.execute(text("SELECT COUNT(*) FROM activity_records")).scalar()
        
        return {
            "developers_table_count": len(developers),
            "developers": developers,
            "total_activities_in_db": activity_count,
            "message": "Direct query to developers table"
        }
        
    except Exception as e:
        logger.error(f"Error in direct developers query: {e}")
        return {
            "error": str(e),
            "message": "Failed to query developers table"
        }
