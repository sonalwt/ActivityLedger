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

# Define productive applications/categories...
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
MIN_WORKING_DAY_HOURS = 2.0


def _resolve_project_period(period: str, start_date_str: Optional[str], end_date_str: Optional[str]):
    """Resolve period string to (start, end) datetime range for project endpoints."""
    today = date.today()
    now = datetime.now(timezone.utc)

    if period == "custom" and start_date_str and end_date_str:
        start = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        # Ensure end covers full day
        if end.hour == 0 and end.minute == 0:
            end = end.replace(hour=23, minute=59, second=59)
    elif period == "current_week":
        # Monday of current week
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
        end = now
    elif period == "last_week":
        # Monday to Sunday of previous week
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        start = datetime(last_monday.year, last_monday.month, last_monday.day, tzinfo=timezone.utc)
        end = datetime(last_sunday.year, last_sunday.month, last_sunday.day,
                      23, 59, 59, tzinfo=timezone.utc)
    elif period == "last_month":
        first_of_this_month = date(today.year, today.month, 1)
        last_month_end = first_of_this_month - timedelta(days=1)
        start = datetime(last_month_end.year, last_month_end.month, 1, tzinfo=timezone.utc)
        end = datetime(last_month_end.year, last_month_end.month, last_month_end.day,
                      23, 59, 59, tzinfo=timezone.utc)
    elif period == "3_months":
        start = datetime(today.year, today.month, 1, tzinfo=timezone.utc) - timedelta(days=90)
        start = start.replace(day=1, hour=0, minute=0, second=0)
        end = now
    elif period == "current_year":
        start = datetime(today.year, 1, 1, tzinfo=timezone.utc)
        end = now
    elif period == "last_year":
        start = datetime(today.year - 1, 1, 1, tzinfo=timezone.utc)
        end = datetime(today.year - 1, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:  # current_month (default)
        start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
        end = now

    return start, end


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
    """Calculate productivity hours for a developer (AFK-aware)"""
    try:
        from afk_helpers import (fetch_afk_data_single,
                                 compute_adjusted_duration, PRODUCTIVE_CATEGORIES)
        from collections import defaultdict

        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc) - timedelta(days=7)

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

        # Fetch all activities for this developer in the date range
        activities = db.execute(text("""
            SELECT id, application_name, category, duration, timestamp, window_title
            FROM activity_records
            WHERE developer_id = :dev_id
              AND timestamp >= :start_date
              AND timestamp <= :end_date
            ORDER BY timestamp ASC
        """), {"dev_id": developer_id, "start_date": start, "end_date": end}).fetchall()

        # Fetch AFK data for this developer
        afk_data = fetch_afk_data_single(db, developer_id, start, end)

        # --- Compute daily productivity with AFK-adjusted durations ---
        daily_data = defaultdict(lambda: {
            "total": 0.0, "productive": 0.0,
            "apps": set(), "count": 0
        })
        # Hourly distribution
        hourly_data = defaultdict(float)
        # App usage
        app_data = defaultdict(lambda: {"hours": 0.0, "count": 0, "category": None})

        for row in activities:
            raw_dur = row.duration or 0
            if raw_dur <= 0:
                continue

            adj_dur = compute_adjusted_duration(
                row.timestamp, raw_dur, row.application_name,
                afk_data.not_afk_intervals, afk_data.all_afk_intervals
            )

            ts = row.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            day_key = ts.date()
            hour_key = ts.hour

            daily_data[day_key]["total"] += adj_dur
            daily_data[day_key]["count"] += 1
            daily_data[day_key]["apps"].add(row.application_name)
            cat = (row.category or "").lower()
            if cat in PRODUCTIVE_CATEGORIES:
                daily_data[day_key]["productive"] += adj_dur

            hourly_data[hour_key] += adj_dur

            app_key = row.application_name or "Unknown"
            app_data[app_key]["hours"] += adj_dur
            app_data[app_key]["count"] += 1
            if app_data[app_key]["category"] is None:
                app_data[app_key]["category"] = row.category

        # Format daily stats (only days with > 2h total)
        daily_stats = []
        total_work_hours = 0.0
        total_productive_hours = 0.0

        for day_key in sorted(daily_data.keys(), reverse=True):
            d = daily_data[day_key]
            total_h = d["total"] / 3600.0
            if total_h <= 2:
                continue
            prod_h = d["productive"] / 3600.0
            # Use max(total_working_hours, 8h) as denominator
            denominator_h = max(total_h, DAILY_TARGET_HOURS)
            pct = min(100.0, (prod_h / denominator_h * 100)) if denominator_h > 0 else 0

            daily_stats.append({
                "date": day_key.isoformat(),
                "total_hours": round(total_h, 2),
                "productive_hours": round(prod_h, 2),
                "productivity_percentage": round(pct, 1),
                "apps_used": len(d["apps"]),
                "total_activities": d["count"]
            })
            total_work_hours += total_h
            total_productive_hours += prod_h

        # Format hourly distribution
        hourly_stats = [
            {"hour": h, "hours": round(hourly_data[h] / 3600.0, 2)}
            for h in sorted(hourly_data.keys())
        ]

        # Format app usage (top 20)
        sorted_apps = sorted(app_data.items(), key=lambda x: x[1]["hours"], reverse=True)[:20]
        app_stats = [{
            "application": app_name,
            "category": info["category"] or "Other",
            "hours": round(info["hours"] / 3600.0, 2),
            "usage_count": info["count"],
            "is_productive": (info["category"] or "").lower() in PRODUCTIVE_CATEGORIES
        } for app_name, info in sorted_apps]

        # Overall productivity: sum of per-day max(tracked, 8h) as denominator
        total_denominator_hours = 0.0
        for day_key in sorted(daily_data.keys()):
            d = daily_data[day_key]
            day_h = d["total"] / 3600.0
            if day_h <= 2:
                continue
            total_denominator_hours += max(day_h, DAILY_TARGET_HOURS)
        overall_productivity = min(100.0, (total_productive_hours / total_denominator_hours * 100)) if total_denominator_hours > 0 else 0
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
    """Get productivity summary for all developers (AFK-adjusted)"""
    try:
        from afk_helpers import (
            fetch_afk_data_bulk, compute_adjusted_duration,
            PRODUCTIVE_CATEGORIES, BROWSER_APPS, MAX_SINGLE_EVENT_DURATION
        )
        from collections import defaultdict

        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)

        # 1. Fetch developer metadata (projects, activity count, last activity)
        meta_query = text("""
            SELECT
                d.developer_id,
                d.name,
                COALESCE(ds.projects_worked, 0) AS projects_worked,
                COALESCE(ds.total_activities, 0) AS total_activities,
                la.last_activity
            FROM developers d
            LEFT JOIN (
                SELECT
                    developer_id,
                    COUNT(DISTINCT project_name) AS projects_worked,
                    COUNT(id) AS total_activities
                FROM activity_records
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                GROUP BY developer_id
            ) ds ON ds.developer_id = d.developer_id
            LEFT JOIN (
                SELECT developer_id, MAX(timestamp) AS last_activity
                FROM activity_records
                GROUP BY developer_id
            ) la ON la.developer_id = d.developer_id
            WHERE d.active = true
            ORDER BY d.name
        """)
        dev_meta_rows = db.execute(meta_query, {
            "start_date": start, "end_date": end
        }).fetchall()

        # 2. Fetch all activity records for the date range
        activity_query = text("""
            SELECT developer_id, category, duration, timestamp, application_name
            FROM activity_records
            WHERE timestamp >= :start_date AND timestamp <= :end_date
            ORDER BY developer_id, timestamp ASC
        """)
        activity_rows = db.execute(activity_query, {
            "start_date": start, "end_date": end
        }).fetchall()

        # Group activities by developer
        activities_by_dev = defaultdict(list)
        for row in activity_rows:
            activities_by_dev[row.developer_id].append(row)

        # 3. Fetch AFK data for all developers in one query
        afk_data_map = fetch_afk_data_bulk(db, start, end)

        # 4. Process each developer with AFK-adjusted durations
        developers = []
        for meta in dev_meta_rows:
            dev_id = meta.developer_id
            name = meta.name
            projects = meta.projects_worked
            activities = meta.total_activities
            last_activity = meta.last_activity

            dev_activities = activities_by_dev.get(dev_id, [])
            afk_data = afk_data_map.get(dev_id)
            not_afk_intervals = afk_data.not_afk_intervals if afk_data else []
            all_afk_intervals = afk_data.all_afk_intervals if afk_data else []

            # Compute not-afk seconds per day (actual keyboard time)
            not_afk_per_day = defaultdict(float)
            for (naf_start, naf_end) in not_afk_intervals:
                day_key = naf_start.date()
                not_afk_per_day[day_key] += (naf_end - naf_start).total_seconds()

            # Per-day accumulation with AFK-adjusted durations
            daily = defaultdict(lambda: {"total": 0.0, "productive": 0.0, "activity_count": 0})

            for act_row in dev_activities:
                raw_dur = act_row.duration or 0
                if raw_dur <= 0:
                    continue

                adj_dur = compute_adjusted_duration(
                    act_row.timestamp, raw_dur, act_row.application_name,
                    not_afk_intervals, all_afk_intervals
                )

                ts = act_row.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                day_key = ts.date()

                daily[day_key]["total"] += adj_dur
                daily[day_key]["activity_count"] += 1
                cat = (act_row.category or "").lower()
                if cat not in ('entertainment', 'non-work'):
                    daily[day_key]["productive"] += adj_dur

            # Cap daily totals at not-afk time to prevent double-counting
            # from overlapping concurrent activities
            for day_key, stats in daily.items():
                cap = not_afk_per_day.get(day_key, 0)
                if cap > 0:
                    stats["total"] = min(stats["total"], cap)
                    stats["productive"] = min(stats["productive"], cap)
                else:
                    # No AFK data = no proof user was at keyboard. Zero out.
                    stats["total"] = 0.0
                    stats["productive"] = 0.0
                    stats["activity_count"] = 0

            # Aggregate across days (include if developer had any activities)
            total_seconds = 0.0
            productive_seconds = 0.0
            denom_seconds = 0.0
            active_days = 0
            filtered_activity_count = 0

            for day_key, stats in daily.items():
                if stats["activity_count"] == 0:
                    continue
                active_days += 1
                total_seconds += stats["total"]
                productive_seconds += stats["productive"]
                filtered_activity_count += stats["activity_count"]
                denom_seconds += max(stats["total"], DAILY_TARGET_HOURS * 3600)

            total_hours = total_seconds / 3600.0
            productive_hours = productive_seconds / 3600.0
            productivity_percentage = min(100.0, (productive_seconds / denom_seconds * 100)) if denom_seconds > 0 else 0.0

            # Determine status based on last activity
            status = "offline"
            if last_activity:
                if hasattr(last_activity, 'replace'):
                    time_diff = datetime.now(timezone.utc) - last_activity.replace(tzinfo=timezone.utc)
                else:
                    time_diff = datetime.now(timezone.utc) - last_activity
                if time_diff.total_seconds() < 1800:
                    status = "online"
                elif time_diff.total_seconds() < 86400:
                    status = "idle"

            developers.append({
                "developer_id": dev_id,
                "name": name,
                "total_hours": round(total_hours, 2),
                "productive_hours": round(productive_hours, 2),
                "productivity_percentage": round(productivity_percentage, 1),
                "active_days": active_days,
                "projects_count": projects,
                "activities_count": filtered_activity_count,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "status": status
            })

        # Sort by productive hours descending
        developers.sort(key=lambda d: d["productive_hours"], reverse=True)

        # Calculate team statistics
        team_total_hours = sum(d["total_hours"] for d in developers)
        team_productive_hours = sum(d["productive_hours"] for d in developers)
        active_developers = sum(1 for d in developers if d["status"] == "online")
        developers_with_activity = [d for d in developers if d["productive_hours"] > 0]

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


