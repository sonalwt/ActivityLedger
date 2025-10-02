# API endpoint using SQLAlchemy ORM relationships
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
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
        # Query developers using ORM
        developers = db.query(Developer).filter(
            (Developer.active == True) | (Developer.active == 1)
        ).all()
        
        developer_list = []
        
        for dev in developers:
            # Count activities using relationship
            activity_count = db.query(ActivityRecord).filter(
                ActivityRecord.developer_id == dev.developer_id
            ).count()
            
            # Get last activity
            last_activity = db.query(ActivityRecord.timestamp).filter(
                ActivityRecord.developer_id == dev.developer_id
            ).order_by(ActivityRecord.timestamp.desc()).first()
            
            # Determine status based on last activity
            status = "offline"
            last_seen = None
            
            if last_activity and last_activity[0]:
                last_seen = last_activity[0]
                if hasattr(last_seen, 'replace'):
                    time_diff = datetime.now(timezone.utc) - last_seen.replace(tzinfo=timezone.utc)
                else:
                    time_diff = datetime.now(timezone.utc) - last_seen
                
                if time_diff.total_seconds() < 1800:  # 30 minutes
                    status = "online"
                elif time_diff.total_seconds() < 86400:  # 24 hours  
                    status = "idle"
            
            developer_list.append({
                "id": dev.developer_id or f"dev_{dev.id}",
                "name": dev.name,
                "hostname": dev.name,
                "host": "unknown",
                "port": 5600,
                "status": status,
                "source": "database",
                "description": f"Developer with {activity_count} activities",
                "device_id": dev.developer_id or f"dev_{dev.id}",
                "activity_count": activity_count,
                "last_seen": last_seen.isoformat() if last_seen else (
                    dev.created_at.isoformat() if dev.created_at else None
                ),
                "version": "N/A",
                "bucket_count": 0,
                "email": dev.email,
                "created_at": dev.created_at.isoformat() if dev.created_at else None,
                "active": dev.active
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
        # Get developer
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        # Get recent activities using ORM
        activities = db.query(ActivityRecord).filter(
            ActivityRecord.developer_id == developer_id
        ).order_by(
            ActivityRecord.timestamp.desc()
        ).limit(limit).all()
        
        activities_list = []
        for activity in activities:
            activities_list.append({
                "id": activity.id,
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
        # Use ORM to get developers with activity stats
        developers_with_stats = db.query(
            Developer,
            func.count(ActivityRecord.id).label('activity_count'),
            func.max(ActivityRecord.timestamp).label('last_activity'),
            func.sum(ActivityRecord.duration).label('total_duration')
        ).outerjoin(
            ActivityRecord,
            Developer.developer_id == ActivityRecord.developer_id
        ).group_by(
            Developer.id
        ).filter(
            (Developer.active == True) | (Developer.active == 1)
        ).all()
        
        developer_list = []
        
        for dev, activity_count, last_activity, total_duration in developers_with_stats:
            # Calculate status
            status = "offline"
            if last_activity:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 1800:
                    status = "online"
                elif time_diff.total_seconds() < 86400:
                    status = "idle"
            
            developer_list.append({
                "id": dev.developer_id,
                "name": dev.name,
                "email": dev.email,
                "status": status,
                "activity_count": activity_count or 0,
                "total_duration_seconds": float(total_duration or 0),
                "total_duration_hours": round(float(total_duration or 0) / 3600, 2),
                "last_activity": last_activity.isoformat() if last_activity else None,
                "created_at": dev.created_at.isoformat() if dev.created_at else None
            })
        
        return {
            "developers": developer_list,
            "total_count": len(developer_list),
            "method": "orm_with_aggregation"
        }
        
    except Exception as e:
        logger.error(f"Error getting developers with stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
