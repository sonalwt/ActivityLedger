# test_dashboard_data.py
# Test what data the dashboard API is actually returning

import requests
import json
from datetime import date

# Configuration
API_URL = "http://localhost:5001"
DEVELOPERS = ["ankita gholap", "RiddhiDhakhara", "ankita_gholap"]

def test_dashboard_api():
    """Test dashboard API endpoints"""
    
    print("=== Testing Dashboard API ===\n")
    
    # 1. Test connection
    print("1. Testing API connection...")
    try:
        response = requests.get(f"{API_URL}/api/test-connection")
        if response.status_code == 200:
            data = response.json()
            print("   ✓ API connected successfully")
            print(f"   Database: {data.get('database_version', 'Unknown')}")
            print(f"   Total records: {data.get('activity_records_count', 0)}")
            print(f"   Sample developers: {data.get('sample_developer_ids', [])}")
        else:
            print(f"   ❌ API error: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        print("   Make sure the dashboard API is running on port 5001")
        return
    
    # 2. Test developers endpoint
    print("\n2. Testing developers endpoint...")
    try:
        response = requests.get(f"{API_URL}/api/developers")
        if response.status_code == 200:
            developers = response.json()
            print(f"   Found {len(developers)} developers:")
            for dev in developers:
                print(f"   - {dev['id']}: {dev['name']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Test dashboard data for each developer
    print("\n3. Testing dashboard data for each developer...")
    today = date.today().isoformat()
    
    for dev_id in DEVELOPERS:
        print(f"\n   Developer: {dev_id}")
        print(f"   -----------------")
        
        # Test today's data
        try:
            response = requests.get(f"{API_URL}/api/dashboard/{dev_id}?date={today}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Today ({today}):")
                print(f"   - Total hours: {data.get('total_hours', 0)}")
                print(f"   - Productivity: {data.get('team_productivity', 0)}%")
                print(f"   - Active devs: {data.get('active_developers', 0)}")
                
                # Check app breakdown
                apps = data.get('application_breakdown', [])
                if apps:
                    print(f"   - Top apps: {', '.join([app['name'] for app in apps[:3]])}")
                else:
                    print("   - No application data")
                    
                # Check if there's any activity
                timeline = data.get('activity_timeline', [])
                active_hours = sum(1 for h in timeline if h.get('value', 0) > 0)
                print(f"   - Active hours: {active_hours}/24")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test sample data
        try:
            response = requests.get(f"{API_URL}/api/sample-data/{dev_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"\n   Sample data:")
                print(f"   - Records found: {data.get('sample_count', 0)}")
                samples = data.get('data', [])
                if samples:
                    for i, sample in enumerate(samples[:3]):
                        print(f"   - {sample.get('timestamp', 'N/A')}: {sample.get('app', 'Unknown')} ({sample.get('duration', 0)}s)")
        except Exception as e:
            print(f"   ❌ Error getting sample data: {e}")
    
    print("\n4. DIAGNOSIS:")
    print("   If hours show as 0:")
    print("   - Check if duration values are set in the database")
    print("   - Check if data exists for today's date")
    print("   - Try selecting a different date in the dashboard")
    print("   - Run the complete_dashboard_fix.bat script")

if __name__ == "__main__":
    test_dashboard_api()
