#!/usr/bin/env python3
"""
Fixed ActivityWatch Data Puller - Working Version
Auto-generated with working URL: http://127.0.0.1:5600
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment
load_dotenv('.env.local')
DATABASE_URL = os.getenv("DATABASE_URL")

# FIXED: Use the working ActivityWatch URL
ACTIVITYWATCH_URL = "http://127.0.0.1:5600"

def pull_activity_data():
    """Pull data from ActivityWatch and save to database"""
    print("🔄 Pulling ActivityWatch data...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        # Get buckets
        buckets_response = requests.get(f"{ACTIVITYWATCH_URL}/api/0/buckets/", timeout=10)
        if buckets_response.status_code != 200:
            print("❌ Could not fetch buckets")
            return
        
        buckets = buckets_response.json()
        print(f"📦 Found {len(buckets)} buckets")
        
        # Get recent data (last 1 hour)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        activities = []
        
        for bucket_name, bucket_info in buckets.items():
            # Skip AFK buckets
            if 'afk' in bucket_name.lower():
                continue
            
            try:
                events_url = f"{ACTIVITYWATCH_URL}/api/0/buckets/{bucket_name}/events"
                params = {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'limit': 100
                }
                
                events_response = requests.get(events_url, params=params, timeout=10)
                if events_response.status_code != 200:
                    continue
                
                events = events_response.json()
                print(f"📈 {bucket_name}: {len(events)} events")
                
                for event in events:
                    data = event.get('data', {})
                    duration = event.get('duration', 0)
                    
                    if duration < 5:  # Skip very short activities
                        continue
                    
                    activity = {
                        'developer_id': 'ankita_gholap',  # Your developer ID
                        'developer_name': 'Ankita Gholap',
                        'application_name': data.get('app', data.get('application', 'Unknown')),
                        'window_title': data.get('title', ''),
                        'duration': duration,
                        'timestamp': datetime.fromisoformat(event.get('timestamp', '').replace('Z', '+00:00')),
                        'bucket_name': bucket_name,
                        'category': 'general'
                    }
                    
                    activities.append(activity)
                    
            except Exception as e:
                print(f"⚠️  Error processing {bucket_name}: {e}")
                continue
        
        # Save to database
        if activities:
            with engine.connect() as conn:
                insert_query = text("""
                    INSERT INTO activity_records (
                        developer_id, developer_name, application_name, 
                        window_title, duration, timestamp, bucket_name, 
                        category, created_at
                    ) VALUES (
                        :developer_id, :developer_name, :application_name,
                        :window_title, :duration, :timestamp, :bucket_name,
                        :category, NOW()
                    )
                """)
                
                saved_count = 0
                for activity in activities:
                    try:
                        conn.execute(insert_query, activity)
                        saved_count += 1
                    except:
                        continue  # Skip duplicates
                
                conn.commit()
                print(f"💾 Saved {saved_count} activities to database")
        else:
            print("📝 No new activities to save")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    pull_activity_data()
