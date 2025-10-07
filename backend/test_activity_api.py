import requests
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# API base URL
API_BASE = "http://localhost:8000"

print("=== Testing Activity API Endpoints ===")

# First, get list of developers
print("\n1. Getting developers list...")
try:
    response = requests.get(f"{API_BASE}/api/developers-orm")
    if response.ok:
        data = response.json()
        developers = data.get('developers', [])
        print(f"   Found {len(developers)} developers")
        
        if developers:
            # Test with first developer
            test_dev = developers[0]
            dev_id = test_dev.get('id')
            dev_name = test_dev.get('name')
            
            print(f"\n2. Testing with developer: {dev_name} (ID: {dev_id})")
            
            # Test activity data endpoint
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            print(f"\n3. Fetching activity data for last 7 days...")
            activity_response = requests.get(
                f"{API_BASE}/api/activity-data/{dev_id}",
                params={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            )
            
            if activity_response.ok:
                activity_data = activity_response.json()
                print(f"   Total activities: {activity_data.get('total_activities', 0)}")
                print(f"   Total time: {activity_data.get('total_time', 0)} seconds")
                
                # Show category breakdown
                breakdown = activity_data.get('category_breakdown', {})
                print("\n   Category Breakdown:")
                for category, stats in breakdown.items():
                    print(f"      {category}: {stats.get('percentage', 0)}% ({stats.get('hours', 0)} hours)")
                
                # Show sample activities
                activities = activity_data.get('data', [])
                if activities:
                    print(f"\n   Sample activities (showing first 5):")
                    for act in activities[:5]:
                        print(f"      - {act.get('application_name')} | {act.get('category')} | {act.get('duration', 0)}s")
                else:
                    print("\n   No activities found!")
            else:
                print(f"   Error fetching activities: {activity_response.status_code}")
                print(f"   Response: {activity_response.text}")
            
            # Test categories endpoint
            print(f"\n4. Fetching categorized activities...")
            categories_response = requests.get(
                f"{API_BASE}/api/activity-categories/{dev_id}",
                params={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            )
            
            if categories_response.ok:
                categories_data = categories_response.json()
                summary = categories_data.get('summary', {})
                
                print("\n   Categories Summary:")
                for category, stats in summary.items():
                    print(f"      {category}: {stats.get('percentage', 0)}% ({stats.get('hours', 0)} hours)")
            else:
                print(f"   Error fetching categories: {categories_response.status_code}")
                print(f"   Response: {categories_response.text}")
                
    else:
        print(f"   Error getting developers: {response.status_code}")
        print(f"   Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to API. Make sure your backend is running on http://localhost:8000")
except Exception as e:
    print(f"\n❌ Error: {e}")

# Test update categories endpoint
print("\n\n5. Testing category update endpoint...")
try:
    update_response = requests.post(f"{API_BASE}/api/update-activity-categories")
    if update_response.ok:
        result = update_response.json()
        print(f"   ✅ Updated {result.get('updated_count', 0)} activities")
    else:
        print(f"   ❌ Error: {update_response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
