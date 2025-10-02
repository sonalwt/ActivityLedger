# Simple fix to show all developers
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/all-developers-simple")
async def get_all_developers_simple(db: Session = Depends(get_db)):
    """Simple query to get all developers"""
    try:
        # Simple query without complex joins
        developers_query = text("""
            SELECT 
                id,
                developer_id,
                name,
                email,
                active,
                created_at,
                last_sync
            FROM developers
            WHERE active = true
            ORDER BY created_at DESC
        """)
        
        result = db.execute(developers_query)
        
        developers = []
        for row in result:
            # Get activity count separately to avoid join issues
            activity_count = 0
            last_activity = None
            
            try:
                # Try with developer_id only (most reliable)
                if row.developer_id:
                    count_result = db.execute(text("""
                        SELECT COUNT(*) as count, MAX(timestamp) as last_activity
                        FROM activity_records 
                        WHERE developer_id = :dev_id
                    """), {"dev_id": row.developer_id}).fetchone()
                    
                    if count_result:
                        activity_count = count_result.count or 0
                        last_activity = count_result.last_activity
            except Exception as e:
                logger.warning(f"Error getting activity count: {e}")
            
            # Determine status
            status = "offline"
            if last_activity:
                try:
                    if hasattr(last_activity, 'replace'):
                        time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                    else:
                        time_diff = datetime.now(timezone.utc) - last_activity
                    
                    if time_diff.total_seconds() < 1800:  # 30 minutes
                        status = "online"
                    elif time_diff.total_seconds() < 86400:  # 24 hours
                        status = "idle"
                except:
                    pass
            
            developers.append({
                "id": row.developer_id or f"dev_{row.id}",
                "name": row.name,
                "hostname": row.name,
                "host": "unknown",
                "port": 5600,
                "status": status,
                "source": "database",
                "description": f"Developer with {activity_count} activities",
                "device_id": row.developer_id or f"dev_{row.id}",
                "activity_count": activity_count,
                "last_seen": last_activity.isoformat() if last_activity else (row.created_at.isoformat() if row.created_at else None),
                "version": "N/A",
                "bucket_count": 0,
                "email": row.email
            })
        
        return {
            "developers": developers,
            "environment": "production",  # Force production mode
            "total_count": len(developers),
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting developers: {e}")
        import traceback
        traceback.print_exc()
        return {
            "developers": [],
            "environment": "production",
            "total_count": 0,
            "error": str(e)
        }