def _is_browser_server_noise(name: str) -> bool:
    """Filter out browser/server noise that is not a real project."""
    import re
    if not name:
        return True
    nl = name.lower().strip()

    # Application/tool names — not projects
    app_names = {
        'google chrome', 'microsoft edge', 'firefox', 'brave', 'opera',
        'termius', 'putty', 'mobaxterm', 'winscp',
        'notepad', 'notepad++', 'claude', 'chatgpt', 'copilot',
        'microsoft sql server management studio', 'anydesk', 'youtube',
        'whatsapp', 'instagram', 'facebook', 'twitter', 'telegram',
        'mysql workbench', 'program manager', 'excel', 'onvue',
    }
    if nl in app_names:
        return True

    # Generic browser/email/system noise
    noise_patterns = [
        'new tab', 'blank', 'google search', 'google sheets', 'google slides',
        'google drive', 'google docs', 'google chrome', 'microsoft edge',
        'first economy mail', 'radiant mail', 'radiant-mail',
        'notification center', 'download collateral', 'fetch all',
        'attendance detail', 'scheme list', 'scheme edit', 'ga data sheet',
        'scrum board', 'latest data required', 'screen lock', 'lock screen',
        'windows default', 'sign-in', 'task manager', 'file explorer',
        'inbox', 'sent mail', 'draft', 'spam', 'trash',
        'regular growth', 'search result', 'open file',
        'google keep', 'snipping tool', 'windows shell',
    ]
    if any(p in nl for p in noise_patterns):
        return True

    # SQL query files (SQLQuery1.sql, etc.)
    if re.match(r'^sqlquery\d', nl):
        return True

    # Drive letters (d:, c:)
    if re.match(r'^[a-z]:$', nl):
        return True

    # Person names: "Firstname Lastname" pattern
    if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', name) and len(name) < 25:
        return True

    # Action verb prefixes
    if re.match(r'^(get |create |download |import |generate |update |register |call to )', nl):
        return True

    # File extensions (except domain names like .com, .in)
    if re.search(r'\.\w{1,5}$', nl) and not re.search(r'\.(com|in|org|net|io|co)$', nl):
        return True

    # URLs or file paths
    if nl.startswith('http') or '/' in name or '\\' in name:
        return True

    # Inbox with count — "Inbox (6)", "Inbox (14)"
    if re.search(r'\(\d+\)', name):
        return True

    return False


