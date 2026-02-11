# API endpoints for productivity and project analysis from database
from fastapi import APIRouter, Depends, HTTPException, Query
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
        
        # Get all developers with their productivity stats using weighted calculation
        developer_stats = db.execute(text("""
            SELECT 
                d.developer_id,
                d.name,
                COALESCE(SUM(ar.duration) / 3600.0, 0) as total_hours,
                COALESCE(SUM(
                    CASE 
                        WHEN ar.category = 'productive' THEN ar.duration * 0.95
                        WHEN ar.category = 'server' THEN ar.duration * 0.90
                        WHEN ar.category = 'browser' THEN ar.duration * 0.20
                        WHEN ar.category = 'non-work' THEN 0
                        ELSE ar.duration * 0.15
                    END
                ) / 3600.0, 0) as productive_hours,
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
            "end_date": end
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
    Only shows projects where at least one developer has spent more than 10 minutes (600 seconds) on that project."""
    try:
        import re

        # UPDATED: Include both productive AND browser categories, then merge by project_name
        # This captures browser-based work (like waaree.com, hdfc sales) that was previously hidden
        # FILTER: Only show projects where at least one developer spent more than 10 minutes (0.1667 hours)
        projects_query = db.execute(text("""
            SELECT
                project_name,
                SUM(activity_count) as activity_count,
                SUM(total_hours) as total_hours,
                COUNT(DISTINCT developer_id) as developer_count,
                SUM(active_days) as active_days
            FROM (
                SELECT
                    project_name,
                    developer_id,
                    COUNT(*) as activity_count,
                    SUM(duration) / 3600.0 as total_hours,
                    COUNT(DISTINCT DATE(timestamp)) as active_days
                FROM activity_records
                WHERE project_name IS NOT NULL
                AND project_name != ''
                AND LENGTH(project_name) >= 4
                AND category IN ('productive', 'browser')
                GROUP BY project_name, developer_id
                HAVING SUM(duration) / 3600.0 > 0.1667
            ) subq
            GROUP BY project_name
            ORDER BY total_hours DESC
        """)).fetchall()

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

            # REMOVED: Domain rejection - we want to keep work-related domains now
            # Domains are now allowed as they may represent actual work (waaree.com, hdfc, etc.)

            # COMPREHENSIVE file extension filtering
            file_extensions = [
                # Web/Frontend
                '.js', '.ts', '.jsx', '.tsx', '.vue', '.css', '.scss', '.sass', '.less',
                '.html', '.htm', '.xml', '.svg', '.blade',
                # Backend/Server
                '.py', '.php', '.java', '.rb', '.go', '.rs', '.c', '.cpp', '.cs', '.h',
                '.aspx', '.asp',
                # Config/Data
                '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.env',
                '.lock', '.log', '.bak', '.tmp', '.cache',
                # Documents
                '.md', '.txt', '.doc', '.docx', '.pdf', '.rtf',
                # Media
                '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp',
                # Executables
                '.sh', '.bat', '.cmd', '.ps1', '.exe', '.dll', '.so',
                # Database
                '.sql', '.db', '.sqlite',
                # Archives
                '.zip', '.tar', '.gz', '.rar', '.7z',
                # Office
                '.xls', '.xlsx', '.xlsm', '.csv',
                # Crypto/Keys
                '.pem', '.key', '.crt', '.cer', '.p12', '.pfx',
                # Git
                '.git', '.gitignore', '.dockerignore'
            ]
            if any(name_lower.endswith(ext) for ext in file_extensions):
                return False

            # Reject double underscores
            if '__' in name:
                return False

            # Reject common page/action names
            page_names = [
                'login', 'logout', 'signin', 'signout', 'register', 'signup',
                'home', 'dashboard', 'profile', 'settings', 'admin',
                'success', 'error', '404', '403', '500',
                'customers', 'customer', 'users', 'user', 'products', 'product',
                'orders', 'order', 'items', 'item'
            ]
            if name_lower in page_names:
                return False

            # Reject application names
            app_names = [
                'meet', 'zoom', 'teams', 'skype', 'slack',
                'termius', 'putty', 'winscp'
            ]
            if name_lower in app_names:
                return False

            # Reject patterns ending with specific words
            if re.search(r'(form|password|managment|management)$', name_lower):
                return False
            if any(x in name_lower for x in ['futures', 'index live', 'messaged', 'asset']):
                return False

            # Reject patterns starting with action verbs
            if re.match(r'^(get |create |download |import |generate |call to |update |register )', name_lower):
                return False

            # Reject patterns with parentheses (usually duplicates or system artifacts)
            if '(' in name or ')' in name:
                return False

            # Reject patterns that look like URLs/links (share-*, view-*, etc.)
            if re.match(r'^(share|view|store|contact|change|forgot|update)-', name_lower):
                return False

            # Reject build/dist folders
            if name_lower.startswith(('dist', 'build', 'node_modules')):
                return False

            # Comprehensive exclusion list
            excluded = {
                'web browsing', 'ide work', 'database work', 'api development',
                'filezilla/ftp', 'cpanel/hosting', 'unknown', 'general',
                'system32', 'windows', 'desktop', 'documents', 'downloads', 'downlaods',
                'program', 'settings', 'extensions', 'terminal', 'output',
                'debug', 'problems', 'console', 'welcome', 'untitled',
                'inbox', 'drafts', 'sent', 'trash', 'spam',
                'google', 'gmail', 'outlook', 'yahoo', 'chrome', 'firefox', 'edge',
                'termius', 'meet', 'login', 'logout', 'profile', 'home', 'dashboard',
                'success', 'error', 'customers', 'users', 'products', 'orders',
                'bitcoin', 'scratches', 'startup', 'runner', 'minimalist',
                'authentication', 'overview', 'nav', 'keyfiles', 'backend', 'frontend',
                'components', 'validation', 'projects', 'activitywatch',
                'contact-form-lead', 'share-single-url', 'share-folder-url',
                'view-single-doc', 'store-collaterals', 'collaterals',
                'change-password', 'forgot-password', 'update-profile',
                'marketing-support', 'registration', 'xampp', 'htdocs', 'assets',
                'opening', 'filters', 'coll', 'solution', 'solution1', 'claude',
                'tradingview', 'navandidcw', 'src', 'dist', 'build', 'public',
                'static', 'images', 'uploads', 'temp', 'tmp',
                'activitywatch sync', 'activitywatch sync setup', 'new tab',
                'login form', 'change password', 'profile managment', 'register broker',
                'validation error', 'javascript quiz data reference error', 'all indices'
            }

            if name_lower in excluded:
                return False

            # REMOVED: URL-like pattern rejection
            # We now allow domains like waaree.com, hdfc.in as they represent actual work
            # The is_browser_noise() function already filters out non-work websites

            # Must start with alphanumeric
            if not name[0].isalnum():
                return False

            return True

        projects = []
        rejected = []
        browser_noise_count = 0
        for row in projects_query:
            project_name = row[0]
            # Debug: Check if email subjects are being filtered
            if 'payment' in project_name.lower() or 'notification' in project_name.lower() or 'statement' in project_name.lower():
                is_noise = is_browser_noise(project_name)
                logger.info(f"DEBUG: '{project_name}' -> is_browser_noise={is_noise}")
                if is_noise:
                    browser_noise_count += 1

            if is_valid_project_name(project_name):
                projects.append({
                    "project_name": project_name.strip(),
                    "activity_count": row[1],
                    "total_hours": round(float(row[2]), 2)
                })
            else:
                rejected.append(project_name)

        logger.info(f"All projects: total from DB={len(projects_query)}, valid={len(projects)}, rejected={len(rejected)}")
        logger.info(f"Rejected project names: {rejected[:50]}")

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

        # Get overall/all-time total hours for the project (no date filter)
        overall_query = db.execute(text(f"""
            SELECT
                COALESCE(SUM(ar.duration) / 3600.0, 0) as overall_hours,
                COUNT(DISTINCT DATE(ar.timestamp)) as overall_days
            FROM activity_records ar
            WHERE ({project_filter})
        """), {
            "project_name": project_name
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
