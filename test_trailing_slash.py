# test_trailing_slash.py
import requests

sync_url_base = "https://api-timesheet.firsteconomy.com"
test_payload = {
    "name": "test",
    "token": "test",
    "data": [],
    "timestamp": "2024-01-01T00:00:00Z"
}

endpoints_to_test = [
    "/api/sync",      # Without trailing slash
    "/api/sync/",     # With trailing slash
]

print("=== Testing Trailing Slash Redirects ===\n")

for endpoint in endpoints_to_test:
    url = sync_url_base + endpoint
    print(f"\nTesting: {url}")
    
    try:
        response = requests.post(url, json=test_payload, allow_redirects=False, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code in [301, 302, 307, 308]:
            redirect_to = response.headers.get('Location', 'Not specified')
            print(f"Redirects to: {redirect_to}")
            
            if response.status_code == 308:
                print("⚠️  This is the problematic 308 redirect!")
                
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*60)
print("\nIf you see a 308 redirect, update your sync script to use the")
print("exact URL shown in 'Redirects to' field above.")
