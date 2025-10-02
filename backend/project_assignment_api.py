# API endpoints for manual project assignment
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import List, Dict, Optional
from datetime import datetime, timezone
from database import get_db
from models import Developer, ActivityRecord
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/developer/{developer_id}/activities-without-project")
async def get_activities_without_project(
    developer_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get activities that don't have project assigned"""
    try:
        # Get activities without projects
        activities = db.execute(text("""
            SELECT 
                id,
                application_name,
                window_title,
                duration,
                timestamp,
                category,
                url,
                file_path
            FROM activity_records
            WHERE developer_id = :dev_id
            AND (project_name IS NULL OR project_name = '')
            AND duration > 60  -- Only activities longer than 1 minute
            ORDER BY timestamp DESC
            LIMIT :limit
        """), {
            "dev_id": developer_id,
            "limit": limit
        }).fetchall()
        
        # Format activities
        unassigned_activities = []
        for row in activities:
            unassigned_activities.append({
                "id": row.id,
                "application_name": row.application_name,
                "window_title": row.window_title,
                "duration": row.duration,
                "duration_formatted": f"{row.duration / 3600:.2f}h",
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "category": row.category or "Other",
                "url": row.url,
                "file_path": row.file_path,
                "suggested_project": suggest_project_name(
                    row.window_title, 
                    row.application_name, 
                    row.file_path,
                    row.url
                )
            })
        
        return {
            "activities": unassigned_activities,
            "total": len(unassigned_activities)
        }
        
    except Exception as e:
        logger.error(f"Error getting unassigned activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/developer/{developer_id}/assign-project")
async def assign_project_to_activities(
    developer_id: str,
    request: Dict,
    db: Session = Depends(get_db)
):
    """Assign project name to multiple activities"""
    try:
        activity_ids = request.get("activity_ids", [])
        project_name = request.get("project_name", "").strip()
        project_type = request.get("project_type", "Development")
        
        if not activity_ids:
            raise HTTPException(status_code=400, detail="No activity IDs provided")
        
        if not project_name:
            raise HTTPException(status_code=400, detail="Project name is required")
        
        # Update activities
        updated = db.execute(text("""
            UPDATE activity_records
            SET project_name = :project_name,
                project_type = :project_type
            WHERE developer_id = :dev_id
            AND id = ANY(:activity_ids)
        """), {
            "dev_id": developer_id,
            "project_name": project_name,
            "project_type": project_type,
            "activity_ids": activity_ids
        }).rowcount
        
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated,
            "project_name": project_name,
            "project_type": project_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/developer/{developer_id}/project-suggestions")
async def get_project_suggestions(
    developer_id: str,
    db: Session = Depends(get_db)
):
    """Get list of existing projects for suggestions"""
    try:
        # Get existing project names
        projects = db.execute(text("""
            SELECT DISTINCT 
                project_name,
                project_type,
                COUNT(*) as usage_count,
                MAX(timestamp) as last_used
            FROM activity_records
            WHERE developer_id = :dev_id
            AND project_name IS NOT NULL
            GROUP BY project_name, project_type
            ORDER BY last_used DESC
            LIMIT 20
        """), {
            "dev_id": developer_id
        }).fetchall()
        
        suggestions = []
        for project, ptype, count, last_used in projects:
            suggestions.append({
                "name": project,
                "type": ptype,
                "usage_count": count,
                "last_used": last_used.isoformat() if last_used else None
            })
        
        # Add common project types
        project_types = [
            "Development",
            "Frontend",
            "Backend", 
            "Mobile",
            "Database",
            "Documentation",
            "Meeting",
            "Research",
            "Testing",
            "DevOps"
        ]
        
        return {
            "existing_projects": suggestions,
            "project_types": project_types
        }
        
    except Exception as e:
        logger.error(f"Error getting project suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def suggest_project_name(window_title, app_name, file_path, url):
    """Suggest a project name based on activity data"""
    import re
    
    if not window_title:
        return None
    
    # Try to extract from IDE window titles
    if app_name and any(ide in app_name.lower() for ide in ['vscode', 'cursor', 'code']):
        # Pattern: file - project - Visual Studio Code
        match = re.search(r'^(.+?)\s*-\s*(.+?)\s*-\s*(Visual Studio Code|Cursor|Code)', window_title)
        if match:
            return match.group(2).strip()
    
    # Try from file path
    if file_path:
        # Look for common project indicators
        patterns = [
            r'/([^/]+)/(src|app|lib|backend|frontend)/',
            r'\\([^\\]+)\\(src|app|lib|backend|frontend)\\'
        ]
        for pattern in patterns:
            match = re.search(pattern, file_path, re.IGNORECASE)
            if match:
                return match.group(1)
    
    # Try from URL
    if url and 'github.com' in url:
        match = re.search(r'github\.com/[^/]+/([^/\s]+)', url)
        if match:
            return match.group(1)
    
    return None


@router.post("/api/developer/{developer_id}/bulk-assign-similar")
async def bulk_assign_similar_activities(
    developer_id: str,
    request: Dict,
    db: Session = Depends(get_db)
):
    """Assign project to all similar activities based on pattern"""
    try:
        pattern = request.get("pattern", {})
        project_name = request.get("project_name", "").strip()
        project_type = request.get("project_type", "Development")
        
        if not project_name:
            raise HTTPException(status_code=400, detail="Project name is required")
        
        # Build query based on pattern
        query_parts = ["developer_id = :dev_id"]
        params = {
            "dev_id": developer_id,
            "project_name": project_name,
            "project_type": project_type
        }
        
        if pattern.get("application_name"):
            query_parts.append("application_name = :app_name")
            params["app_name"] = pattern["application_name"]
        
        if pattern.get("window_title_contains"):
            query_parts.append("window_title LIKE :title_pattern")
            params["title_pattern"] = f"%{pattern['window_title_contains']}%"
        
        if pattern.get("file_path_contains"):
            query_parts.append("file_path LIKE :path_pattern")
            params["path_pattern"] = f"%{pattern['file_path_contains']}%"
        
        # Update matching activities
        update_query = f"""
            UPDATE activity_records
            SET project_name = :project_name,
                project_type = :project_type
            WHERE {' AND '.join(query_parts)}
            AND (project_name IS NULL OR project_name = '')
        """
        
        updated = db.execute(text(update_query), params).rowcount
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated,
            "project_name": project_name,
            "pattern": pattern
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error bulk assigning project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
