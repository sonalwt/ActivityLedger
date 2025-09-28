#!/usr/bin/env python3
"""
Automated ActivityWatch Data Puller
Pulls activity data from all registered developers' local ActivityWatch instances
and saves to production database every 10 seconds via scheduled task.
"""

import requests
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:asdf1234@localhost:5432/timesheet")
ACTIVITYWATCH_PORT = int(os.getenv("ACTIVITYWATCH_PORT", "5600"))
DATA_PULL_WINDOW_MINUTES = int(os.getenv("DATA_PULL_WINDOW_MINUTES", "1"))  # Pull last 1 minute of data
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/activitywatch_puller.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ActivityWatchDataPuller:
    def __init__(self):
        """Initialize the data puller with database connection"""
        try:
            self.engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.db = SessionLocal()
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            sys.exit(1)
    
    def get_registered_developers(self) -> List[Dict]:
        """Get all registered developers from database"""
        try:
            query = text("""
                SELECT 
                    developer_id,
                    name,
                    email,
                    api_token,
                    created_at,
                    last_sync,
                    ip_address,
                    activitywatch_port,
                    hostname
                FROM developers 
                WHERE active = true
                ORDER BY developer_id
            """)
            
            result = self.db.execute(query)
            developers = []
            
            for row in result:
                developers.append({
                    'developer_id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'api_token': row[3],
                    'created_at': row[4],
                    'last_sync': row[5],
                    'ip_address': row[6],
                    'activitywatch_port': row[7],
                    'hostname': row[8]
                })
            
            logger.info(f"📋 Found {len(developers)} active developers")
            return developers
            
        except Exception as e:
            logger.error(f"❌ Error fetching developers: {e}")
            return []
    
    def detect_developer_ip_and_port(self, developer: Dict) -> Optional[str]:
        """Get developer's ActivityWatch URL from stored registration info"""
        try:
            # Use stored IP address from registration
            ip_address = developer.get('ip_address')
            port = developer.get('activitywatch_port') or ACTIVITYWATCH_PORT
            
            if ip_address:
                aw_url = f"https://{ip_address}:{port}"
                
                # Test the connection quickly
                try:
                    response = requests.get(f"{aw_url}/api/0/info", timeout=3)
                    if response.status_code == 200:
                        logger.debug(f"✅ {developer['developer_id']}: Connected to {aw_url}")
                        return aw_url
                    else:
                        logger.warning(f"⚠️  {developer['developer_id']}: ActivityWatch not responding at {aw_url}")
                except requests.exceptions.RequestException:
                    logger.warning(f"⚠️  {developer['developer_id']}: Cannot reach {aw_url}")
            
            # If stored IP doesn't work, try localhost (common case)
            try:
                localhost_url = f"http://127.0.0.1:{port}"
                response = requests.get(f"{localhost_url}/api/0/info", timeout=2)
                if response.status_code == 200:
                    logger.info(f"🎯 Found {developer['developer_id']} at localhost")
                    # Update database with localhost
                    update_query = text("""
                        UPDATE developers 
                        SET ip_address = '127.0.0.1', updated_at = NOW()
                        WHERE developer_id = :dev_id
                    """)
                    self.db.execute(update_query, {"dev_id": developer['developer_id']})
                    self.db.commit()
                    return localhost_url
            except:
                pass
            
            logger.warning(f"⚠️  Could not locate ActivityWatch for developer: {developer['developer_id']}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error detecting IP for {developer['developer_id']}: {e}")
            return None
    
    def pull_activity_data_from_developer(self, developer: Dict) -> List[Dict]:
        """Pull ActivityWatch data from a specific developer's machine"""
        developer_id = developer['developer_id']
        
        try:
            # Get developer's ActivityWatch URL from stored registration info
            aw_url = self.detect_developer_ip_and_port(developer)
            if not aw_url:
                logger.debug(f"⚠️  Skipping {developer_id}: ActivityWatch not accessible")
                return []
            
            # Get available buckets
            buckets_url = f"{aw_url}/api/0/buckets"
            buckets_response = requests.get(buckets_url, timeout=10)
            
            if buckets_response.status_code != 200:
                logger.debug(f"⚠️  {developer_id}: Could not fetch buckets")
                return []
            
            buckets = buckets_response.json()
            logger.debug(f"📦 {developer_id}: Found {len(buckets)} buckets")
            
            # Define time window for data pull
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=DATA_PULL_WINDOW_MINUTES)
            
            activities = []
            
            # Pull data from each bucket
            for bucket_name, bucket_info in buckets.items():
                # Skip AFK buckets
                if 'afk' in bucket_name.lower():
                    continue
                
                try:
                    events_url = f"{aw_url}/api/0/buckets/{bucket_name}/events"
                    params = {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat(),
                        'limit': 1000
                    }
                    
                    events_response = requests.get(events_url, params=params, timeout=10)
                    if events_response.status_code != 200:
                        continue
                    
                    events = events_response.json()
                    
                    for event in events:
                        data = event.get('data', {})
                        duration = event.get('duration', 0)
                        
                        # Skip very short activities (less than 5 seconds)
                        if duration < 5:
                            continue
                        
                        activity = {
                            'developer_id': developer_id,
                            'developer_name': developer.get('name', developer_id),
                            'developer_hostname': data.get('hostname', developer.get('hostname', 'unknown')),
                            'application_name': data.get('app', data.get('application', 'Unknown')),
                            'window_title': data.get('title', ''),
                            'url': data.get('url', None),
                            'category': self._categorize_application(data.get('app', '')),
                            'duration': duration,
                            'timestamp': datetime.fromisoformat(event.get('timestamp', '').replace('Z', '+00:00')),
                            'bucket_name': bucket_name,
                            'raw_data': json.dumps(data)
                        }
                        
                        activities.append(activity)
                
                except Exception as e:
                    logger.debug(f"⚠️  Error processing bucket {bucket_name} for {developer_id}: {e}")
                    continue
            
            if activities:
                logger.info(f"📊 {developer_id}: Pulled {len(activities)} activities")
            return activities
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"⚠️  {developer_id}: Network error - {e}")
            return []
        except Exception as e:
            logger.error(f"❌ {developer_id}: Unexpected error - {e}")
            return []
    
    def _categorize_application(self, app_name: str) -> str:
        """Categorize application based on name"""
        if not app_name:
            return "unknown"
        
        app_lower = app_name.lower()
        
        if any(ide in app_lower for ide in ['code', 'idea', 'pycharm', 'studio', 'sublime']):
            return "ide"
        elif any(browser in app_lower for browser in ['chrome', 'firefox', 'edge', 'safari']):
            return "browser"
        elif any(term in app_lower for term in ['terminal', 'cmd', 'powershell']):
            return "terminal"
        elif any(comm in app_lower for comm in ['slack', 'teams', 'discord', 'zoom']):
            return "communication"
        else:
            return "general"
    
    def save_activities_to_database(self, activities: List[Dict]) -> bool:
        """Save activities to the production database"""
        if not activities:
            return True
        
        try:
            # Use INSERT ... ON CONFLICT to avoid duplicates
            insert_query = text("""
                INSERT INTO activity_records (
                    developer_id, developer_name, developer_hostname,
                    application_name, window_title, url, category,
                    duration, timestamp, bucket_name, created_at
                ) VALUES (
                    :developer_id, :developer_name, :developer_hostname,
                    :application_name, :window_title, :url, :category,
                    :duration, :timestamp, :bucket_name, :created_at
                )
            """)
            
            saved_count = 0
            for activity in activities:
                try:
                    # Check if activity already exists to avoid duplicates
                    exists_query = text("""
                        SELECT 1 FROM activity_records 
                        WHERE developer_id = :developer_id 
                        AND timestamp = :timestamp 
                        AND application_name = :application_name 
                        AND duration = :duration
                        LIMIT 1
                    """)
                    
                    exists = self.db.execute(exists_query, {
                        'developer_id': activity['developer_id'],
                        'timestamp': activity['timestamp'],
                        'application_name': activity['application_name'],
                        'duration': activity['duration']
                    }).fetchone()
                    
                    if not exists:
                        self.db.execute(insert_query, {
                            **activity,
                            'created_at': datetime.now(timezone.utc)
                        })
                        saved_count += 1
                        
                except Exception as e:
                    logger.debug(f"⚠️  Failed to save activity: {e}")
                    continue
            
            self.db.commit()
            if saved_count > 0:
                logger.info(f"💾 Saved {saved_count} new activities to database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database save error: {e}")
            self.db.rollback()
            return False
    
    def update_developer_sync_status(self, developer_id: str, success: bool):
        """Update last sync timestamp for developer"""
        try:
            query = text("""
                UPDATE developers 
                SET last_sync = :timestamp
                WHERE developer_id = :dev_id
            """)
            
            self.db.execute(query, {
                "timestamp": datetime.now(timezone.utc),
                "dev_id": developer_id
            })
            self.db.commit()
            
        except Exception as e:
            logger.debug(f"⚠️  Could not update sync status for {developer_id}: {e}")
    
    def pull_all_developer_data(self):
        """Main function to pull data from all registered developers"""
        start_time = time.time()
        logger.debug("🔄 Starting data pull from all developers...")
        
        try:
            # Get all registered developers
            developers = self.get_registered_developers()
            
            if not developers:
                logger.debug("⚠️  No active developers found")
                return
            
            total_activities = 0
            successful_pulls = 0
            
            # Pull data from each developer
            for developer in developers:
                developer_id = developer['developer_id']
                
                try:
                    activities = self.pull_activity_data_from_developer(developer)
                    
                    if activities:
                        success = self.save_activities_to_database(activities)
                        if success:
                            total_activities += len(activities)
                            successful_pulls += 1
                    
                    # Always update sync status
                    self.update_developer_sync_status(developer_id, True)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process {developer_id}: {e}")
                    self.update_developer_sync_status(developer_id, False)
                    continue
            
            # Summary (only log if there's activity)
            elapsed = time.time() - start_time
            if total_activities > 0:
                logger.info(f"✅ Pull completed in {elapsed:.2f}s: {total_activities} activities from {successful_pulls}/{len(developers)} developers")
            
        except Exception as e:
            logger.error(f"❌ Critical error during data pull: {e}")
        finally:
            self.db.close()

def main():
    """Main entry point"""
    try:
        puller = ActivityWatchDataPuller()
        puller.pull_all_developer_data()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
