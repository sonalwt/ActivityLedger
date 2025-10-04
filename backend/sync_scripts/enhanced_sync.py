#!/usr/bin/env python3
"""
Enhanced ActivityWatch Sync with Proper Categorization
"""

import requests
import json
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
import time
from typing import Dict, List, Tuple

# Add parent directory to path to import activity_categorizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from activity_categorizer import ActivityCategorizer

class EnhancedActivityWatchSync:
    def __init__(self, developer_name: str, api_token: str):
        self.developer_name = developer_name
        self.api_token = api_token
        self.aw_url = "http://localhost:5600"
        self.api_url = "https://api-timesheet.firsteconomy.com/api/sync"
        self.categorizer = ActivityCategorizer()
        
        # Database connection (adjust these settings)
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'timesheet'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'your_password'),
            'port': os.getenv('DB_PORT', '5432')
        }
    
    def get_activitywatch_data(self, minutes_back: int = 6) -> List[Dict]:
        """Get activity data from ActivityWatch"""
        try:
            # Get buckets
            buckets_response = requests.get(f"{self.aw_url}/api/0/buckets", timeout=10)
            if buckets_response.status_code != 200:
                print("❌ Could not connect to ActivityWatch")
                return []
            
            buckets = buckets_response.json()
            print(f"📦 Found {len(buckets)} ActivityWatch buckets")
            
            # Time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=minutes_back)
            
            all_activities = []
            
            for bucket_name, bucket_info in buckets.items():
                # Skip AFK buckets
                if 'afk' in bucket_name.lower():
                    continue
                
                try:
                    # Get events
                    events_url = f"{self.aw_url}/api/0/buckets/{bucket_name}/events"
                    params = {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat(),
                        'limit': 1000
                    }
                    
                    events_response = requests.get(events_url, params=params, timeout=10)
                    if events_response.status_code != 200:
                        continue
                    
                    events = events_response.json()
                    print(f"  - {bucket_name}: {len(events)} events")
                    
                    # Process each event
                    for event in events:
                        activity = self.process_event(event, bucket_name)
                        if activity:
                            all_activities.append(activity)
                
                except Exception as e:
                    print(f"⚠️  Error processing {bucket_name}: {e}")
                    continue
            
            return all_activities
            
        except Exception as e:
            print(f"❌ Error getting ActivityWatch data: {e}")
            return []
    
    def process_event(self, event: Dict, bucket_name: str) -> Dict:
        """Process a single ActivityWatch event"""
        data = event.get('data', {})
        duration = event.get('duration', 0)
        timestamp = event.get('timestamp', '')
        
        # Skip very short activities (less than 5 seconds)
        if duration < 5:
            return None
        
        # Extract window title and app name properly
        window_title = data.get('title', 'Untitled')
        app_name = data.get('app', data.get('application', 'Unknown'))
        
        # Handle different bucket types
        if 'window' in bucket_name:
            # Window watcher provides title and app
            pass
        elif 'web' in bucket_name:
            # Web watcher provides URL and title
            url = data.get('url', '')
            if url and window_title == 'Untitled':
                window_title = url
        
        # Clean up window title
        if window_title:
            # Remove common suffixes
            window_title = window_title.replace(' - Google Chrome', '')
            window_title = window_title.replace(' - Mozilla Firefox', '')
            window_title = window_title.replace(' - Microsoft Edge', '')
            window_title = window_title.replace(' - Visual Studio Code', '')
        
        # Categorize the activity
        category_info = self.categorizer.get_detailed_category(window_title, app_name)
        
        # Parse timestamp
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            parsed_timestamp = datetime.now(timezone.utc)
        
        return {
            'developer_id': self.developer_name,
            'application_name': app_name,
            'window_title': window_title[:500],  # Limit length
            'url': data.get('url', ''),
            'file_path': data.get('file', ''),
            'duration': int(duration * 1000),  # Convert to milliseconds
            'timestamp': parsed_timestamp,
            'category': category_info['category'],
            'project_name': self.extract_project_name(window_title, app_name),
            'project_type': category_info['subcategory'],
            'bucket_name': bucket_name,
            'created_at': datetime.now(timezone.utc)
        }
    
    def extract_project_name(self, window_title: str, app_name: str) -> str:
        """Try to extract project name from window title"""
        # Look for common patterns
        import re
        
        # VSCode pattern: "filename - folder - Visual Studio Code"
        vscode_match = re.search(r' - ([^-]+) - (?:Visual Studio Code|VS Code|Cursor)', window_title)
        if vscode_match:
            return vscode_match.group(1).strip()
        
        # IntelliJ/PyCharm pattern: "project_name – filename"
        jetbrains_match = re.search(r'^([^–]+) – ', window_title)
        if jetbrains_match and any(ide in app_name.lower() for ide in ['intellij', 'pycharm', 'webstorm']):
            return jetbrains_match.group(1).strip()
        
        # Git pattern
        git_match = re.search(r'\\([^\\]+)\\\.git', window_title)
        if git_match:
            return git_match.group(1)
        
        # URL pattern for GitHub/GitLab
        repo_match = re.search(r'github\.com/[^/]+/([^/\s]+)', window_title)
        if repo_match:
            return repo_match.group(1)
        
        # Folder path pattern
        folder_match = re.search(r'\\([^\\]+)\\[^\\]+\.[a-z]+$', window_title)
        if folder_match:
            return folder_match.group(1)
        
        return "general"
    
    def save_to_database(self, activities: List[Dict]) -> int:
        """Save activities to database"""
        if not activities:
            return 0
        
        saved_count = 0
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            insert_query = """
                INSERT INTO activity_records (
                    developer_id, application_name, window_title,
                    url, file_path, duration, timestamp,
                    category, project_name, project_type,
                    created_at
                ) VALUES (
                    %(developer_id)s, %(application_name)s, %(window_title)s,
                    %(url)s, %(file_path)s, %(duration)s, %(timestamp)s,
                    %(category)s, %(project_name)s, %(project_type)s,
                    %(created_at)s
                )
                ON CONFLICT (developer_id, timestamp, application_name, window_title) 
                DO NOTHING
            """
            
            for activity in activities:
                try:
                    # Remove bucket_name as it's not in the table
                    activity_data = {k: v for k, v in activity.items() if k != 'bucket_name'}
                    cur.execute(insert_query, activity_data)
                    saved_count += 1
                except Exception as e:
                    print(f"⚠️  Error saving activity: {e}")
                    continue
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ Saved {saved_count} activities to database")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
        
        return saved_count
    
    def send_to_api(self, activities: List[Dict]) -> bool:
        """Send activities to API endpoint"""
        if not activities:
            return True
        
        try:
            payload = {
                'name': self.developer_name,
                'token': self.api_token,
                'data': activities,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Sent {len(activities)} activities to API")
                    return True
                else:
                    print(f"❌ API error: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ API returned status {response.status_code}")
            
        except Exception as e:
            print(f"❌ Error sending to API: {e}")
        
        return False
    
    def sync_once(self):
        """Perform a single sync"""
        print(f"\n🔄 Syncing ActivityWatch data for {self.developer_name}...")
        
        # Get data
        activities = self.get_activitywatch_data()
        
        if activities:
            print(f"📊 Processed {len(activities)} activities")
            
            # Show category breakdown
            categories = {}
            for activity in activities:
                cat = activity['category']
                categories[cat] = categories.get(cat, 0) + 1
            
            print("📈 Category breakdown:")
            for cat, count in categories.items():
                print(f"   - {cat}: {count} activities")
            
            # Save to database
            saved = self.save_to_database(activities)
            
            # Send to API
            self.send_to_api(activities)
            
        else:
            print("📝 No new activities to sync")
    
    def continuous_sync(self, interval_minutes: int = 5):
        """Run continuous sync"""
        print(f"🚀 Starting continuous sync every {interval_minutes} minutes")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 50)
        
        try:
            while True:
                self.sync_once()
                
                next_sync = datetime.now() + timedelta(minutes=interval_minutes)
                print(f"\n⏳ Next sync at {next_sync.strftime('%H:%M:%S')}")
                print("-" * 50)
                
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n🛑 Sync stopped by user")

def main():
    # Configuration
    DEVELOPER_NAME = "mrunali"  # Change this
    API_TOKEN = "YOUR_TOKEN_HERE"  # Change this
    
    # Create sync instance
    sync = EnhancedActivityWatchSync(DEVELOPER_NAME, API_TOKEN)
    
    # Run continuous sync
    sync.continuous_sync()

if __name__ == "__main__":
    main()
