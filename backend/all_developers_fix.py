# Quick fix to always show developers from database
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/all-developers")
async def get_all_developers_fix(db: Session = Depends(get_db)):
    """Get all developers from database regardless of environment"""
    try:
        # Query developers table
        # First, check which columns exist in activity_records
        columns_check = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'activity_records'
        """)).fetchall()
        
        available_columns = [col[0] for col in columns_check]
        has_developer_name = 'developer_name' in available_columns
        
        # Build query based on available columns
        if has_developer_name:
            developers_query = text("""
                SELECT 
                    d.id,
                    d.developer_id,
                    d.name,
                    d.email,
                    d.active,
                    d.created_at,
                    d.last_sync,
                    COUNT(DISTINCT ar.id) as activity_count,
                    MAX(ar.timestamp) as last_activity
                FROM developers d
                LEFT JOIN activity_records ar ON (
                    ar.developer_id = d.developer_id 
                    OR ar.developer_name = d.name
                )
                WHERE d.active = true OR d.active = 1
                GROUP BY d.id, d.developer_id, d.name, d.email, d.active, d.created_at, d.last_sync
                ORDER BY d.created_at DESC
            """)
        else:
            # Fallback query without developer_name column
            developers_query = text("""
                SELECT 
                    d.id,
                    d.developer_id,
                    d.name,
                    d.email,
                    d.active,
                    d.created_at,
                    d.last_sync,
                    COUNT(DISTINCT ar.id) as activity_count,
                    MAX(ar.timestamp) as last_activity
                FROM developers d
                LEFT JOIN activity_records ar ON ar.developer_id = d.developer_id
                WHERE d.active = true OR d.active = 1
                GROUP BY d.id, d.developer_id, d.name, d.email, d.active, d.created_at, d.last_sync
                ORDER BY d.created_at DESC
            """)
        
        result = db.execute(developers_query)
        
        developers = []
        for row in result:
            # Determine status based on last activity
            status = "offline"
            if row.last_activity:
                time_diff = datetime.now(timezone.utc) - row.last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 1800:  # 30 minutes
                    status = "online"
                elif time_diff.total_seconds() < 86400:  # 24 hours
                    status = "idle"
            
            developers.append({
                "id": row.developer_id or f"dev_{row.id}",
                "name": row.name,
                "hostname": row.name,
                "host": "unknown",
                "port": 5600,
                "status": status,
                "source": "database",
                "description": f"Developer with {row.activity_count} activities",
                "device_id": row.developer_id or f"dev_{row.id}",
                "activity_count": row.activity_count,
                "last_seen": row.last_activity.isoformat() if row.last_activity else row.created_at.isoformat() if row.created_at else None,
                "version": "N/A",
                "bucket_count": 0,
                "email": row.email
            })
        
        # Also check for local ActivityWatch instances
        from developer_discovery import DeveloperDiscovery
        discovery = DeveloperDiscovery(db)
        local_instances = discovery.discover_local_instances()
        
        # Add local instances if not already in the list
        existing_ids = {dev['id'] for dev in developers}
        for instance in local_instances:
            if instance['id'] not in existing_ids:
                developers.append(instance)
        
        return {
            "developers": developers,
            "environment": "production",  # Force production mode to show all developers
            "total_count": len(developers),
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting all developers: {e}")
        import traceback
        traceback.print_exc()
        return {
            "developers": [],
            "environment": "production",
            "total_count": 0,
            "error": str(e)
        }
