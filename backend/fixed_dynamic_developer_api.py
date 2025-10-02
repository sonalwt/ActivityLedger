# backend/fixed_dynamic_developer_api.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import os
import logging
from database import get_db
from models import ActivityRecord
from config import Config
from developer_discovery import DeveloperDiscovery
from fixed_developer_discovery import FixedDeveloperDiscovery
from dynamic_activitywatch_client import DynamicActivityWatchClient
from activity_categorizer import ActivityCategorizer
import socket

logger = logging.getLogger(__name__)
router = APIRouter()

class EnvironmentBasedDeveloperService:
    """Service to handle developer list based on environment - Fixed for existing DB"""
    
    def __init__(self, db: Session):
        self.db = db
        self.discovery = FixedDeveloperDiscovery(db)
        
    def get_developers_list(self, scan_network: bool = False, 
                           scan_local: bool = True, 
                           scan_database: bool = True,
                           force_refresh: bool = False) -> Dict:
        """Get developers list based on environment (local vs production)"""
        
        if Config.is_local():
            return self._get_local_developer_only()
        else:
            return self._get_all_developers(scan_network, scan_local, scan_database, force_refresh)
    
    def _get_local_developer_only(self) -> Dict:
        """Return only the current local developer"""
        try:
            # Get local machine info
            local_hostname = socket.gethostname()
            local_developer_name = Config.LOCAL_DEVELOPER_NAME or local_hostname
            
            # Check if local developer exists in developers table
            from sqlalchemy import text
            dev_result = self.db.execute(text("""
                SELECT developer_id, name 
                FROM developers 
                WHERE name = :dev_name OR developer_id = :dev_name
                LIMIT 1
            """), {
                "dev_name": local_developer_name
            }).fetchone()
            
            # Use the developer_id from database if exists
            if dev_result:
                local_developer_id = dev_result[0]
                local_developer_name = dev_result[1]
            else:
                local_developer_id = local_developer_name
                logger.warning(f"Local developer '{local_developer_name}' not found in developers table")
            
            # Check if ActivityWatch is running locally
            local_instances = self.discovery.discover_local_instances()
            
            developers = []
            
            if local_instances:
                # ActivityWatch is running - use live data
                for instance in local_instances:
                    developers.append({
                        "id": f"local_{instance['port']}",
                        "name": local_developer_name,
                        "hostname": local_hostname,
                        "host": instance['host'],
                        "port": instance['port'],
                        "status": "online",
                        "source": "local",
                        "description": f"Local ActivityWatch instance",
                        "device_id": instance.get('device_id', f"{local_hostname}_{instance['port']}"),
                        "developer_id": local_developer_id,
                        "activity_count": self._get_activity_count_safe(local_developer_id),
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "version": instance.get('version', 'unknown'),
                        "bucket_count": instance.get('bucket_count', 0)
                    })
            else:
                # No ActivityWatch running - check database for historical data
                db_activity_count = self._get_activity_count_safe(local_developer_id)
                
                developers.append({
                    "id": f"local_db_{local_hostname}",
                    "name": local_developer_name,
                    "hostname": local_hostname,
                    "host": "localhost",
                    "port": 5600,
                    "status": "database_only" if db_activity_count > 0 else "offline",
                    "source": "database" if db_activity_count > 0 else "local",
                    "description": f"Local developer ({db_activity_count} activities in database)" if db_activity_count > 0 else f"Local developer (no data yet)",
                    "device_id": local_hostname,
                    "developer_id": local_developer_id,
                    "activity_count": db_activity_count,
                    "last_seen": self._get_last_activity_time_safe(local_developer_id),
                    "version": "database" if db_activity_count > 0 else "unknown",
                    "bucket_count": 0
                })
            
            return {
                "developers": developers,
                "environment": "local",
                "total_count": len(developers),
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "local_developer": local_developer_name,
                "local_developer_id": local_developer_id if 'local_developer_id' in locals() else local_developer_name
            }
            
        except Exception as e:
            logger.error(f"Error getting local developer: {e}")
            # Return basic developer info even if database fails
            return {
                "developers": [{
                    "id": "local_fallback",
                    "name": Config.LOCAL_DEVELOPER_NAME,
                    "hostname": socket.gethostname(),
                    "host": "localhost",
                    "port": 5600,
                    "status": "unknown",
                    "source": "local",
                    "description": "Local developer (database error)",
                    "device_id": socket.gethostname(),
                    "developer_id": Config.LOCAL_DEVELOPER_NAME,
                    "activity_count": 0,
                    "last_seen": None,
                    "version": "unknown",
                    "bucket_count": 0
                }],
                "environment": "local",
                "total_count": 1,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "local_developer": Config.LOCAL_DEVELOPER_NAME,
                "error": str(e)
            }
    
    def _get_all_developers(self, scan_network: bool, scan_local: bool, 
                           scan_database: bool, force_refresh: bool) -> Dict:
        """Get all developers from all sources (production mode)"""
        try:
            # Full discovery
            logger.info("Performing full developer discovery...")
            discovered_developers = self.discovery.discover_all_developers(
                scan_network=scan_network,
                scan_local=scan_local, 
                scan_database=scan_database
            )
            
            # Enhance with activity counts
            for dev in discovered_developers:
                # Use developer_id for activity count lookup
                dev_id = dev.get('developer_id') or dev.get('id')
                dev['activity_count'] = self._get_activity_count_safe(dev_id)
                if not dev.get('last_seen'):
                    dev['last_seen'] = self._get_last_activity_time_safe(dev_id)
                    if dev['last_seen']:
                        dev['last_seen'] = dev['last_seen'].isoformat() if isinstance(dev['last_seen'], datetime) else dev['last_seen']
            
            return {
                "developers": discovered_developers,
                "environment": "production",
                "total_count": len(discovered_developers),
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"Error discovering all developers: {e}")
            raise HTTPException(status_code=500, detail=f"Error discovering developers: {str(e)}")
    
    def _get_activity_count_safe(self, developer_id_or_name: str) -> int:
        """Safely get activity count for a developer"""
        try:
            from sqlalchemy import func, text
            
            # First check if it's a developer_id
            dev_result = self.db.execute(text("""
                SELECT developer_id 
                FROM developers 
                WHERE developer_id = :dev_id OR name = :dev_name
                LIMIT 1
            """), {
                "dev_id": developer_id_or_name,
                "dev_name": developer_id_or_name
            }).fetchone()
            
            if dev_result:
                developer_id = dev_result[0]
                # Count activities for this developer
                result = self.db.execute(text("""
                    SELECT COUNT(*) 
                    FROM activity_records 
                    WHERE developer_id = :dev_id
                """), {
                    "dev_id": developer_id
                })
                
                count = result.scalar()
                return count or 0
            else:
                return 0
            
        except Exception as e:
            logger.warning(f"Error getting activity count for {developer_id_or_name}: {e}")
            # Try simpler query
            try:
                result = self.db.execute(text("SELECT COUNT(*) FROM activity_records"))
                total = result.scalar()
                logger.info(f"Returning total activity count: {total}")
                return total or 0
            except:
                return 0
    
    def _get_last_activity_time_safe(self, developer_id_or_name: str) -> Optional[str]:
        """Safely get last activity time for a developer"""
        try:
            from sqlalchemy import text
            
            # First get the developer_id
            dev_result = self.db.execute(text("""
                SELECT developer_id 
                FROM developers 
                WHERE developer_id = :dev_id OR name = :dev_name
                LIMIT 1
            """), {
                "dev_id": developer_id_or_name,
                "dev_name": developer_id_or_name
            }).fetchone()
            
            if dev_result:
                developer_id = dev_result[0]
                # Get last activity for this developer
                result = self.db.execute(text("""
                    SELECT MAX(timestamp)
                    FROM activity_records 
                    WHERE developer_id = :dev_id
                """), {
                    "dev_id": developer_id
                })
                
                last_time = result.scalar()
                return last_time.isoformat() if last_time else None
            else:
                return None
            
        except Exception as e:
            logger.warning(f"Error getting last activity time for {developer_id_or_name}: {e}")
            return None

