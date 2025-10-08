# test_api_endpoints.py
# Test the API endpoints to see which one is failing

import requests
import json
from datetime import date, datetime

# Configuration - adjust based on your setup
BASE_URL = "http://localhost:5001"  # Change to your API URL
# BASE_URL = "https://timesheet.firsteconomy.com"  # If testing production

# Test data based on your screenshot
developer_id = "riddhidhakhara"  # lowercase version
developer_id_caps = "RiddhiDhakhara"  # capitalized version
start_date = "2025-09-30"
end_date = "2025-10-08"

print("=== Testing API Endpoints ===\n")

# Test 1: Basic connection
print("1. Testing API connection...")
try:
    response = requests.get(f"{BASE_URL}/api/test-connection", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Connected to database")
        print(f"   Total records: {data.get('activity_records_count', 'Unknown')}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Connection error: {str(e)}")

# Test 2: Developers endpoint
print("\n2. Testing developers endpoint...")
try:
    response = requests.get(f"{BASE_URL}/api/developers", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        developers = response.json()
        print(f"   Found {len(developers)} developers:")
        for dev in developers[:5]:  # Show first 5
            print(f"   - {dev.get('id')} : {dev.get('name')}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 3: Activity data endpoints (try different variations)
print("\n3. Testing activity data endpoints...")

# Different possible endpoint patterns
endpoints_to_test = [
    f"/api/activity/{developer_id}?start_date={start_date}&end_date={end_date}",
    f"/api/activity/{developer_id_caps}?start_date={start_date}&end_date={end_date}",
    f"/api/activities/{developer_id}?start={start_date}&end={end_date}",
    f"/api/dashboard/{developer_id}/activities?start_date={start_date}&end_date={end_date}",
    f"/api/developer/{developer_id}/activities?from={start_date}&to={end_date}",
]

for endpoint in endpoints_to_test:
    print(f"\n   Testing: {endpoint}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Success!")
            data = response.json()
            if isinstance(data, list):
                print(f"   Found {len(data)} activities")
            elif isinstance(data, dict):
                print(f"   Response keys: {list(data.keys())}")
        elif response.status_code == 404:
            print("   ⚠️ Endpoint not found")
        elif response.status_code == 500:
            print("   ❌ 500 Internal Server Error!")
            print(f"   Error: {response.text[:300]}")
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")

# Test 4: Dashboard data endpoint
print("\n4. Testing dashboard data endpoint...")
test_dates = [
    end_date,  # Oct 8, 2025
    "2025-10-01",  # Oct 1, 2025
    date.today().isoformat(),  # Today
]

for test_date in test_dates:
    print(f"\n   Testing date: {test_date}")
    for dev_id in [developer_id, developer_id_caps]:
        try:
            response = requests.get(f"{BASE_URL}/api/dashboard/{dev_id}?date={test_date}", timeout=5)
            print(f"   Developer '{dev_id}': Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"     Total hours: {data.get('total_hours', 0)}")
            elif response.status_code == 500:
                print(f"     ❌ Error: {response.text[:200]}")
        except Exception as e:
            print(f"     ❌ Failed: {str(e)}")

print("\n5. DEBUGGING TIPS:")
print("   - Check server logs for the actual error message")
print("   - Verify database connection in production")
print("   - Check if column names match (case sensitivity)")
print("   - Ensure all required columns exist in the database")
