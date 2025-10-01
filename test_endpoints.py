import requests
import json
from datetime import datetime

print("\n=== Testing ActivityWatch Sync Endpoints ===\n")

# Test payload
test_payload = {
    "name": "test",
    "token": "AWToken_test",
    "data": [],
    "timestamp": datetime.utcnow().isoformat() + "Z"
}

# Endpoints to test
endpoints = [
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/",
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/"
]

working_endpoint = None

for endpoint in endpoints:
    print(f"\nTesting: {endpoint}")
    print("-" * 60)
    
    # Test without following redirects
    try:
        response = requests.post(
            endpoint, 
            json=test_payload, 
            allow_redirects=False,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 308:
            print("✗ 308 Redirect detected!")
            if 'Location' in response.headers:
                print(f"  Redirects to: {response.headers['Location']}")
        
        elif response.status_code in [400, 401, 422]:
            print("✓ Endpoint works! (auth/validation error is expected)")
            working_endpoint = endpoint
            print(f"Response: {response.text[:200]}")
        
        elif response.status_code == 200:
            print("✓ Success! This endpoint works perfectly.")
            working_endpoint = endpoint
            print(f"Response: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

print("\n" + "=" * 60)
print("\nSUMMARY:")
print("=" * 60)

if working_endpoint:
    print(f"\n✓ WORKING ENDPOINT FOUND: {working_endpoint}")
    print(f"\nUpdate your sync.ps1 to use:")
    print(f'$SERVER_URL = "{working_endpoint}"')
else:
    print("\n✗ No working endpoint found!")
    print("Please check your server configuration.")

print("\nNOTE: The 308 redirect is likely caused by FastAPI's")
print("automatic trailing slash redirect. To fix this on the")
print("server side, set redirect_slashes=False in your FastAPI app.")
print("")