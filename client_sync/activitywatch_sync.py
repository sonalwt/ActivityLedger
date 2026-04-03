#!/usr/bin/env python3
"""
ActivityWatch Data Sync Client
Automatically syncs local ActivityWatch data to central timesheet server
"""

import requests
import json
import os
import time
import schedule
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import List, Dict, Optional
import sys
import argparse

# Load environment variables
load_dotenv()

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "https://your-timesheet-server.com/api/v1")
DEVELOPER_ID = os.getenv("DEVELOPER_ID", "")
API_TOKEN = os.getenv("API_TOKEN", "")
ACTIVITYWATCH_HOST = os.getenv("ACTIVITYWATCH_HOST", "http://localhost:5600")
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('activitywatch_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ActivityWatchSyncer:
    def __init__(self):
        self.aw_api_url = f"{ACTIVITYWATCH_HOST}/api/0"
        self.server_url = SERVER_URL
        self.developer_id = DEVELOPER_ID
        self.api_token = API_TOKEN
        
        if not self.developer_id or not self.api_token:
            logger.error("DEVELOPER_ID and API_TOKEN must be set in environment or .env file")
            sys.exit(1)
        
        self.headers = {
            "Developer-ID": self.developer_id,
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Initialized syncer for developer: {self.developer_id}")
        logger.info(f"Server URL: {self.server_url}")
        logger.info(f"ActivityWatch Host: {ACTIVITYWATCH_HOST}")
    
    def get_local_activity_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get activity data from local ActivityWatch instance"""
        try:
            logger.debug(f"Fetching local data from {start_time} to {end_time}")
            
            # Get available buckets
            buckets_response = requests.get(f"{self.aw_api_url}/buckets/", timeout=10)
            buckets_response.raise_for_status()
            buckets = buckets_response.json()
            
            logger.debug(f"Found {len(buckets)} ActivityWatch buckets")
            
            activities = []
            
            for bucket_name, bucket_info in buckets.items():
                # Skip AFK buckets
                if 'afk' in bucket_name.lower():
                    continue
                
                logger.debug(f"Processing bucket: {bucket_name}")
                
                # Get events from this bucket
                params = {
                    'start': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'end': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'limit': 5000
                }
                
                try:
                    events_response = requests.get(
                        f"{self.aw_api_url}/buckets/{bucket_name}/events",
                        params=params,
                        timeout=15
                    )
                    events_response.raise_for_status()
                    events = events_response.json()
                    
                    logger.debug(f"Found {len(events)} events in bucket {bucket_name}")
                    
                    for event in events:
                        data = event.get('data', {})
                        duration = event.get('duration', 0)
                        timestamp = event.get('timestamp', '')
                        
                        # Skip very short activities (less than 5 seconds)
                        if duration < 5:
                            continue
                        
                        # Skip activities with no meaningful data
                        app_name = data.get('app', data.get('application', ''))
                        window_title = data.get('title', '')
                        project = data.get('project', '')
                        file_path = data.get('file', '')
                        language = data.get('language', '')

                        # For VS Code watcher events: no app/title but has project/file
                        if not app_name and (project or file_path):
                            app_name = 'Visual Studio Code'

                        # Derive window_title from file_path when title is empty (e.g. aw-watcher-vscode)
                        if not window_title and file_path:
                            basename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path.rsplit('\\', 1)[-1] if '\\' in file_path else file_path
                            window_title = basename

                        if not app_name or app_name == 'Unknown':
                            continue

                        activity = {
                            "application_name": app_name,
                            "window_title": window_title,
                            "duration": duration,
                            "timestamp": timestamp,
                            "bucket_name": bucket_name,
                            "developer_id": self.developer_id,
                            "project": project,
                            "file": file_path,
                            "language": language
                        }
                        
                        activities.append(activity)
                        
                except requests.RequestException as e:
                    logger.error(f"Error fetching events from bucket {bucket_name}: {e}")
                    continue
            
            logger.info(f"Collected {len(activities)} activities from local ActivityWatch")
            return activities
            
        except requests.RequestException as e:
            logger.error(f"Error connecting to local ActivityWatch: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting local data: {e}")
            return []
    
    def send_to_server(self, activities: List[Dict]) -> bool:
        """Send activities to central timesheet server"""
        if not activities:
            logger.info("No activities to send")
            return True

        # Convert activities to ActivityWatch event format for /api/sync endpoint
        events = []
        for activity in activities:
            event = {
                "timestamp": activity.get("timestamp", ""),
                "duration": activity.get("duration", 0),
                "data": {
                    "app": activity.get("application_name", ""),
                    "title": activity.get("window_title", ""),
                    "url": activity.get("url", None),
                    "project": activity.get("project", ""),
                    "file": activity.get("file", ""),
                    "language": activity.get("language", "")
                }
            }
            events.append(event)

        # Payload format for /api/sync endpoint (name/token in body)
        payload = {
            "name": self.developer_id,
            "token": self.api_token,
            "data": events,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            logger.debug(f"Sending {len(events)} activities to server")

            # Send directly to SERVER_URL (which should be the /api/sync endpoint)
            response = requests.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            result = response.json()

            if result.get("success"):
                logger.info(f"✅ Successfully sent {len(events)} activities to server")
                logger.info(f"Server response: {result.get('message', 'No message')}")
                return True
            else:
                logger.error(f"❌ Server error: {result.get('error', 'Unknown error')}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending data to server: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Server error details: {error_detail}")
                except:
                    logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending to server: {e}")
            return False
    
    def sync_recent_data(self, hours_back: float = 1.0) -> bool:
        """Sync recent activity data to server"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        logger.info(f"🔄 Starting sync for period: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get local activity data
        activities = self.get_local_activity_data(start_time, end_time)
        
        if activities:
            # Send to server
            success = self.send_to_server(activities)
            if success:
                logger.info(f"✅ Sync completed successfully")
            else:
                logger.error(f"❌ Sync failed - server communication error")
            return success
        else:
            logger.info("ℹ️  No activities found to sync")
            return True
    
    def test_connections(self) -> bool:
        """Test connections to both ActivityWatch and server"""
        logger.info("🔍 Testing connections...")

        # Test ActivityWatch
        aw_status = False
        try:
            aw_response = requests.get(f"{self.aw_api_url}/buckets/", timeout=5)
            aw_status = aw_response.status_code == 200
            logger.info(f"ActivityWatch connection: {'✅' if aw_status else '❌'}")
        except Exception as e:
            logger.error(f"ActivityWatch connection: ❌ ({e})")

        # Test server - try health endpoint
        server_status = False
        try:
            # SERVER_URL is the full /api/sync URL, get base URL for health check
            base_url = self.server_url.rsplit('/api/sync', 1)[0]
            health_url = f"{base_url}/api/sync/health"
            server_response = requests.get(health_url, timeout=5)
            server_status = server_response.status_code == 200
            logger.info(f"Server connection: {'✅' if server_status else '❌'}")
        except Exception as e:
            # Try alternate health endpoint
            try:
                base_url = self.server_url.rsplit('/api/sync', 1)[0]
                server_response = requests.get(f"{base_url}/", timeout=5)
                server_status = server_response.status_code == 200
                logger.info(f"Server connection: {'✅' if server_status else '❌'}")
            except:
                logger.error(f"Server connection: ❌ ({e})")

        # Test authentication by sending empty sync
        auth_status = False
        try:
            test_payload = {
                "name": self.developer_id,
                "token": self.api_token,
                "data": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            auth_response = requests.post(
                self.server_url,
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            result = auth_response.json()
            auth_status = result.get("success", False) or "Invalid" not in result.get("error", "")
            logger.info(f"Authentication: {'✅' if auth_status else '❌'}")
            if not auth_status:
                logger.error(f"Auth error: {result.get('error', 'Unknown')}")
        except Exception as e:
            logger.error(f"Authentication test: ❌ ({e})")

        return aw_status and server_status and auth_status
    
    def run_continuous(self):
        """Run continuous syncing with scheduled intervals"""
        logger.info(f"🚀 Starting continuous sync with {SYNC_INTERVAL_MINUTES} minute intervals")
        
        # Test connections first
        if not self.test_connections():
            logger.error("❌ Connection tests failed. Please check configuration.")
            return False
        
        # Schedule regular syncing
        sync_job = schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(
            lambda: self.sync_recent_data(hours_back=SYNC_INTERVAL_MINUTES/60 + 0.5)  # Add 30 min buffer
        )
        
        # Schedule hourly sync for broader coverage
        hourly_job = schedule.every().hour.do(
            lambda: self.sync_recent_data(hours_back=2)  # 2 hour window
        )
        
        # Initial sync for last 24 hours
        logger.info("📥 Performing initial sync (last 24 hours)")
        self.sync_recent_data(hours_back=24)
        
        logger.info(f"⏰ Scheduler started. Next sync in {SYNC_INTERVAL_MINUTES} minutes...")
        
        # Main loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("🛑 Sync stopped by user")
            return True
        except Exception as e:
            logger.error(f"❌ Unexpected error in main loop: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='ActivityWatch Data Sync Client')
    parser.add_argument('--test', action='store_true', help='Test connections and exit')
    parser.add_argument('--sync-hours', type=float, default=1.0, help='Hours of data to sync (for one-time sync)')
    parser.add_argument('--continuous', action='store_true', help='Run continuous sync (default)')
    
    args = parser.parse_args()
    
    syncer = ActivityWatchSyncer()
    
    if args.test:
        logger.info("🔍 Running connection test...")
        if syncer.test_connections():
            logger.info("✅ All connections successful!")
            sys.exit(0)
        else:
            logger.error("❌ Connection test failed!")
            sys.exit(1)
    
    elif args.sync_hours:
        logger.info(f"📥 Running one-time sync for last {args.sync_hours} hours")
        success = syncer.sync_recent_data(hours_back=args.sync_hours)
        sys.exit(0 if success else 1)
    
    else:
        # Default: continuous mode
        success = syncer.run_continuous()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
