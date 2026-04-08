# API endpoints for productivity and project analysis from database
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone, date
from database import get_db
from models import Developer, ActivityRecord, Project
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Define productive applications/categories
CODING_CATEGORIES = ['Development', 'IDE', 'Code', 'Terminal', 'Documentation']
CODING_APPS = [
    'Visual Studio Code', 'IntelliJ IDEA', 'PyCharm', 'WebStorm', 'Android Studio',
    'Sublime Text', 'Atom', 'Eclipse', 'NetBeans', 'Vim', 'Emacs',
    'Terminal', 'Command Prompt', 'PowerShell', 'Git Bash',
    'Chrome', 'Firefox', 'Edge', 'Safari',  # When on development sites
    'Postman', 'Insomnia', 'Docker Desktop',
    'Microsoft Teams', 'Slack', 'Zoom',  # Communication during work
    'Microsoft Word', 'Excel', 'PowerPoint', 'Google Docs'
]

# Work-related browser keywords - browser activities matching these in
# window_title or url are counted as productive in productivity calculation
# NOTE: Project/client names are fetched dynamically from the projects table
WORK_BROWSER_KEYWORDS = [
    # Development platforms
    'github', 'gitlab', 'bitbucket', 'stackoverflow', 'stack overflow',
    # Server/hosting panels
    'cpanel', 'phpmyadmin', 'plesk',
    # Work email
    'gmail', 'firsteconomy', '@firsteconomy', 'mail',
    # Office tools in browser
    'excel', 'google sheets', 'google docs', 'google drive',
    # Dev tools in browser
    'localhost', '127.0.0.1', 'postman', 'swagger', 'devtools',
    'jira', 'confluence', 'trello', 'notion', 'asana', 'clickup',
    # AI coding tools
    'chatgpt', 'claude', 'perplexity', 'phind', 'copilot',
    # Cloud platforms
    'aws', 'azure', 'firebase', 'vercel', 'netlify',
    # Client/project work in browser
    'cms', 'admin', 'dashboard', 'panel', 'portal',
    'hdfc', 'waaree', 'mahindra', 'manulife', 'indosolar',
    # Timesheet
    'timesheet',
]

# Daily target hours for productivity calculation
DAILY_TARGET_HOURS = 8.0



def _build_work_browser_condition(keywords):
    """Build SQL OR condition for work-related browser pattern matching."""
    conditions = []
    for kw in keywords:
        safe_kw = kw.replace("'", "''")
        conditions.append(f"LOWER(ar.window_title) LIKE '%{safe_kw}%'")
        conditions.append(f"LOWER(COALESCE(ar.url, '')) LIKE '%{safe_kw}%'")
    return "(" + " OR ".join(conditions) + ")"


