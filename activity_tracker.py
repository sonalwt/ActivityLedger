#!/usr/bin/env python3
# Simple Activity Tracker Client
# Save this as: activity_tracker.py

import requests
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

class SimpleTracker:
    def __init__(self, api_url, api_token, developer_id):
        self.api_url = api_url
        self.api_token = api_token
        self.developer_id = developer_id
        self.headers = {"Authorization": f"Bearer {api_token}"}
    
    def get_activitywatch_data(self):
        """Get data from local ActivityWatch"""
        try:
            # Get data from ActivityWatch API
            aw_url = "http://localhost:5600/api/0"
            
            # Get buckets
            buckets = requests.get(f"{aw_url}/buckets/").json()
            
            activities = []
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            
            for bucket_name in buckets:
                if 'afk' in bucket_name:
                    continue
                
                # Get recent events
                params = {
                    'start': one_hour_ago.isoformat(),
                    'end': now.isoformat(),
                    'limit': 100
                }
                
                events = requests.get(f"{aw_url}/buckets/{bucket_name}/events", params=params).json()
                
                for event in events:
                    if event.get('duration', 0) < 5:  # Skip short activities
                        continue
                    
                    data = event.get('data', {})
                    activities.append({
                        "application_name": data.get('app', 'Unknown'),
                        "window_title": data.get('title', ''),
                        "duration": event.get('duration', 0),
                        "timestamp": event.get('timestamp'),
                        "category": "other"
                    })
            
            return activities
        except Exception as e:
            print(f"Error getting ActivityWatch data: {e}")
            return []
    
    def upload_activities(self, activities):
        """Upload activities to server"""
        if not activities:
            return True
        
        try:
            response = requests.post(
                f"{self.api_url}/activity/upload",
                headers=self.headers,
                json=activities
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Uploaded {result.get('processed', 0)} activities")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def run(self):
        """Main tracking loop"""
        print(f"🚀 Starting tracker for {self.developer_id}")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                # Get recent activities
                activities = self.get_activitywatch_data()
                
                # Upload to server
                if activities:
                    self.upload_activities(activities)
                else:
                    print("📊 No new activities")
                
                # Wait 5 minutes
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\n👋 Stopping tracker...")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(60)

# Configuration
CONFIG = {
    "api_url": "https://api-timesheet.firsteconomy.com/api/multi-dev",
    "api_token": "REPLACE_WITH_YOUR_TOKEN",
    "developer_id": "your_name"
}

if __name__ == "__main__":
    # Check if config file exists
    config_file = Path("config.json")
    if config_file.exists():
        with open(config_file) as f:
            CONFIG = json.load(f)
    else:
        # Create sample config
        with open(config_file, 'w') as f:
            json.dump(CONFIG, f, indent=2)
        print(f"📝 Created config.json - please edit it with your token")
        exit(1)
    
    # Start tracker
    tracker = SimpleTracker(
        CONFIG["api_url"],
        CONFIG["api_token"], 
        CONFIG["developer_id"]
    )
    tracker.run()