def _auto_insert_projects_on_load(db: Session):
    """
    Auto-insert qualifying projects into the projects table on dashboard load.
    Considers three types of work:
      - IDE/editor work (dev editor apps) — threshold: >2 hours
      - Server work (category: server) — threshold: >3 hours
      - Browser work (category: browser) — threshold: >5 hours + at least 2 developers
    Projects must pass name validation and not already exist in the projects table.
    """
    from project_auto_insert import _is_valid_project_name, DEV_EDITOR_NAMES
    from sqlalchemy.exc import IntegrityError

    # Build LIKE conditions for dev editors (substring match)
    editor_like_conditions = " OR ".join(
        f"LOWER(ar.application_name) LIKE '%{e}%'" for e in DEV_EDITOR_NAMES
    )

    try:
        # Get per-project hours split by work type (IDE, server, browser)
        candidates_query = text(f"""
            SELECT
                ar.project_name,
                COALESCE(SUM(ar.duration), 0) / 3600.0 as total_hours,
                COALESCE(SUM(CASE WHEN ({editor_like_conditions})
                    THEN ar.duration ELSE 0 END), 0) / 3600.0 as ide_hours,
                COALESCE(SUM(CASE WHEN ar.category = 'server'
                    THEN ar.duration ELSE 0 END), 0) / 3600.0 as server_hours,
                COALESCE(SUM(CASE WHEN ar.category = 'browser'
                    THEN ar.duration ELSE 0 END), 0) / 3600.0 as browser_hours,
                COUNT(DISTINCT ar.developer_id) as dev_count
            FROM activity_records ar
            WHERE ar.project_name IS NOT NULL
              AND ar.project_name != ''
              AND LENGTH(ar.project_name) > 4
              AND ar.category IN ('productive', 'coding', 'server', 'browser')
              AND NOT EXISTS (
                  SELECT 1 FROM projects p
                  WHERE LOWER(p.name) = LOWER(ar.project_name)
              )
            GROUP BY ar.project_name
        """)

        candidates = db.execute(candidates_query).fetchall()

        inserted_count = 0
        for row in candidates:
            project_name = row[0]
            total_hours = float(row[1])
            ide_hours = float(row[2])
            server_hours = float(row[3])
            browser_hours = float(row[4])
            dev_count = int(row[5])

            # Check thresholds by work type
            source = ''
            if ide_hours > 2.0:
                source = f"IDE {ide_hours:.1f}h"
            elif server_hours > 3.0:
                source = f"Server {server_hours:.1f}h"
            elif browser_hours > 5.0 and dev_count >= 2:
                source = f"Browser {browser_hours:.1f}h, {dev_count} devs"
            else:
                continue

            # Name validation (excluded folders, generic names)
            if not _is_valid_project_name(project_name):
                continue

            # Browser/server noise filter (app names, person names, etc.)
            if _is_browser_server_noise(project_name):
                continue

            try:
                nested = db.begin_nested()
                new_project = Project(
                    name=project_name,
                    description=f"Auto-added ({source})",
                    is_active=True
                )
                db.add(new_project)
                db.flush()

                inserted_count += 1
                logger.info(f"Dashboard auto-inserted project '{project_name}' (id={new_project.id}, {source})")
            except IntegrityError:
                nested.rollback()
                continue

        if inserted_count > 0:
            db.commit()
            logger.info(f"Dashboard auto-inserted {inserted_count} new project(s)")

        # Update activity_records project_id for all active projects
        # Covers newly inserted projects AND existing projects with stale/missing project_id
        update_query = text("""
            UPDATE activity_records ar
            SET project_id = p.id
            FROM projects p
            WHERE p.is_active = true
              AND LOWER(ar.project_name) = LOWER(p.name)
              AND (ar.project_id IS NULL OR ar.project_id != p.id)
        """)
        result = db.execute(update_query)
        if result.rowcount > 0:
            db.commit()
            logger.info(f"Updated project_id for {result.rowcount} activity records")

    except Exception as e:
        logger.error(f"Error in auto-insert projects on load: {e}")
        # Don't fail the dashboard load if auto-insert fails
        try:
            db.rollback()
        except Exception:
            pass


