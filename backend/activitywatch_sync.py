# activitywatch_sync.py - Minimal implementation to fix import error

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests
from config import Config

class ActivityWatchSync:
    """Minimal ActivityWatch sync implementation to fix import errors"""
    
    def __init__(self):
        self.aw_host = Config.ACTIVITYWATCH_HOST
        self.developer_name = Config.LOCAL_DEVELOPER_NAME
        
    def sync_activitywatch_data(self, start_date: datetime, end_date: datetime) -> bool:
        """Sync data from ActivityWatch (stub implementation)"""
        print(f"ActivityWatchSync: Would sync data from {start_date} to {end_date}")
        # For now, just return success to avoid errors
        return True
        
    def get_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get summary of synced data (stub implementation)"""
        return {
            "synced_records": 0,
            "total_duration": 0,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "message": "Sync module is in stub mode"
        }
