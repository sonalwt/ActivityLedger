# API endpoint using SQLAlchemy ORM relationships
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, String, cast
from typing import List
from datetime import datetime, timezone, timedelta
from database import get_db
from models import Developer, ActivityRecord
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/developers-orm")
async def get_developers_using_orm(db: Session = Depends(get_db)):
    """Get all developers using SQLAlchemy ORM with relationships"""
    try:
        # Use raw SQL to avoid type mismatch issues
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                d.id,
                d.developer_id,
                d.name,
                d.email,
                d.active,
                d.created_at,
                d.last_sync,
                COALESCE(ac.activity_count, 0) as activity_count,
                ac.last_activity
            FROM developers d
            LEFT JOIN (
                SELECT 
                    developer_id::VARCHAR as developer_id,
                    COUNT(*) as activity_count,
                    MAX(timestamp) as last_activity
                FROM activity_records
                WHERE developer_id IS NOT NULL
                GROUP BY developer_id
            ) ac ON d.developer_id::VARCHAR = ac.developer_id::VARCHAR
            WHERE d.active = true
        """)
        
        result = db.execute(query)
        developers_with_stats = result.fetchall()
        
        developer_list = []
        
        for row in developers_with_stats:
            # Unpack row data
            (dev_id, developer_id, name, email, active, 
             created_at, last_sync, activity_count, last_activity) = row
            
            # Determine status based on last activity
            status = "offline"
            last_seen = None
            
            if last_activity:
                last_seen = last_activity
                if hasattr(last_seen, 'replace'):
                    time_diff = datetime.now(timezone.utc) - last_seen.replace(tzinfo=timezone.utc)
                else:
                    time_diff = datetime.now(timezone.utc) - last_seen
                
                if time_diff.total_seconds() < 1800:  # 30 minutes
                    status = "online"
                elif time_diff.total_seconds() < 86400:  # 24 hours  
                    status = "idle"
            
            developer_list.append({
                "id": developer_id or f"dev_{dev_id}",
                "name": name,
                "hostname": name,
                "host": "unknown",
                "port": 5600,
                "status": status,
                "source": "database",
                "description": f"Developer with {activity_count} activities",
                "device_id": developer_id or f"dev_{dev_id}",
                "activity_count": activity_count,
                "last_seen": last_seen.isoformat() if last_seen else (
                    created_at.isoformat() if created_at else None
                ),
                "version": "N/A",
                "bucket_count": 0,
                "email": email,
                "created_at": created_at.isoformat() if created_at else None,
                "active": active
            })
        
        return {
            "developers": developer_list,
            "environment": "production",
            "total_count": len(developer_list),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "method": "orm_relationships"
        }
        
    except Exception as e:
        logger.error(f"Error getting developers via ORM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/developer/{developer_id}/activities")
async def get_developer_activities(
    developer_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get activities for a specific developer using ORM"""
    try:
        # Get developer using ORM
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        # Get recent activities with proper join to get developer info
        activities = db.query(
            ActivityRecord,
            Developer.name.label('developer_name')
        ).join(
            Developer,
            ActivityRecord.developer_id == Developer.developer_id,
            isouter=True
        ).filter(
            ActivityRecord.developer_id == developer_id
        ).order_by(
            ActivityRecord.timestamp.desc()
        ).limit(limit).all()
        
        activities_list = []
        for activity, developer_name in activities:
            activities_list.append({
                "id": activity.id,
                "developer_id": activity.developer_id,
                "developer_name": developer_name,
                "application_name": activity.application_name,
                "window_title": activity.window_title,
                "category": activity.category or "Other",
                "duration": activity.duration,
                "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
                "url": activity.url,
                "file_path": activity.file_path,
                "project_name": activity.project_name
            })
        
        return {
            "developer": {
                "id": developer.developer_id,
                "name": developer.name,
                "email": developer.email
            },
            "activities": activities_list,
            "total_activities": len(activities_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting developer activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/developers-with-stats")
async def get_developers_with_stats(db: Session = Depends(get_db)):
    """Get developers with aggregated statistics using ORM"""
    try:
        # Use raw SQL to avoid type mismatch issues
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                d.developer_id,
                d.name,
                d.email,
                d.created_at,
                COUNT(ar.id) as activity_count,
                MAX(ar.timestamp) as last_activity,
                COALESCE(SUM(ar.duration), 0) as total_duration
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id::VARCHAR = ar.developer_id::VARCHAR
            WHERE d.active = true
            GROUP BY d.developer_id, d.name, d.email, d.created_at
        """)
        
        result = db.execute(query)
        developers_with_stats = result.fetchall()
        
        developer_list = []
        
        for row in developers_with_stats:
            # Unpack row data
            (developer_id, name, email, created_at,
             activity_count, last_activity, total_duration) = row
            
            # Calculate status
            status = "offline"
            if last_activity:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 1800:
                    status = "online"
                elif time_diff.total_seconds() < 86400:
                    status = "idle"
            
            developer_list.append({
                "id": developer_id,
                "name": name,
                "email": email,
                "status": status,
                "activity_count": activity_count or 0,
                "total_duration_seconds": float(total_duration or 0),
                "total_duration_hours": round(float(total_duration or 0) / 3600, 2),
                "last_activity": last_activity.isoformat() if last_activity else None,
                "created_at": created_at.isoformat() if created_at else None
            })
        
        return {
            "developers": developer_list,
            "total_count": len(developer_list),
            "method": "orm_with_aggregation"
        }
        
    except Exception as e:
        logger.error(f"Error getting developers with stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