def format_duration(seconds):
    """Convert seconds to hours, minutes, seconds format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"

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
        
        # Query daily productivity using raw SQL
        # Productive = productive + server + browser (all 100%)
        # non-work (idle/lock screen) is excluded
        # Only include days with > 2 hours of total activity
        daily_productivity = db.execute(text(f"""
            SELECT
                DATE(timestamp) as work_date,
                SUM(duration) / 3600.0 as total_hours,
                SUM(
                    CASE
                        WHEN category IN ('development', 'database', 'productivity', 'browser') THEN duration
                        ELSE 0
                    END
                ) / 3600.0 as productive_hours,
                COUNT(DISTINCT application_name) as apps_used,
                COUNT(*) as total_activities
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY DATE(timestamp)
            HAVING SUM(duration) / 3600.0 > 2
            ORDER BY work_date DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
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
            "is_productive": category in ('development', 'database', 'productivity', 'browser')
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
        
        # Fetch active project names from DB to use as work-related browser keywords
        project_names = db.query(Project.name).filter(Project.is_active == True).all()
        dynamic_keywords = list(WORK_BROWSER_KEYWORDS)
        for (proj_name,) in project_names:
            if proj_name and proj_name.lower() not in [k.lower() for k in dynamic_keywords]:
                dynamic_keywords.append(proj_name.lower())

        # Get per-developer productivity stats
        # Working day = day with > 2 hours of total tracked activity
        # Productivity % = avg of (coding%, browser%, server%) where each = category_hours / expected_hours * 100
        # Expected hours = working_days * 8 hours
        query = f"""
            WITH daily_stats AS (
                SELECT
                    ar.developer_id,
                    DATE(ar.timestamp) AS activity_date,
                    SUM(ar.duration) / 3600.0 AS total_day_hours,
                    SUM(CASE WHEN ar.category IN ('development', 'productivity') THEN ar.duration ELSE 0 END) / 3600.0 AS coding_hours,
                    SUM(CASE WHEN ar.category = 'browser' THEN ar.duration ELSE 0 END) / 3600.0 AS browser_hours,
                    SUM(CASE WHEN ar.category = 'database' THEN ar.duration ELSE 0 END) / 3600.0 AS server_hours,
                    LEAST(
                        SUM(
                            CASE
                                WHEN ar.category IN ('development', 'database', 'productivity', 'browser') THEN ar.duration
                                ELSE 0
                            END
                        ) / 3600.0,
                        {DAILY_TARGET_HOURS}
                    ) AS capped_productive_hours
                FROM activity_records ar
                WHERE ar.timestamp >= :start_date
                  AND ar.timestamp <= :end_date
                GROUP BY ar.developer_id, DATE(ar.timestamp)
                HAVING SUM(ar.duration) / 3600.0 > 2
            ),
            ds_agg AS (
                SELECT
                    developer_id,
                    SUM(capped_productive_hours) AS productive_hours,
                    SUM(coding_hours) AS total_coding_hours,
                    SUM(browser_hours) AS total_browser_hours,
                    SUM(server_hours) AS total_server_hours,
                    COUNT(*) AS active_days,
                    SUM(total_day_hours) AS total_hours
                FROM daily_stats
                GROUP BY developer_id
            ),
            ar_agg AS (
                SELECT
                    developer_id,
                    COUNT(DISTINCT project_name) AS projects_worked,
                    COUNT(id) AS total_activities
                FROM activity_records
                WHERE timestamp >= :start_date
                  AND timestamp <= :end_date
                GROUP BY developer_id
            ),
            latest_activity AS (
                SELECT
                    developer_id,
                    MAX(timestamp) AS last_activity
                FROM activity_records
                GROUP BY developer_id
            )
            SELECT
                d.developer_id,
                d.name,
                COALESCE(ds.productive_hours, 0) AS productive_hours,
                COALESCE(ds.active_days, 0) AS active_days,
                COALESCE(ds.total_hours, 0) AS total_hours,
                COALESCE(ds.total_coding_hours, 0) AS coding_hours,
                COALESCE(ds.total_browser_hours, 0) AS browser_hours,
                COALESCE(ds.total_server_hours, 0) AS server_hours,
                COALESCE(ar.projects_worked, 0) AS projects_worked,
                COALESCE(ar.total_activities, 0) AS total_activities,
                la.last_activity
            FROM developers d
            LEFT JOIN ds_agg ds ON ds.developer_id = d.developer_id
            LEFT JOIN ar_agg ar ON ar.developer_id = d.developer_id
            LEFT JOIN latest_activity la ON la.developer_id = d.developer_id
            WHERE d.active = true
            ORDER BY productive_hours DESC
        """
        developer_stats = db.execute(text(query), {
            "start_date": start,
            "end_date": end
        }).fetchall()

        # Calculate productivity per developer
        # productivity = (coding + browser + server) / (active_days * 8h) * 100
        developers = []
        for row in developer_stats:
            dev_id, name, productive_hours, active_days, total_hours, coding_hours, browser_hours, server_hours, projects, activities, last_activity = row

            expected_hours = int(active_days) * DAILY_TARGET_HOURS
            productivity_percentage = min(100.0, (float(productive_hours) / expected_hours * 100)) if expected_hours > 0 else 0.0

            # Determine status based on last activity
            # Match developers_orm_api.py thresholds: <30 min = online, <24h = idle
            status = "offline"
            if last_activity:
                if hasattr(last_activity, 'replace'):
                    time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                else:
                    time_diff = datetime.now(timezone.utc) - last_activity
                if time_diff.total_seconds() < 1800:  # 30 minutes
                    status = "online"
                elif time_diff.total_seconds() < 86400:  # 24 hours
                    status = "idle"

            developers.append({
                "developer_id": dev_id,
                "name": name,
                "total_hours": round(float(total_hours), 2),
                "productive_hours": round(float(productive_hours), 2),
                "productivity_percentage": round(productivity_percentage, 1),
                "active_days": int(active_days),
                "projects_count": projects,
                "activities_count": activities,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "status": status
            })

        # Calculate team statistics
        team_total_hours = sum(d["total_hours"] for d in developers)
        team_productive_hours = sum(d["productive_hours"] for d in developers)
        active_developers = sum(1 for d in developers if d["status"] == "online")
        developers_with_activity = [d for d in developers if d["productive_hours"] > 0]

        # Team productivity = average of individual productivity percentages
        if developers_with_activity:
            team_productivity = sum(d["productivity_percentage"] for d in developers_with_activity) / len(developers_with_activity)
        else:
            team_productivity = 0.0

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
                "average_hours_per_developer": round(team_productive_hours / len(developers_with_activity), 2) if developers_with_activity else 0
            },
            "developers": developers
        }
        
    except Exception as e:
        logger.error(f"Error getting all developers productivity summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Add this to your activity endpoint or create a new one
@router.get("/api/projects-summary/{developer_id}")
async def get_projects_summary(
    developer_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get activities grouped by project name only"""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Group by project name only (not by file)
        query = text("""
            SELECT 
                COALESCE(project_name, 'Uncategorized') as project,
                COUNT(DISTINCT file_path) as files_worked,
                COUNT(*) as total_activities,
                SUM(duration) as total_duration_ms,
                STRING_AGG(DISTINCT category, ', ') as categories
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            AND project_name IS NOT NULL
            AND project_name != ''
            GROUP BY project_name
            ORDER BY total_duration_ms DESC
        """)
        
        result = db.execute(query, {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        projects = []
        total_productive_time = 0
        
        for row in result:
            duration_seconds = (row[3] or 0) / 1000
            
            project_data = {
                "project_name": row[0],
                "files_count": row[1],
                "activities_count": row[2],
                "total_time_seconds": duration_seconds,
                "total_time_formatted": format_duration(duration_seconds),
                "categories": row[4].split(', ') if row[4] else []
            }
            
            projects.append(project_data)
            
            # Count productive time (exclude non-work categories)
            if 'non-work' not in project_data['categories']:
                total_productive_time += duration_seconds
        
        return {
            "projects": projects,
            "total_projects": len(projects),
            "total_productive_time": format_duration(total_productive_time),
            "date_range": {"start": start.isoformat(), "end": end.isoformat()}
        }
    except Exception as e:
        logger.error(f"Error getting projects summary: {e}")
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


@router.get("/api/all-projects")
async def get_all_projects(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of actual project folder names from activity_records - includes both productive and work-related browser activities.
    Only shows projects where at least one developer has spent 1 hour or more on that project."""
    try:
        import re
        from datetime import datetime, timezone, timedelta

        # Parse date range
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = None
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = None

        # Build date filter
        date_filter = ""
        query_params = {}
        if start and end:
            date_filter = "AND timestamp >= :start_date AND timestamp <= :end_date"
            query_params = {"start_date": start, "end_date": end}

        # Fetch all projects with any meaningful time
        projects_query = db.execute(text(f"""
            SELECT
                project_name,
                SUM(activity_count) as activity_count,
                SUM(total_hours) as total_hours,
                COUNT(DISTINCT developer_id) as developer_count,
                SUM(active_days) as active_days,
                MAX(has_ide) as has_ide
            FROM (
                SELECT
                    project_name,
                    developer_id,
                    COUNT(*) as activity_count,
                    SUM(duration) / 3600.0 as total_hours,
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    MAX(CASE WHEN LOWER(application_name) IN (
                        'code.exe', 'visual studio code',
                        'xampp', 'apache', 'httpd', 'mysql', 'mariadb',
                        'phpstorm.exe', 'phpstorm64.exe', 'webstorm.exe', 'webstorm64.exe',
                        'sublime_text.exe', 'notepad++.exe',
                        'terminal', 'powershell.exe', 'cmd.exe',
                        'git-bash.exe', 'windowsterminal.exe',
                        'filezilla.exe', 'filezilla', 'winscp.exe',
                        'cpanel', 'putty.exe', 'mobaxterm.exe'
                    ) OR LOWER(window_title) LIKE '%cpanel%'
                      OR LOWER(window_title) LIKE '%filezilla%'
                    THEN 1 ELSE 0 END) as has_ide
                FROM activity_records
                WHERE project_name IS NOT NULL
                AND project_name != ''
                AND LENGTH(project_name) >= 4
                AND category IN ('development', 'database', 'productivity', 'browser')
                {date_filter}
                GROUP BY project_name, developer_id
                HAVING SUM(duration) / 3600.0 >= 1.0
            ) subq
            GROUP BY project_name
            ORDER BY total_hours DESC
        """), query_params).fetchall()

        # Auto-fetch developer names from DB to exclude them from project list
        dev_names_query = db.execute(text("""
            SELECT DISTINCT LOWER(name) FROM developers WHERE name IS NOT NULL AND name != ''
        """)).fetchall()
        developer_names = {row[0].strip() for row in dev_names_query if row[0]}
        # Also add without spaces (e.g. "Riddhi Dhakhara" -> "riddhidhakhara")
        developer_names_no_space = {name.replace(' ', '') for name in developer_names}
        all_developer_names = developer_names | developer_names_no_space

        def is_browser_noise(name):
            """
            Detect browser category noise (emails, entertainment, personal stuff).
            Returns True if this is noise that should be filtered out.
            """
            import re
            name_lower = name.lower()

            # Email-related patterns
            email_patterns = [
                'inbox', 'draft', 'sent', 'trash', 'spam',
                '@gmail', '@yahoo', '@outlook', '@hotmail', '@firsteconomy',
                'first economy mail', ' mail', 'compose', 'email',
                'invitation:', 're:', 'fwd:', 'weekly task list',
                'notification', 'statement available', 'billing statement',
                'invoice available', 'payment', 'gst invoice'
            ]
            if any(pattern in name_lower for pattern in email_patterns):
                return True

            # Email subject patterns (long sentences with specific words)
            email_subject_indicators = [
                'we have not received',
                'registration notification',
                'amazon web services',
                'billing statement',
                'invoice available'
            ]
            if any(indicator in name_lower for indicator in email_subject_indicators):
                return True

            # Entertainment patterns
            entertainment_patterns = [
                'youtube', 'netflix', 'spotify', 'amazon prime',
                'baby shark', 'nursery rhymes', 'songs', 'music', 'video',
                'cocomelon', 'lyrically'
            ]
            if any(pattern in name_lower for pattern in entertainment_patterns):
                return True

            # Personal names patterns (first + last name)
            # If it looks like "FirstName LastName" with capital letters
            if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', name):
                return True

            # Meeting/calendar patterns
            if 'meeting' in name_lower or 'invitation' in name_lower:
                return True

            # Shopping patterns
            shopping_patterns = [
                'amazon.in', 'amazon.com', 'flipkart', 'myntra',
                'shopping', 'buy online', 'add to cart'
            ]
            if any(pattern in name_lower for pattern in shopping_patterns):
                return True

            return False

        def is_valid_project_name(name):
            """
            Comprehensive validation for project names.
            Moved from SQL to Python for better performance.
            Now includes browser noise filtering.
            """
            import re

            if not name or len(name) < 4:
                return False

            name = name.strip()
            name_lower = name.lower()

            # NEW: Filter out browser noise first
            if is_browser_noise(name):
                return False

            # Reject patterns that start with numbers/special chars
            if re.match(r'^[0-9]+\.', name):
                return False
            if name.startswith('?') or name.startswith('*'):
                return False
            if name.startswith('Merging:'):
                return False

            # Reject git-related patterns
            if '(Working Tree)' in name or '(Index)' in name:
                return False
            if ' and ' in name and ' more tab' in name:
                return False

            # Reject error/exception patterns
            if any(x in name for x in ['Error', 'Exception', 'SQLSTATE', 'HTTP Method']):
                return False

            # Reject drive patterns
            if re.search(r'\([a-zA-Z]:?\)', name):
                return False
            if ' messaged you' in name:
                return False

            # Reject system disk names
            if name.startswith(('New Volume', 'Windows-SSD', 'Local Disk')):
                return False

            # Reject generic browser tabs
            if re.match(r'^(new tab|blank)$', name, re.IGNORECASE):
                return False

            # Reject "Untitled" variations (Untitled, Untitled-1, Untitled 2, etc.)
            if re.match(r'^untitled[\s\-_]*\d*$', name_lower):
                return False

            # Reject "Claude" and AI assistant patterns
            if re.match(r'^claude[\s\-_]', name_lower) or name_lower == 'claude':
                return False
            if 'claude' in name_lower and len(name) < 20:
                return False

            # Reject screen lock / system UI patterns
            screen_lock_patterns = [
                'screen lock', 'lock screen', 'default screen',
                'screen saver', 'screensaver', 'sign-in', 'sign in screen',
                'windows lock', 'lock window'
            ]
            if any(pattern in name_lower for pattern in screen_lock_patterns):
                return False

            # Reject specific unwanted patterns
            unwanted_patterns = [
                'dow futures', 'error test', 'wrong ', 'scheme list', 'test cases',
                'body exfoliator', 'gold rate', 'gift nifty', 'task list', 'new folder',
                'new request', 'open file', 'invalid endpoint',
                'salicylic acid', 'vitamin', 'protein', 'retinol', 'hyaluronic'
            ]
            if any(pattern in name_lower for pattern in unwanted_patterns):
                return False

            # Reject FTP/hosting/API patterns
            if any(x + ':' in name for x in ['FTP', 'Hosting', 'DB', 'API', 'localhost']):
                return False

            # Reject URLs
            if name.startswith('http'):
                return False

            # Reject IP addresses
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', name):
                return False

            # Reject paths
            if '/' in name or '\\' in name:
                return False

            # COMPREHENSIVE file extension filtering - reject ANY name containing a file extension
            file_extensions = [
                # Web/Frontend
                '.js', '.ts', '.jsx', '.tsx', '.vue', '.css', '.scss', '.sass', '.less',
                '.html', '.htm', '.xml', '.svg', '.blade', '.ejs', '.hbs', '.pug',
                # Backend/Server
                '.py', '.php', '.java', '.rb', '.go', '.rs', '.c', '.cpp', '.cs', '.h',
                '.aspx', '.asp', '.jsp', '.pl', '.swift', '.kt', '.scala', '.lua',
                # Config/Data
                '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.env',
                '.lock', '.log', '.bak', '.tmp', '.cache', '.map', '.wasm',
                # Documents
                '.md', '.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt',
                # Media/Images
                '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp', '.tiff',
                '.tif', '.psd', '.ai', '.eps', '.raw', '.heic', '.avif',
                # Audio/Video
                '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.wav',
                '.ogg', '.webm', '.m4a', '.flac', '.aac',
                # Executables
                '.sh', '.bat', '.cmd', '.ps1', '.exe', '.dll', '.so', '.msi', '.apk',
                '.dmg', '.app', '.bin', '.deb', '.rpm',
                # Database
                '.sql', '.db', '.sqlite', '.mdb', '.accdb', '.dbf',
                # Archives
                '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2', '.xz',
                # Office
                '.xls', '.xlsx', '.xlsm', '.csv', '.ppt', '.pptx', '.ods',
                # Crypto/Keys
                '.pem', '.key', '.crt', '.cer', '.p12', '.pfx',
                # Git/Config
                '.git', '.gitignore', '.dockerignore', '.editorconfig',
                # Fonts
                '.ttf', '.otf', '.woff', '.woff2', '.eot',
            ]
            # Check if name contains ANY file extension (not just ends with)
            if re.search(r'\.\w{1,5}(?:\s|$|:|-)', name_lower) or any(name_lower.endswith(ext) for ext in file_extensions):
                # Double-check: allow legitimate domain-based project names (e.g., waaree.com)
                # Only allow if it looks like a domain (word.tld format where tld is a known domain extension)
                domain_tlds = ['.com', '.in', '.org', '.net', '.io', '.co', '.dev', '.app', '.ai']
                is_domain = any(name_lower.endswith(tld) for tld in domain_tlds)
                if not is_domain:
                    return False

            # Reject double underscores
            if '__' in name:
                return False

            # Reject parentheses (system artifacts)
            if '(' in name or ')' in name:
                return False

            # Must start with alphanumeric
            if not name[0].isalnum():
                return False

            # Reject non-project items
            excluded = {
                'general', 'unknown', 'claude', 'cursor', 'open', 'search',
                'inbox', 'message', 'messages', 'whatsapp', 'youtube', 'console',
                'notepad', 'jira', 'jeera', 'services', 'migration',
                'products', 'candid', 'functions', 'controllers',
                'bills', 'ajax', 'banner', 'banners', 'docs', 'excel',
                'onevue', 'regular growth', 'attendance detail',
                'google search', 'google slide', 'google drive',
                'firsteconomy mail', 'first economy mail',
                'fetchall', 'login', 'logout', 'home', 'dashboard',
                'settings', 'downloads', 'desktop', 'explorer',
                'terminal', 'powershell', 'task manager', 'file explorer',
                'control panel', 'command prompt', 'windows terminal',
                'lock screen', 'screen lock', 'screen saver',
                'new tab', 'untitled', 'welcome', 'debug', 'output',
                'problems', 'extensions', 'scratches',
                'gmail', 'outlook', 'yahoo', 'google', 'chrome', 'firefox', 'edge',
                'meet', 'zoom', 'teams', 'skype', 'slack', 'telegram',
                'instagram', 'facebook', 'twitter', 'snapchat',
                'chatgpt', 'copilot', 'gemini',
                'postman', 'figma', 'photoshop', 'canva',
                'calculator', 'paint', 'wordpad', 'media player',
                'snipping tool', 'recycle bin',
                'system32', 'windows', 'program', 'documents',
                'backend', 'frontend', 'components', 'src', 'dist', 'build',
                'public', 'static', 'images', 'uploads', 'temp', 'assets',
                'node_modules', 'htdocs', 'xampp',
                'activitywatch', 'activitywatch sync',
                'bitcoin', 'tradingview',
                'seeders', 'flow', 'uknowa', 'uknowva', 'naishana', 'naishana r', 'nishana', 'nishana r',
                'models', 'routes', 'views', 'helpers', 'middleware',
                'config', 'database', 'migrations', 'factories',
                'ajaxservice', 'onvue', 'onevue',
                'fz3temp-2',
                # Generic code/IDE folder names - not real projects
                'tools', 'startup', 'projects', 'layouts', 'layout',
                'transactions', 'constants', 'switch', 'user', 'users',
                'mrunali', 'fe tech team', 'search results',
                'visual studio code', 'visual studio',
                'utils', 'lib', 'vendor', 'packages', 'modules',
                'tests', 'specs', 'fixtures', 'resources', 'lang',
                'traits', 'interfaces', 'abstract', 'enums', 'types',
                'hooks', 'store', 'reducers', 'actions', 'selectors',
                'pages', 'screens', 'widgets', 'adapters', 'repositories',
                'entities', 'schemas', 'pipes', 'guards', 'interceptors',
                'commands', 'events', 'jobs', 'notifications', 'policies',
                'channels', 'exceptions', 'filters', 'observers',
            }
            if name_lower in excluded:
                return False

            # Reject partial matches for noise patterns
            noise_substrings = [
                'ajax', 'temp-', 'search result',
            ]
            if any(sub in name_lower for sub in noise_substrings):
                return False

            # Reject developer names (auto-fetched from database)
            if name_lower in all_developer_names:
                return False
            # Also check first name only (e.g. "mrunali" matches "Mrunali Patel")
            first_name = name_lower.split()[0] if ' ' in name_lower else name_lower
            if any(first_name == dev.split()[0] for dev in developer_names if len(first_name) >= 4):
                return False

            # Reject person name patterns (for names not in DB)
            # "Firstname Lastname" or "Firstname L" pattern (with space)
            if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]*$', name) and len(name) < 25:
                return False
            # "FirstnameLastname" camelCase pattern (no space, e.g. RiddhiDhakhara)
            if re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', name) and len(name) < 25:
                return False

            # Reject patterns starting with action verbs
            if re.match(r'^(get |create |download |import |generate |update |register |call to )', name_lower):
                return False

            # Reject patterns ending with form/password
            if re.search(r'(form|password|management|managment)$', name_lower):
                return False

            # Reject Laravel/framework folder names (seeders, factories, etc.)
            framework_patterns = ['seeder', 'factory', 'middleware', 'provider', 'handler', 'listener']
            if any(name_lower.endswith(p) or name_lower.endswith(p + 's') for p in framework_patterns):
                return False

            return True

        def extract_root_name(name):
            """
            Extract a canonical root name for consolidation.
            e.g. 'godrej-ihp-lp' -> 'godrej', 'jaypee-website-development' -> 'jaypee'
            Works by taking the first meaningful word from hyphenated/underscore names,
            or the first word from multi-word names like 'Godrej Reserve Kandivali'.
            """
            clean = name.strip().lower()
            # Remove common prefixes
            for prefix in ['domain portfolio:', 'view-source:', 'fe-techteam/', 'd:\\downloads\\']:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]
            # Remove .com, .in, .org etc from end
            clean = re.sub(r'\.(com|in|org|net|io|co|dev|app|html|js|css)$', '', clean)
            # Split by hyphen, underscore, space, or dot
            parts = re.split(r'[-_\s./\\]+', clean)
            # Return first meaningful part (length >= 3)
            for part in parts:
                part = part.strip()
                if len(part) >= 3 and part.isalpha():
                    return part
            return clean

        # Filter valid projects
        # Browser projects (ending with "- Google Chrome", "- Microsoft Edge", etc.) get consolidated by root name
        # IDE/code projects stay separate as-is
        browser_suffixes = [' - google chrome', ' - microsoft edge', ' - microsoft\u200b edge',
                            ' - firefox', ' - brave', ' - opera']

        valid_projects = []
        for row in projects_query:
            project_name = row[0]
            if not project_name or not project_name.strip():
                continue
            name = project_name.strip()
            if is_browser_noise(name) or not is_valid_project_name(name):
                continue
            has_ide = int(row[5]) if row[5] else 0
            total_hours = float(row[2])

            # Check if this is a browser-tab project name
            is_browser_project = any(name.lower().endswith(s) for s in browser_suffixes)

            valid_projects.append({
                "name": name,
                "activity_count": row[1],
                "total_hours": total_hours,
                "has_ide": has_ide,
                "is_browser": is_browser_project
            })

        # Consolidate browser projects by root name, keep IDE projects separate
        consolidated = {}
        direct_projects = []

        for proj in valid_projects:
            if proj["is_browser"] and not proj["has_ide"]:
                root = extract_root_name(proj["name"])
                if root in consolidated:
                    consolidated[root]["activity_count"] += proj["activity_count"]
                    consolidated[root]["total_hours"] += proj["total_hours"]
                    if len(proj["name"]) < len(consolidated[root]["project_name"]):
                        consolidated[root]["project_name"] = proj["name"]
                else:
                    consolidated[root] = {
                        "project_name": proj["name"],
                        "activity_count": proj["activity_count"],
                        "total_hours": proj["total_hours"]
                    }
            else:
                direct_projects.append(proj)

        # Build final list
        projects = []
        # Add consolidated browser projects
        for root, data in consolidated.items():
            if data["total_hours"] >= 1.0:
                # Clean browser suffix from display name
                display_name = data["project_name"]
                for s in browser_suffixes:
                    if display_name.lower().endswith(s):
                        display_name = display_name[:len(display_name)-len(s)].strip()
                        break
                projects.append({
                    "project_name": display_name,
                    "activity_count": data["activity_count"],
                    "total_hours": round(data["total_hours"], 2)
                })
        # Add IDE/code projects directly
        for proj in direct_projects:
            if proj["total_hours"] >= 1.0:
                projects.append({
                    "project_name": proj["name"],
                    "activity_count": proj["activity_count"],
                    "total_hours": round(proj["total_hours"], 2)
                })

        # Sort by total hours descending
        projects.sort(key=lambda x: x["total_hours"], reverse=True)

        return {
            "projects": projects,
            "total_projects": len(projects),
            "date_range": None
        }

    except Exception as e:
        logger.error(f"Error getting all projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects")
