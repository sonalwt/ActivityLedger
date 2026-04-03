from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime
from typing import List, Dict
import models, schemas, auth

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_activity_record(db: Session, activity_data: Dict, user_id: int):
    """Create a new activity record (prevents duplicates)"""
    from improved_project_extractor import extract_project_info
    
    # Convert duration from milliseconds to seconds
    activity_data['duration'] = activity_data.get('duration', 0) / 1000

    # If project_name is missing or 'general', try to extract from window title
    if not activity_data.get('project_name') or activity_data.get('project_name') == 'general':
        window_title = activity_data.get('window_title', '')
        if ' - ' in window_title:
            # Extract project name from window title (e.g., "timesheet - main.py - VS Code")
            activity_data['project_name'] = window_title.split(' - ')[0].strip()
    
    # Check if this exact record already exists
    existing_record = db.query(models.ActivityRecord).filter(
        and_(
            models.ActivityRecord.user_id == user_id,
            models.ActivityRecord.application_name == activity_data.get("application_name", "Unknown"),
            models.ActivityRecord.window_title == activity_data.get("window_title", ""),
            models.ActivityRecord.timestamp == activity_data.get("timestamp", datetime.now()),
            models.ActivityRecord.duration == activity_data.get("duration", 0)
        )
    ).first()
    
    if existing_record:
        # Update existing record with project info if missing
        if not existing_record.project_name:
            project_info = extract_project_info(activity_data)
            existing_record.project_name = project_info.get("project_name")
            existing_record.project_type = project_info.get("project_type")
            existing_record.project_file = project_info.get("project_file")
            db.commit()
        return existing_record
    
    # Extract project information
    project_info = extract_project_info(activity_data)
    
    # Create new record if it doesn't exist
    db_activity = models.ActivityRecord(
        user_id=user_id,
        application_name=activity_data.get("application_name", "Unknown"),
        window_title=activity_data.get("window_title", ""),
        url=activity_data.get("url"),
        file_path=activity_data.get("file_path"),
        database_connection=activity_data.get("database_connection"),
        specific_process=activity_data.get("specific_process"),
        detailed_activity=activity_data.get("detailed_activity"),
        category=activity_data.get("category", "other"),
        duration=activity_data.get("duration", 0),  # Now in seconds
        timestamp=activity_data.get("timestamp", datetime.now()),
        # Add project information
        project_name=project_info.get("project_name"),
        project_type=project_info.get("project_type"),
        project_file=project_info.get("project_file")
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

def get_activity_summary(db: Session, user_id: int, start_date: datetime, end_date: datetime):
    """Get activity summary grouped by application"""
    from sqlalchemy import text
    
    # Group by application name only to avoid duplicates, but get the primary category
    database_url = db.get_bind().url
    if 'postgresql' in str(database_url):
        # PostgreSQL uses string_agg
        results = db.query(
            models.ActivityRecord.application_name,
            func.string_agg(models.ActivityRecord.url, ',').label('urls'),
            func.sum(models.ActivityRecord.duration).label('total_duration')
        ).filter(
            and_(
                models.ActivityRecord.user_id == user_id,
                models.ActivityRecord.timestamp >= start_date,
                models.ActivityRecord.timestamp <= end_date
            )
        ).group_by(
            models.ActivityRecord.application_name
        ).all()
    else:
        # SQLite uses group_concat
        results = db.query(
            models.ActivityRecord.application_name,
            func.group_concat(models.ActivityRecord.url).label('urls'),
            func.sum(models.ActivityRecord.duration).label('total_duration')
        ).filter(
            and_(
                models.ActivityRecord.user_id == user_id,
                models.ActivityRecord.timestamp >= start_date,
                models.ActivityRecord.timestamp <= end_date
            )
        ).group_by(
            models.ActivityRecord.application_name
        ).all()

    total_time = sum(result.total_duration for result in results)
    
    summary = []
    for result in results:
        urls = list(set(result.urls.split(',') if result.urls else []))
        urls = [url for url in urls if url and url != 'None']
        
        # Get the most representative record for this application (longest duration)
        sample_record = db.query(models.ActivityRecord).filter(
            and_(
                models.ActivityRecord.user_id == user_id,
                models.ActivityRecord.application_name == result.application_name,
                models.ActivityRecord.timestamp >= start_date,
                models.ActivityRecord.timestamp <= end_date
            )
        ).order_by(models.ActivityRecord.duration.desc()).first()
        
        summary.append({
            "application_name": result.application_name,
            "category": sample_record.category if sample_record else "other",
            "duration": result.total_duration,
            "percentage": (result.total_duration / total_time * 100) if total_time > 0 else 0,
            "urls": urls[:10] if urls else [],  # Limit to top 10 URLs
            "file_path": sample_record.file_path if sample_record else None,
            "database_connection": sample_record.database_connection if sample_record else None,
            "specific_process": sample_record.specific_process if sample_record else None,
            "detailed_activity": sample_record.detailed_activity if sample_record else None,
            "window_title": sample_record.window_title if sample_record else None,
            # Add project information
            "project_name": sample_record.project_name if sample_record else None,
            "project_type": sample_record.project_type if sample_record else None,
            "project_file": sample_record.project_file if sample_record else None
        })
    
    # Sort by duration descending
    summary.sort(key=lambda x: x["duration"], reverse=True)
    
    return summary