@router.get("/api/all-projects")
async def get_all_projects(
    period: str = Query("current_month",
        description="Filter: current_month, last_month, current_year, last_year, custom"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    developer_ids: Optional[str] = Query(None, description="Comma-separated developer IDs to filter projects"),
    db: Session = Depends(get_db)
):
    """Get list of projects from the projects table with aggregated hours from activity_records."""
    try:
        from datetime import datetime, timezone

        # Auto-insert qualifying projects before fetching
        _auto_insert_projects_on_load(db)

        # Resolve date range from period
        start, end = _resolve_project_period(period, start_date, end_date)

        # Build date filter for activity aggregation
        date_filter = ""
        query_params = {}
        if start and end:
            date_filter = "AND ar.timestamp >= :start_date AND ar.timestamp <= :end_date"
            query_params = {"start_date": start, "end_date": end}

        # Developer filter
        dev_filter = ""
        if developer_ids:
            dev_id_list = [d.strip() for d in developer_ids.split(",") if d.strip()]
            if dev_id_list:
                placeholders = ", ".join([f":dev_{i}" for i in range(len(dev_id_list))])
                dev_filter = f"AND ar.developer_id::VARCHAR IN ({placeholders})"
                for i, did in enumerate(dev_id_list):
                    query_params[f"dev_{i}"] = did

        # Excluded project names (noise/non-project entries)
        excluded_names = {'scripts', 'ide work', 'mails', 'general', 'unknown', '',
                          'data', 'home', 'desktop', 'documents', 'downloads',
                          'users', 'temp', 'tmp', 'system', 'windows', 'program files',
                          'appdata', 'local', 'roaming', 'new tab', 'google', 'settings',
                          'dia', 'terminal', 'console', 'finder', 'postman', 'gmail',
                          'cursor', 'code', 'calendar', 'preview', 'file', 'pdf'}

        # Build blacklist window_title filter from the existing categorizer blacklist
        from activity_categorizer import get_categorizer
        _blacklisted = [s for s in get_categorizer().blacklisted_browser_sites if s and "'" not in s]
        blacklist_filter = " AND ".join(
            f"LOWER(ar.window_title) NOT LIKE '%{s}%'" for s in _blacklisted
        ) if _blacklisted else "1=1"

        # Query from activity_records directly, LEFT JOIN projects for metadata.
        # Use LOWER(ar.project_name) to merge case variations (e.g. "Mahindra" vs "mahindra").
        projects_query = db.execute(text(f"""
            SELECT
                LOWER(ar.project_name) as project_key,
                MAX(ar.project_name) as project_name,
                MAX(p.id) as project_id,
                MAX(p.description) as description,
                COALESCE(MAX(p.total_cost), 0) as total_cost,
                COALESCE(SUM(ar.duration) / 3600.0, 0) as total_hours,
                COALESCE(COUNT(ar.id), 0) as activity_count,
                COUNT(DISTINCT ar.developer_id) as developer_count
            FROM activity_records ar
            LEFT JOIN projects p ON (ar.project_id = p.id OR (ar.project_id IS NULL AND LOWER(ar.project_name) = LOWER(p.name)))
            WHERE ar.project_name IS NOT NULL
                AND ar.project_name != ''
                AND ar.project_name != 'general'
                AND ar.category != 'non-work'
                AND {blacklist_filter}
                {date_filter}
                {dev_filter}
            GROUP BY LOWER(ar.project_name)
            HAVING SUM(ar.duration) > 1800
            ORDER BY total_hours DESC
        """), query_params).fetchall()

        projects = []
        for row in projects_query:
            pname = row[1]  # MAX(ar.project_name) - original casing
            # Skip excluded project names
            if pname and pname.lower() in excluded_names:
                continue
            # Skip very short names (likely noise from path extraction)
            if pname and len(pname) <= 2:
                continue
            projects.append({
                "project_id": row[2],
                "project_name": pname,
                "description": row[3],
                "total_cost": round(float(row[4]), 2) if row[4] else 0,
                "total_hours": round(float(row[5]), 2),
                "activity_count": row[6],
                "developer_count": row[7]
            })

        return {
            "projects": projects,
            "total_projects": len(projects),
            "date_range": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None}
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


@router.put("/api/developer/{developer_id}/hourly-cost")
async def update_developer_hourly_cost(
    developer_id: str,
    hourly_cost: float = Query(..., description="Hourly cost for the developer"),
    db: Session = Depends(get_db)
):
    """Update hourly cost for a developer"""
    try:
        developer = db.query(Developer).filter(Developer.developer_id == developer_id).first()
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        developer.hourly_cost = hourly_cost
        db.commit()
        return {"success": True, "developer_id": developer_id, "hourly_cost": hourly_cost}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating developer hourly cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/projects/{project_name}/total-cost")
async def update_project_total_cost(
    project_name: str,
    total_cost: float = Query(..., description="Total cost/budget for the project"),
    db: Session = Depends(get_db)
):
    """Update total cost for a project"""
    try:
        result = db.execute(
            text("UPDATE projects SET total_cost = :cost WHERE LOWER(name) = LOWER(:name) AND is_active = true"),
            {"cost": total_cost, "name": project_name}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        db.commit()
        return {"success": True, "project_name": project_name, "total_cost": total_cost}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project total cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/project/{project_name}/developers-time")
async def get_project_developers_time(
    project_name: str,
    period: str = Query("current_month",
        description="Filter: current_month, last_month, current_year, last_year, custom"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get developer-wise time breakdown for a specific project, grouped by date"""
    try:
        # Resolve date range from period
        start, end = _resolve_project_period(period, start_date, end_date)

        # Look up project_id and total_cost from projects table
        project_row = db.execute(text("SELECT id, COALESCE(total_cost, 0) FROM projects WHERE LOWER(name) = LOWER(:name) AND is_active = true"), {"name": project_name}).fetchone()
        project_id = project_row[0] if project_row else None
        project_total_cost = float(project_row[1]) if project_row else 0

        # Handle "Unassigned" project
        # Match on both project_id and project_name to capture browser activities
        # (browser activities have project_name set but project_id is NULL)
        if project_name == "Unassigned":
            project_filter = "ar.project_id IS NULL AND (ar.project_name IS NULL OR ar.project_name = '')"
        elif project_id:
            project_filter = "(ar.project_id = :project_id OR (ar.project_id IS NULL AND LOWER(ar.project_name) = LOWER(:project_name_str)))"
        else:
            project_filter = "LOWER(ar.project_name) = LOWER(:project_name_str)"

        query_params = {
            "project_id": project_id,
            "project_name_str": project_name,
            "start_date": start,
            "end_date": end
        }

        # Get developer-wise time breakdown for the project
        developers_query = db.execute(text(f"""
            SELECT
                ar.developer_id,
                d.name as developer_name,
                SUM(ar.duration) / 3600.0 as total_hours,
                COUNT(*) as activity_count,
                COUNT(DISTINCT DATE(ar.timestamp)) as days_worked,
                MIN(ar.timestamp) as first_activity,
                MAX(ar.timestamp) as last_activity,
                COALESCE(d.hourly_cost, 0) as hourly_cost
            FROM activity_records ar
            LEFT JOIN developers d ON ar.developer_id = d.developer_id
            WHERE ({project_filter})
            AND ar.timestamp >= :start_date
            AND ar.timestamp <= :end_date
            GROUP BY ar.developer_id, d.name, d.hourly_cost
            ORDER BY total_hours DESC
        """), query_params).fetchall()

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
        """), query_params).fetchall()

        # Get overall total hours for the project within date range
        # Overall hours = ALL time invested in project (no date filter)
        overall_query = db.execute(text(f"""
            SELECT
                COALESCE(SUM(ar.duration) / 3600.0, 0) as overall_hours,
                COUNT(DISTINCT DATE(ar.timestamp)) as overall_days
            FROM activity_records ar
            WHERE ({project_filter})
        """), {"project_id": project_id, "project_name_str": project_name}).fetchone()

        overall_hours = round(float(overall_query[0]), 2) if overall_query else 0
        overall_days = overall_query[1] if overall_query else 0

        # Lifetime resource cost = all-time hours per developer * their hourly rate
        lifetime_cost_query = db.execute(text(f"""
            SELECT
                COALESCE(SUM((ar_hours.total_hours) * COALESCE(d.hourly_cost, 0)), 0) as lifetime_cost
            FROM (
                SELECT ar.developer_id, SUM(ar.duration) / 3600.0 as total_hours
                FROM activity_records ar
                WHERE ({project_filter})
                GROUP BY ar.developer_id
            ) ar_hours
            LEFT JOIN developers d ON ar_hours.developer_id = d.developer_id
        """), {"project_id": project_id, "project_name_str": project_name}).fetchone()

        lifetime_resource_cost = round(float(lifetime_cost_query[0]), 2) if lifetime_cost_query else 0

        # Format developers data
        developers = []
        total_project_hours = 0

        total_resource_cost = 0
        for row in developers_query:
            dev_id, dev_name, total_hours, activity_count, days_worked, first_activity, last_activity, hourly_cost = row
            total_project_hours += total_hours
            dev_cost = round(float(total_hours) * float(hourly_cost), 2)
            total_resource_cost += dev_cost

            developers.append({
                "developer_id": dev_id,
                "developer_name": dev_name or dev_id,
                "total_hours": round(float(total_hours), 2),
                "hourly_cost": float(hourly_cost),
                "resource_cost": dev_cost,
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
            "period": period,
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "summary": {
                "total_hours": round(total_project_hours, 2),
                "total_developers": len(developers),
                "total_days": len(datewise_breakdown),
                "overall_hours": overall_hours,
                "overall_days": overall_days,
                "total_cost": round(project_total_cost, 2),
                "resource_cost": lifetime_resource_cost
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