async def add_project(
    project_name: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Add a new project to the projects table"""
    try:
        # Check if project already exists
        existing = db.execute(text("SELECT id FROM projects WHERE LOWER(name) = LOWER(:name)"), {"name": project_name}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Project already exists")

        # Insert new project
        db.execute(text("""
            INSERT INTO projects (name, description, is_active, created_at)
            VALUES (:name, :description, true, NOW())
        """), {"name": project_name, "description": description})
        db.commit()

        return {"message": f"Project '{project_name}' added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/projects/{project_name}")
async def delete_project(
    project_name: str,
    db: Session = Depends(get_db)
):
    """Delete (deactivate) a project"""
    try:
        db.execute(text("UPDATE projects SET is_active = false WHERE LOWER(name) = LOWER(:name)"), {"name": project_name})
        db.commit()
        return {"message": f"Project '{project_name}' deleted"}

    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/project/{project_name}/developers-time")
async def get_project_developers_time(
    project_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get developer-wise time breakdown for a specific project, grouped by date"""
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc) - timedelta(days=30)

        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)

        # Handle "Unassigned" project
        project_filter = "project_name IS NULL OR project_name = ''" if project_name == "Unassigned" else "project_name = :project_name"

        # Get developer-wise time breakdown for the project
        developers_query = db.execute(text(f"""
            SELECT
                ar.developer_id,
                d.name as developer_name,
                SUM(ar.duration) / 3600.0 as total_hours,
                COUNT(*) as activity_count,
                COUNT(DISTINCT DATE(ar.timestamp)) as days_worked,
                MIN(ar.timestamp) as first_activity,
                MAX(ar.timestamp) as last_activity
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            WHERE ({project_filter})
            AND ar.timestamp >= :start_date
            AND ar.timestamp <= :end_date
            GROUP BY ar.developer_id, d.name
            ORDER BY total_hours DESC
        """), {
            "project_name": project_name,
            "start_date": start,
            "end_date": end
        }).fetchall()

        # Get date-wise breakdown for each developer
        datewise_query = db.execute(text(f"""
            SELECT
                ar.developer_id,
                d.name as developer_name,
                DATE(ar.timestamp) as work_date,
                SUM(ar.duration) / 3600.0 as hours
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            WHERE ({project_filter})
            AND ar.timestamp >= :start_date
            AND ar.timestamp <= :end_date
            GROUP BY ar.developer_id, d.name, DATE(ar.timestamp)
            ORDER BY work_date DESC, hours DESC
        """), {
            "project_name": project_name,
            "start_date": start,
            "end_date": end
        }).fetchall()

        # Get overall total hours for the project within date range
        overall_query = db.execute(text(f"""
            SELECT
                COALESCE(SUM(ar.duration) / 3600.0, 0) as overall_hours,
                COUNT(DISTINCT DATE(ar.timestamp)) as overall_days
            FROM activity_records ar
            WHERE ({project_filter})
            AND ar.timestamp >= :start_date
            AND ar.timestamp <= :end_date
        """), {
            "project_name": project_name,
            "start_date": start,
            "end_date": end
        }).fetchone()

        overall_hours = round(float(overall_query[0]), 2) if overall_query else 0
        overall_days = overall_query[1] if overall_query else 0

        # Format developers data
        developers = []
        total_project_hours = 0

        for row in developers_query:
            dev_id, dev_name, total_hours, activity_count, days_worked, first_activity, last_activity = row
            total_project_hours += total_hours

            developers.append({
                "developer_id": dev_id,
                "developer_name": dev_name or dev_id,
                "total_hours": round(float(total_hours), 2),
                "activity_count": activity_count,
                "days_worked": days_worked,
                "average_hours_per_day": round(float(total_hours) / days_worked, 2) if days_worked > 0 else 0,
                "first_activity": first_activity.isoformat() if first_activity else None,
                "last_activity": last_activity.isoformat() if last_activity else None
            })

        # Calculate percentages
        for dev in developers:
            dev["percentage"] = round((dev["total_hours"] / total_project_hours * 100), 1) if total_project_hours > 0 else 0

        # Format date-wise data
        datewise_breakdown = {}
        for row in datewise_query:
            dev_id, dev_name, work_date, hours = row
            date_str = work_date.isoformat() if work_date else "Unknown"

            if date_str not in datewise_breakdown:
                datewise_breakdown[date_str] = []

            datewise_breakdown[date_str].append({
                "developer_id": dev_id,
                "developer_name": dev_name or dev_id,
                "hours": round(float(hours), 2)
            })

        return {
            "project_name": project_name,
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "summary": {
                "total_hours": round(total_project_hours, 2),
                "total_developers": len(developers),
                "total_days": len(datewise_breakdown),
                "overall_hours": overall_hours,
                "overall_days": overall_days
            },
            "developers": developers,
            "datewise_breakdown": datewise_breakdown
        }

    except Exception as e:
        logger.error(f"Error getting project developers time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/developer/{developer_id}/afk-summary")
