# test_sync_endpoint.py
import requests

print("=== Testing Sync Endpoint 308 Redirect ===\n")

# The URL from your sync script
sync_url = "https://api-timesheet.firsteconomy.com/api/sync"
developer_name = "ankita gholap"
api_token = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"

# Test payload
test_payload = {
    "name": developer_name,
    "token": api_token,
    "data": [],
    "timestamp": "2024-01-01T00:00:00.000Z"
}

print(f"Testing: {sync_url}")
print("-" * 60)

# Test without following redirects
try:
    response = requests.post(
        sync_url, 
        json=test_payload,
        allow_redirects=False,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 308:
        redirect_location = response.headers.get('Location', 'Not specified')
        print(f"❌ 308 PERMANENT REDIRECT detected!")
        print(f"   Redirects to: {redirect_location}")
        print("\nSOLUTION: Update your sync script to use:")
        print(f"   $SERVER_URL = \"{redirect_location}\"")
        
    elif response.status_code in [301, 302, 307]:
        redirect_location = response.headers.get('Location', 'Not specified')
        print(f"⚠️  {response.status_code} Redirect detected")
        print(f"   Redirects to: {redirect_location}")
        
    elif response.status_code == 200:
        print("✅ Endpoint is working correctly (200 OK)")
        print(f"Response: {response.text[:100]}...")
        
    else:
        print(f"Response: {response.status_code}")
        print(f"Body: {response.text[:200]}...")
        
except requests.exceptions.SSLError:
    print("❌ SSL Error - trying with HTTP instead")
    # Try HTTP
    http_url = sync_url.replace('https://', 'http://')
    try:
        response = requests.post(http_url, json=test_payload, allow_redirects=False, timeout=10)
        print(f"\nHTTP Status: {response.status_code}")
        if response.status_code == 308:
            print(f"HTTP also redirects to: {response.headers.get('Location')}")
    except Exception as e:
        print(f"HTTP also failed: {e}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test other possible endpoints
print("\n" + "="*60)
print("Testing alternative endpoints:")
alternative_endpoints = [
    "https://api-timesheet.firsteconomy.com/api/sync/",  # With trailing slash
    "http://api-timesheet.firsteconomy.com/api/sync",   # HTTP instead of HTTPS
    "https://timesheet-api.firsteconomy.com/api/sync",  # Different subdomain
    "https://api-timesheet.firsteconomy.com/sync",      # Without /api prefix
]

for endpoint in alternative_endpoints:
    try:
        response = requests.post(endpoint, json=test_payload, allow_redirects=False, timeout=5)
        if response.status_code == 200:
            print(f"✅ WORKING: {endpoint} (Status: {response.status_code})")
        elif response.status_code in [301, 302, 307, 308]:
            print(f"   {endpoint} → {response.headers.get('Location')} ({response.status_code})")
        else:
            print(f"   {endpoint} → Status {response.status_code}")
    except:
        print(f"   {endpoint} → Connection failed")
