# Simple debug endpoint to check activity data
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/debug/activity-check/{developer_id}")
async def debug_activity_check(
    developer_id: str,
    db: Session = Depends(get_db)
):
    """Debug endpoint to check activity data for a developer"""
    try:
        # Check if developer exists
        dev_check = db.execute(
            text("SELECT * FROM developers WHERE developer_id = :dev_id OR id::text = :dev_id"),
            {"dev_id": developer_id}
        ).fetchone()
        
        if not dev_check:
            return {
                "error": f"Developer '{developer_id}' not found",
                "available_developers": db.execute(
                    text("SELECT developer_id, name FROM developers")
                ).fetchall()
            }
        
        # Get activity count
        activity_count = db.execute(
            text("""
                SELECT COUNT(*), 
                       MIN(timestamp) as first_activity,
                       MAX(timestamp) as last_activity
                FROM activity_records 
                WHERE developer_id = :dev_id
            """),
            {"dev_id": developer_id}
        ).fetchone()
        
        # Get category breakdown
        categories = db.execute(
            text("""
                SELECT category, COUNT(*) as count, SUM(duration) as total_duration
                FROM activity_records 
                WHERE developer_id = :dev_id
                  AND timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY category
                ORDER BY count DESC
            """),
            {"dev_id": developer_id}
        ).fetchall()
        
        # Get sample activities
        samples = db.execute(
            text("""
                SELECT application_name, category, duration, timestamp
                FROM activity_records 
                WHERE developer_id = :dev_id
                ORDER BY timestamp DESC
                LIMIT 10
            """),
            {"dev_id": developer_id}
        ).fetchall()
        
        return {
            "developer_id": developer_id,
            "developer_exists": True,
            "total_activities": activity_count[0] if activity_count else 0,
            "date_range": {
                "first_activity": activity_count[1].isoformat() if activity_count[1] else None,
                "last_activity": activity_count[2].isoformat() if activity_count[2] else None
            },
            "last_7_days_categories": [
                {
                    "category": cat[0] or "uncategorized",
                    "count": cat[1],
                    "duration_seconds": float(cat[2] or 0),
                    "duration_hours": round(float(cat[2] or 0) / 3600, 2)
                }
                for cat in categories
            ],
            "recent_activities": [
                {
                    "app": sample[0],
                    "category": sample[1],
                    "duration": sample[2],
                    "timestamp": sample[3].isoformat() if sample[3] else None
                }
                for sample in samples
            ]
        }
        
    except Exception as e:
        logger.error(f"Debug check error: {e}")
        return {"error": str(e)}