async def get_developer_afk_summary(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get AFK (active vs away) summary for a developer — separate from productivity."""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc) - timedelta(days=7)
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)

        # Daily AFK breakdown
        daily_afk = db.execute(text("""
            SELECT
                DATE(timestamp) as work_date,
                SUM(duration) / 3600.0 as total_active_hours,
                COUNT(*) as event_count,
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event
            FROM afk_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            GROUP BY DATE(timestamp)
            ORDER BY work_date DESC
        """), {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()

        daily_stats = []
        total_active_hours = 0

        for row in daily_afk:
            work_date, active_hours, events, first_evt, last_evt = row
            # Span = time from first to last event
            span_hours = (last_evt - first_evt).total_seconds() / 3600.0 if first_evt and last_evt else 0
            away_hours = max(0, span_hours - float(active_hours))

            daily_stats.append({
                "date": work_date.isoformat() if work_date else None,
                "active_hours": round(float(active_hours), 2),
                "away_hours": round(away_hours, 2),
                "span_hours": round(span_hours, 2),
                "active_percentage": round((float(active_hours) / span_hours * 100) if span_hours > 0 else 0, 1),
                "event_count": events,
                "first_event": first_evt.isoformat() if first_evt else None,
                "last_event": last_evt.isoformat() if last_evt else None,
            })
            total_active_hours += float(active_hours)

        return {
            "developer_id": developer_id,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "total_active_hours": round(total_active_hours, 2),
            "total_days": len(daily_stats),
            "daily_breakdown": daily_stats
        }

    except Exception as e:
        logger.error(f"Error getting AFK summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
