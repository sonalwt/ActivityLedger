import requests
import json
import time
from datetime import datetime, timedelta, timezone

# Configuration
DEVELOPER_NAME = "ankita gholap"
API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
LOCAL_AW = "http://localhost:5600/api/0"

# Test endpoints to find one that works
print("=== ActivityWatch Sync (Python Version) ===")
print("Testing server endpoints...")

endpoints = [
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/",
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/"
]

SERVER_URL = None
test_payload = {
    "name": "test",
    "token": "test",
    "data": [],
    "timestamp": datetime.utcnow().isoformat() + "Z"
}

for endpoint in endpoints:
    print(f"\nTesting: {endpoint}")
    try:
        # Python requests follows redirects by default
        response = requests.post(endpoint, json=test_payload, timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code in [200, 400, 401, 422]:
            print(f"  ✓ This endpoint works!")
            SERVER_URL = endpoint
            break
            
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error: {str(e)}")

if not SERVER_URL:
    print("\n❌ No working endpoint found!")
    print("Please contact your server administrator.")
    input("Press Enter to exit...")
    exit()

print(f"\nUsing endpoint: {SERVER_URL}")
print("=" * 60)

def send_activity_data():
    try:
        # Get buckets
        print(f"{LOCAL_AW}/buckets")
        buckets_response = requests.get(f"{LOCAL_AW}/buckets", timeout=10)
        buckets = list(buckets_response.json().keys())
        print(f"Found {len(buckets)} ActivityWatch buckets")
        
        # Time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=6)
        start_iso = start_time.isoformat().replace("+00:00", "Z")
        end_iso = end_time.isoformat().replace("+00:00", "Z")
        
        # Collect events
        all_events = []
        for bucket in buckets:
            try:
                events_url = f"{LOCAL_AW}/buckets/{bucket}/events?start={start_iso}&end={end_iso}"
                events_response = requests.get(events_url, timeout=10)
                events = events_response.json()
                
                if events:
                    all_events.extend(events)
                    print(f"  - {bucket}: {len(events)} events", flush=True)
            except:
                pass  # Skip bucket on error
        
        if all_events:
            print(f"Sending {len(all_events)} events to server...")
            
            payload = {
                "name": DEVELOPER_NAME,
                "token": API_TOKEN,
                "data": all_events,
                "timestamp": end_time.isoformat().replace("+00:00", "Z")
            }
            
            # Send to server
            response = requests.post(SERVER_URL, json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"[SUCCESS] Synced {len(all_events)} events successfully")
                else:
                    print(f"Server error: {result.get('error', 'Unknown error')}")
            else:
                print(f"HTTP Error {response.status_code}: {response.text[:200]}")
                
        else:
            print("No new data to sync")
            
    except Exception as e:
        print(f"Sync error: {str(e)}")

# Main loop
print("=" * 40)
print(f"ActivityWatch Sync for {DEVELOPER_NAME}")
print(f"Server: {SERVER_URL}")
print("=" * 40)
print("Press Ctrl+C to stop")
print()

while True:
    send_activity_data()
    next_sync = datetime.now() + timedelta(minutes=5)
    print(f"\nWaiting 5 minutes... (next sync at {next_sync.strftime('%H:%M:%S')})")
    print("-" * 40)
    time.sleep(300)