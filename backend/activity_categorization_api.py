# activity_categorization_api.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Optional, List, Dict
from database import get_db
from activity_categorizer import ActivityCategorizer
import json

router = APIRouter()

@router.get("/api/activity-categories/{developer_id}")
async def get_categorized_activities(
    developer_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get activities categorized into Productive, Browser, and Server categories"""
    try:
        # Initialize categorizer
        categorizer = ActivityCategorizer()
        
        # Parse dates or use defaults
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Fetch activities from database
        query = text("""
            SELECT *
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
            ORDER BY timestamp DESC
        """)
        
        result = db.execute(query, {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        # Categorize activities
        activities_by_category = {
            "productive": [],
            "browser": [],
            "server": [],
            "uncategorized": [],
            "non-work": []
        }
        
        category_stats = {
            "productive": {"count": 0, "duration": 0},
            "browser": {"count": 0, "duration": 0},
            "server": {"count": 0, "duration": 0},
            "uncategorized": {"count": 0, "duration": 0},
            "non-work": {"count": 0, "duration": 0}
        }
        
        total_duration = 0
        
        for row in result:
            activity = {
                "id": row[0],
                "developer_id": row[1],
                "application_name": row[2] or "",
                "window_title": row[3] or "",
                "duration": row[4] or 0,
                "timestamp": row[5].isoformat() if row[5] else None,
                "url": row[6],
                "file_path": row[7],
                "project_name": row[8],
                "project_type": row[9],
                "existing_category": row[10]
            }
            
            # Get categorization
            category_info = categorizer.get_detailed_category(
                activity["window_title"],
                activity["application_name"]
            )
            
            activity["new_category"] = category_info["category"]
            activity["subcategory"] = category_info["subcategory"]
            activity["confidence"] = category_info["confidence"]
            
            # Add to appropriate category list
            category = category_info["category"]
            activities_by_category[category].append(activity)
            
            # Update statistics
            category_stats[category]["count"] += 1
            category_stats[category]["duration"] += activity["duration"]
            total_duration += activity["duration"]
        
        # Calculate percentages
        for category in category_stats:
            if total_duration > 0:
                category_stats[category]["percentage"] = (
                    category_stats[category]["duration"] / total_duration * 100
                )
            else:
                category_stats[category]["percentage"] = 0
            
            # Format duration
            duration_seconds = category_stats[category]["duration"]
            hours = duration_seconds / 3600
            category_stats[category]["duration_hours"] = round(hours, 2)
        
        # Get top activities by category
        top_activities_by_category = {}
        for category, activities in activities_by_category.items():
            # Sort by duration and get top 10
            sorted_activities = sorted(
                activities, 
                key=lambda x: x["duration"], 
                reverse=True
            )[:10]
            
            top_activities_by_category[category] = [
                {
                    "window_title": act["window_title"],
                    "application_name": act["application_name"],
                    "duration": act["duration"],
                    "duration_hours": round(act["duration"] / 3600, 2),
                    "subcategory": act["subcategory"],
                    "confidence": act["confidence"]
                }
                for act in sorted_activities
            ]
        
        return {
            "developer_id": developer_id,
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "statistics": category_stats,
            "total_duration_hours": round(total_duration / 3600, 2),
            "top_activities_by_category": top_activities_by_category,
            "productivity_score": calculate_productivity_score(category_stats)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error categorizing activities: {str(e)}"
        )

@router.post("/api/update-activity-categories/{developer_id}")
async def update_activity_categories(
    developer_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Update the category field in the database for all activities"""
    try:
        categorizer = ActivityCategorizer()
        
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        
        # Fetch activities
        query = text("""
            SELECT id, window_title, application_name
            FROM activity_records
            WHERE developer_id = :dev_id
            AND timestamp >= :start_date
            AND timestamp <= :end_date
        """)
        
        result = db.execute(query, {
            "dev_id": developer_id,
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        updated_count = 0
        
        for row in result:
            activity_id = row[0]
            window_title = row[1] or ""
            app_name = row[2] or ""
            
            # Get category
            category_info = categorizer.get_detailed_category(window_title, app_name)
            
            # Update database
            update_query = text("""
                UPDATE activity_records
                SET 
                    category = :category,
                    subcategory = :subcategory,
                    category_confidence = :confidence
                WHERE id = :activity_id
            """)
            
            db.execute(update_query, {
                "category": category_info["category"],
                "subcategory": category_info["subcategory"],
                "confidence": category_info["confidence"],
                "activity_id": activity_id
            })
            
            updated_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} activities"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating categories: {str(e)}"
        )

@router.get("/api/category-summary")
async def get_category_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get summary of all activities by category across all developers"""
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
        
        # Get summary by category
        query = text("""
            SELECT 
                COALESCE(category, 'uncategorized') as category,
                COUNT(*) as activity_count,
                SUM(duration) as total_duration,
                COUNT(DISTINCT developer_id) as developer_count
            FROM activity_records
            WHERE timestamp >= :start_date
            AND timestamp <= :end_date
            GROUP BY category
            ORDER BY total_duration DESC
        """)
        
        result = db.execute(query, {
            "start_date": start,
            "end_date": end
        }).fetchall()
        
        summary = []
        total_duration = 0
        
        for row in result:
            category_data = {
                "category": row[0],
                "activity_count": row[1],
                "total_duration_seconds": row[2] or 0,
                "total_duration_hours": round((row[2] or 0) / 3600, 2),
                "developer_count": row[3]
            }
            summary.append(category_data)
            total_duration += category_data["total_duration_seconds"]
        
        # Add percentages
        for item in summary:
            if total_duration > 0:
                item["percentage"] = round(
                    item["total_duration_seconds"] / total_duration * 100, 2
                )
            else:
                item["percentage"] = 0
        
        return {
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "summary": summary,
            "total_duration_hours": round(total_duration / 3600, 2)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting category summary: {str(e)}"
        )

def calculate_productivity_score(category_stats: Dict) -> float:
    """Calculate productivity score based on category distribution"""
    productive_time = category_stats["productive"]["duration"]
    server_time = category_stats["server"]["duration"]
    browser_time = category_stats["browser"]["duration"]
    non_work_time = category_stats["non-work"]["duration"]
    
    # Productive and server time count fully
    productive_total = productive_time + server_time
    
    # Browser time counts at 50% (some is work-related)
    productive_total += browser_time * 0.5
    
    # Total time excluding non-work
    total_time = sum(stat["duration"] for stat in category_stats.values())
    work_time = total_time - non_work_time
    
    if work_time > 0:
        score = (productive_total / work_time) * 100
    else:
        score = 0
    
    return round(min(score, 100), 2)