# API Endpoints
@router.get("/developers")
async def get_developers_list(
    scan_network: bool = False,
    scan_local: bool = True,
    scan_database: bool = True,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """Get developers list based on environment"""
    service = EnvironmentBasedDeveloperService(db)
    return service.get_developers_list(scan_network, scan_local, scan_database, force_refresh)

@router.get("/activity-data/{developer_id}")
async def get_developer_activity_data(
    developer_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get activity data for a specific developer"""
    try:
        # Initialize categorizer
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
        
        # Get developer info
        service = EnvironmentBasedDeveloperService(db)
        developers_result = service.get_developers_list()
        
        developer = next((d for d in developers_result['developers'] if d['id'] == developer_id), None)
        if not developer:
            raise HTTPException(status_code=404, detail="Developer not found")
        
        activity_data = []
        data_source = "database"
        
        # Try to get live data if developer is online
        if developer['status'] == 'online':
            try:
                client = DynamicActivityWatchClient(developer)
                if client.test_connection():
                    activity_data = client.get_activity_data(start, end)
                    data_source = "activitywatch"
                    logger.info(f"Retrieved live data for {developer['name']}: {len(activity_data)} activities")
                            
            except Exception as e:
                logger.warning(f"Failed to get live data for {developer['name']}: {e}")
        
        # Fallback to database if no live data
        if not activity_data:
            try:
                from sqlalchemy import text
                
                # Use proper JOIN to get developer name from developers table
                db_records = db.execute(text("""
                    SELECT 
                        ar.application_name,
                        ar.window_title,
                        ar.duration,
                        ar.timestamp,
                        ar.category,
                        ar.detailed_activity,
                        ar.url,
                        ar.file_path,
                        ar.developer_id,
                        d.name as developer_name
                    FROM activity_records ar
                    LEFT JOIN developers d ON ar.developer_id = d.developer_id
                    WHERE ar.developer_id = :dev_id
                    AND ar.timestamp >= :start_date
                    AND ar.timestamp <= :end_date
                    ORDER BY ar.duration DESC
                    LIMIT 1000
                """), {
                    "dev_id": developer.get('developer_id') or developer['name'],
                    "start_date": start,
                    "end_date": end
                }).fetchall()
                
                activity_data = [{
                    "developer_id": record.developer_id,
                    "developer_name": record.developer_name or developer['name'],
                    "application_name": record.application_name,
                    "window_title": record.window_title,
                    "duration": record.duration or 0,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "category": record.category or "Other",
                    "detailed_activity": record.detailed_activity or record.window_title,
                    "url": record.url or "",
                    "file_path": record.file_path or ""
                } for record in db_records]
                
                data_source = "database"
                logger.info(f"Retrieved database data for {developer['name']}: {len(activity_data)} activities")
                
            except Exception as e:
                logger.error(f"Error getting database records: {e}")
                activity_data = []
        
        # Categorize all activities
        for activity in activity_data:
            category_info = categorizer.get_detailed_category(
                activity.get('window_title', ''),
                activity.get('application_name', '')
            )
            
            # Update activity with categorization
            activity['category'] = category_info['category']
            activity['subcategory'] = category_info['subcategory']
            activity['category_confidence'] = category_info['confidence']
        
        # Calculate category summaries
        category_summary = {
            "productive": {"count": 0, "duration": 0},
            "browser": {"count": 0, "duration": 0},
            "server": {"count": 0, "duration": 0},
            "non-work": {"count": 0, "duration": 0},
            "uncategorized": {"count": 0, "duration": 0}
        }
        
        for activity in activity_data:
            cat = activity.get('category', 'uncategorized')
            if cat in category_summary:
                category_summary[cat]['count'] += 1
                category_summary[cat]['duration'] += activity.get('duration', 0)
        
        total_duration = sum(item["duration"] for item in activity_data)
        
        # Calculate percentages
        for cat in category_summary:
            if total_duration > 0:
                category_summary[cat]['percentage'] = round((category_summary[cat]['duration'] / total_duration) * 100, 1)
            else:
                category_summary[cat]['percentage'] = 0
        
        return {
            "data": activity_data,
            "developer": developer,
            "data_source": data_source,
            "total_time": total_duration,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "activity_count": len(activity_data),
            "category_summary": category_summary
        }
        
    except Exception as e:
        logger.error(f"Error getting activity data for {developer_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting activity data: {str(e)}")
