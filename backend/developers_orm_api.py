# API endpoint using SQLAlchemy ORM relationships
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, String, cast
from typing import List, Optional
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
                COALESCE(d.hourly_cost, 0) as hourly_cost,
                COALESCE(ac.activity_count, 0) as activity_count,
                ac.last_activity
            FROM developers d
            LEFT JOIN (
                SELECT
                    developer_id::VARCHAR as developer_id,
                    COUNT(*) as activity_count,
                    MAX(CASE WHEN COALESCE(category, '') NOT IN ('entertainment', 'non-work') THEN timestamp END) as last_activity
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
             created_at, last_sync, hourly_cost, activity_count, last_activity) = row
            
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
                "hourly_cost": float(hourly_cost or 0),
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


@router.put("/api/developers/{developer_id}")
async def update_developer(
    developer_id: str,
    body: dict,
    db: Session = Depends(get_db)
):
    """Update developer details (name, email)"""
    developer = db.query(Developer).filter(Developer.developer_id == developer_id).first()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")
    if "name" in body and body["name"]:
        developer.name = body["name"]
    if "email" in body:
        developer.email = body["email"] or None
    if "hourly_cost" in body and body["hourly_cost"] is not None:
        developer.hourly_cost = float(body["hourly_cost"])
    db.commit()
    return {"success": True, "developer_id": developer_id}


@router.put("/api/developers/{developer_id}/salary")
async def update_developer_salary(
    developer_id: str,
    hourly_cost: float = Query(..., description="Hourly cost for the developer"),
    db: Session = Depends(get_db)
):
    """Update hourly cost/salary for a developer"""
    developer = db.query(Developer).filter(Developer.developer_id == developer_id).first()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")
    developer.hourly_cost = hourly_cost
    db.commit()
    return {"success": True, "developer_id": developer_id, "hourly_cost": hourly_cost}


@router.delete("/api/developers/{developer_id}")
async def delete_developer(
    developer_id: str,
    db: Session = Depends(get_db)
):
    """Delete a developer (hard delete)"""
    developer = db.query(Developer).filter(Developer.developer_id == developer_id).first()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")
    db.delete(developer)
    db.commit()
    return {"success": True, "developer_id": developer_id}


@router.get("/api/developers-with-stats")
async def get_developers_with_stats(
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    range_days: int = Query(7)
):
    try:
        now = datetime.now(timezone.utc)

        # Parse end_date
        if end_date:
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end = now

        # Parse start_date
        if start_date:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        else:
            start = end - timedelta(days=range_days)

        # Fetch all activity records for all developers in range
        rows = db.query(ActivityRecord).filter(
            ActivityRecord.timestamp >= start,
            ActivityRecord.timestamp <= end
        ).order_by(ActivityRecord.timestamp.asc()).all()

        # Group by developer
        developer_map = {}
        for act in rows:
            dev = act.developer_id
            if dev not in developer_map:
                developer_map[dev] = []
            developer_map[dev].append(act)

        results = []
        team_total_seconds = 0

        for developer in db.query(Developer).filter(Developer.active == True).all():

            dev_id = developer.developer_id
            acts = developer_map.get(dev_id, [])

            # === ACTUAL WORK HOURS CALC (same function you already use) ===
            work_seconds, daily_breakdown = calculate_actual_work_hours([
                type("Row", (), {
                    "timestamp": a.timestamp,
                    "duration": a.duration,
                    "application_name": a.application_name,
                    "window_title": a.window_title
                })() for a in acts
            ])

            team_total_seconds += work_seconds

            # Format
            hours = int(work_seconds // 3600)
            minutes = int((work_seconds % 3600) // 60)

            results.append({
                "id": dev_id,
                "name": developer.name,
                "email": developer.email,
                "actual_work_seconds": work_seconds,
                "actual_work_display": f"{hours}h {minutes}m",
                "productivity_percentage": round(
                    (work_seconds / (range_days * 8 * 3600)) * 100, 2
                ) if work_seconds else 0,
                "last_activity": max([a.timestamp for a in acts]).isoformat() if acts else None,
                "activity_count": len(acts)
            })

        return {
            "developers": results,
            "total_hours_seconds": team_total_seconds,
            "total_hours_display": f"{round(team_total_seconds/3600,2)}h",
            "avg_hours_per_dev": round((team_total_seconds / max(len(results), 1)) / 3600, 2),
            "range_days": range_days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
