# API endpoints for productivity and project analysis from database
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone, date
from database import get_db
from models import Developer, ActivityRecord
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Define productive applications/categories
PRODUCTIVE_CATEGORIES = ['Development', 'IDE', 'Code', 'Terminal', 'Documentation']
PRODUCTIVE_APPS = [
    'Visual Studio Code', 'IntelliJ IDEA', 'PyCharm', 'WebStorm', 'Android Studio',
    'Sublime Text', 'Atom', 'Eclipse', 'NetBeans', 'Vim', 'Emacs',
    'Terminal', 'Command Prompt', 'PowerShell', 'Git Bash',
    'Chrome', 'Firefox', 'Edge', 'Safari',  # When on development sites
    'Postman', 'Insomnia', 'Docker Desktop',
    'Microsoft Teams', 'Slack', 'Zoom',  # Communication during work
    'Microsoft Word', 'Excel', 'PowerPoint', 'Google Docs'
]

@router.get("/api/developer/{developer_id}/productivity-hours")
async def get_developer_productivity_hours(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Calculate productivity hours for a developer from database"""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc) - timedelta(days=7)  # Last 7 days
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Get developer info
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        # Query daily productivity using raw SQL for better control
        daily_productivity = db.execute(text("""
            SELECT 
                DATE(timestamp) as work_date,
                SUM(duration) / 3600.0 as total_hours,
                SUM(CASE 
                    WHEN category IN :productive_categories 
                    OR application_name IN :productive_apps 
                    THEN duration 
                    ELSE 0 
                END) / 3600.0 as productive_hours,
                COUNT(DISTINCT application_name) as apps_used,
                COUNT(*) as total_activities
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY DATE(timestamp)
            ORDER BY work_date DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end,
            "productive_categories": tuple(PRODUCTIVE_CATEGORIES),
            "productive_apps": tuple(PRODUCTIVE_APPS)
        }).fetchall()
        
        # Calculate productivity by hour of day
        hourly_distribution = db.execute(text("""
            SELECT 
                EXTRACT(HOUR FROM timestamp) as hour_of_day,
                SUM(duration) / 3600.0 as total_hours
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY EXTRACT(HOUR FROM timestamp)
            ORDER BY hour_of_day
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Calculate app usage statistics
        app_usage = db.execute(text("""
            SELECT 
                application_name,
                category,
                SUM(duration) / 3600.0 as total_hours,
                COUNT(*) as usage_count
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY application_name, category
            ORDER BY total_hours DESC
            LIMIT 20
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Format results
        daily_stats = []
        total_work_hours = 0
        total_productive_hours = 0
        
        for row in daily_productivity:
            work_date, total_hours, productive_hours, apps_used, activities = row
            productivity_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
            
            daily_stats.append({
                "date": work_date.isoformat() if work_date else None,
                "total_hours": round(float(total_hours), 2),
                "productive_hours": round(float(productive_hours), 2),
                "productivity_percentage": round(productivity_percentage, 1),
                "apps_used": apps_used,
                "total_activities": activities
            })
            
            total_work_hours += total_hours
            total_productive_hours += productive_hours
        
        # Format hourly distribution
        hourly_stats = [{
            "hour": int(hour),
            "hours": round(float(hours), 2)
        } for hour, hours in hourly_distribution]
        
        # Format app usage
        app_stats = [{
            "application": app_name,
            "category": category or "Other",
            "hours": round(float(hours), 2),
            "usage_count": count,
            "is_productive": category in PRODUCTIVE_CATEGORIES or app_name in PRODUCTIVE_APPS
        } for app_name, category, hours, count in app_usage]
        
        # Calculate overall statistics
        overall_productivity = (total_productive_hours / total_work_hours * 100) if total_work_hours > 0 else 0
        avg_daily_hours = total_work_hours / len(daily_stats) if daily_stats else 0
        
        return {
            "developer": {
                "id": developer.developer_id,
                "name": developer.name
            },
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "overall_stats": {
                "total_work_hours": round(total_work_hours, 2),
                "total_productive_hours": round(total_productive_hours, 2),
                "productivity_percentage": round(overall_productivity, 1),
                "average_daily_hours": round(avg_daily_hours, 2),
                "total_days_worked": len(daily_stats)
            },
            "daily_productivity": daily_stats,
            "hourly_distribution": hourly_stats,
            "top_applications": app_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating productivity hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/developer/{developer_id}/project-breakdown")
async def get_developer_project_breakdown(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get project-wise breakdown for a developer from database"""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc) - timedelta(days=30)  # Last 30 days
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Get developer info
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        # Get project breakdown
        project_stats = db.execute(text("""
            SELECT 
                COALESCE(project_name, 'Unassigned') as project,
                SUM(duration) / 3600.0 as total_hours,
                COUNT(DISTINCT DATE(timestamp)) as days_worked,
                COUNT(DISTINCT application_name) as apps_used,
                COUNT(*) as activity_count,
                MIN(timestamp) as first_activity,
                MAX(timestamp) as last_activity
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY project_name
            ORDER BY total_hours DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Get daily project distribution
        daily_project_hours = db.execute(text("""
            SELECT 
                DATE(timestamp) as work_date,
                COALESCE(project_name, 'Unassigned') as project,
                SUM(duration) / 3600.0 as hours
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY DATE(timestamp), project_name
            ORDER BY work_date DESC, hours DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Get project activity details
        project_activities = db.execute(text("""
            SELECT 
                COALESCE(project_name, 'Unassigned') as project,
                application_name,
                category,
                SUM(duration) / 3600.0 as hours,
                COUNT(*) as count
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY project_name, application_name, category
            ORDER BY project_name, hours DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Format project statistics
        projects = []
        total_hours_all_projects = 0
        
        for row in project_stats:
            project_name, hours, days, apps, activities, first_activity, last_activity = row
            total_hours_all_projects += hours
            
            projects.append({
                "project_name": project_name,
                "total_hours": round(float(hours), 2),
                "days_worked": days,
                "apps_used": apps,
                "activity_count": activities,
                "first_activity": first_activity.isoformat() if first_activity else None,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "average_hours_per_day": round(float(hours) / days, 2) if days > 0 else 0
            })
        
        # Calculate project percentages
        for project in projects:
            project["percentage"] = round(
                (project["total_hours"] / total_hours_all_projects * 100) 
                if total_hours_all_projects > 0 else 0, 1
            )
        
        # Format daily distribution
        daily_distribution = {}
        for work_date, project, hours in daily_project_hours:
            date_str = work_date.isoformat() if work_date else "Unknown"
            if date_str not in daily_distribution:
                daily_distribution[date_str] = []
            daily_distribution[date_str].append({
                "project": project,
                "hours": round(float(hours), 2)
            })
        
        # Format project activities
        project_apps = {}
        for project, app, category, hours, count in project_activities:
            if project not in project_apps:
                project_apps[project] = []
            project_apps[project].append({
                "application": app,
                "category": category or "Other",
                "hours": round(float(hours), 2),
                "usage_count": count
            })
        
        # Limit apps per project to top 10
        for project in project_apps:
            project_apps[project] = project_apps[project][:10]
        
        return {
            "developer": {
                "id": developer.developer_id,
                "name": developer.name
            },
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "summary": {
                "total_hours": round(total_hours_all_projects, 2),
                "total_projects": len(projects),
                "most_active_project": projects[0]["project_name"] if projects else None
            },
            "projects": projects,
            "daily_distribution": daily_distribution,
            "project_applications": project_apps
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/all-developers/productivity-summary")
async def get_all_developers_productivity_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get productivity summary for all developers"""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Get all developers with their productivity stats
        developer_stats = db.execute(text("""
            SELECT 
                d.developer_id,
                d.name,
                COALESCE(SUM(ar.duration) / 3600.0, 0) as total_hours,
                COALESCE(SUM(CASE 
                    WHEN ar.category IN :productive_categories 
                    OR ar.application_name IN :productive_apps 
                    THEN ar.duration 
                    ELSE 0 
                END) / 3600.0, 0) as productive_hours,
                COUNT(DISTINCT ar.project_name) as projects_worked,
                COUNT(ar.id) as total_activities,
                MAX(ar.timestamp) as last_activity
            FROM developers d
            LEFT JOIN activity_records ar ON d.developer_id = ar.developer_id
                AND ar.timestamp >= :start_date
                AND ar.timestamp <= :end_date
            WHERE d.active = true
            GROUP BY d.developer_id, d.name
            ORDER BY total_hours DESC
        """), {
            "start_date": start,
            "end_date": end,
            "productive_categories": tuple(PRODUCTIVE_CATEGORIES),
            "productive_apps": tuple(PRODUCTIVE_APPS)
        }).fetchall()
        
        # Format results
        developers = []
        for row in developer_stats:
            dev_id, name, total_hours, productive_hours, projects, activities, last_activity = row
            
            productivity_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
            
            # Determine status based on last activity
            status = "inactive"
            if last_activity and total_hours > 0:
                time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() < 3600:  # 1 hour
                    status = "active"
                elif time_diff.total_seconds() < 86400:  # 24 hours
                    status = "idle"
            
            developers.append({
                "developer_id": dev_id,
                "name": name,
                "total_hours": round(float(total_hours), 2),
                "productive_hours": round(float(productive_hours), 2),
                "productivity_percentage": round(productivity_percentage, 1),
                "projects_count": projects,
                "activities_count": activities,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "status": status
            })
        
        # Calculate team statistics
        team_total_hours = sum(d["total_hours"] for d in developers)
        team_productive_hours = sum(d["productive_hours"] for d in developers)
        team_productivity = (team_productive_hours / team_total_hours * 100) if team_total_hours > 0 else 0
        active_developers = sum(1 for d in developers if d["status"] == "active")
        
        return {
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "team_summary": {
                "total_developers": len(developers),
                "active_developers": active_developers,
                "team_total_hours": round(team_total_hours, 2),
                "team_productive_hours": round(team_productive_hours, 2),
                "team_productivity_percentage": round(team_productivity, 1),
                "average_hours_per_developer": round(team_total_hours / len(developers), 2) if developers else 0
            },
            "developers": developers
        }
        
    except Exception as e:
        logger.error(f"Error getting all developers productivity summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/developer/{developer_id}/update-project")
async def update_activity_project(
    developer_id: str,
    activity_ids: List[int],
    project_name: str,
    db: Session = Depends(get_db)
):
    """Update project name for specific activities"""
    try:
        # Verify developer exists
        developer = db.query(Developer).filter(
            Developer.developer_id == developer_id
        ).first()
        
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        # Update activities
        updated = db.query(ActivityRecord).filter(
            and_(
                ActivityRecord.developer_id == developer_id,
                ActivityRecord.id.in_(activity_ids)
            )
        ).update(
            {"project_name": project_name},
            synchronize_session=False
        )
        
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated,
            "project_name": project_name,
            "activity_ids": activity_ids
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
