# Test endpoint to verify developer-activity relationships
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models import Developer, ActivityRecord
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/test/developer-relationships")
async def test_developer_relationships(db: Session = Depends(get_db)):
    """Test the relationship between developers and activity_records"""
    try:
        # Test 1: Get developers with their activity counts using ORM
        from sqlalchemy import func
        
        developers_with_counts = db.query(
            Developer,
            func.count(ActivityRecord.id).label('activity_count')
        ).outerjoin(
            ActivityRecord,
            Developer.developer_id == ActivityRecord.developer_id
        ).group_by(
            Developer.id
        ).filter(
            Developer.active == True
        ).all()
        
        orm_results = []
        for dev, count in developers_with_counts:
            orm_results.append({
                "developer_id": dev.developer_id,
                "name": dev.name,
                "activity_count": count
            })
        
        # Test 2: Raw SQL with JOIN
        sql_results = db.execute(text("""
            SELECT 
                d.developer_id,
                d.name,
                COUNT(ar.id) as activity_count,
                MAX(ar.timestamp) as last_activity
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id
            WHERE d.active = true
            GROUP BY d.developer_id, d.name
        """)).fetchall()
        
        sql_formatted = []
        for row in sql_results:
            sql_formatted.append({
                "developer_id": row.developer_id,
                "name": row.name,
                "activity_count": row.activity_count,
                "last_activity": str(row.last_activity) if row.last_activity else None
            })
        
        # Test 3: Sample activities with developer names
        activities_with_names = db.execute(text("""
            SELECT 
                ar.id,
                ar.developer_id,
                d.name as developer_name,
                ar.application_name,
                ar.timestamp
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            LIMIT 5
        """)).fetchall()
        
        activities_formatted = []
        for row in activities_with_names:
            activities_formatted.append({
                "id": row.id,
                "developer_id": row.developer_id,
                "developer_name": row.developer_name,
                "application": row.application_name,
                "timestamp": str(row.timestamp) if row.timestamp else None
            })
        
        return {
            "test": "developer-activity relationships",
            "orm_join_results": orm_results,
            "sql_join_results": sql_formatted,
            "sample_activities_with_developer_names": activities_formatted,
            "relationships_working": len(orm_results) > 0 and len(sql_formatted) > 0
        }
        
    except Exception as e:
        logger.error(f"Error testing relationships: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "test": "developer-activity relationships",
            "relationships_working": False
        }
