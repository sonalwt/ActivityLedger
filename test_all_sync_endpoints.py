# test_all_sync_endpoints.py
import requests
import json

print("=== Testing All Possible Sync Endpoints ===\n")

base_url = "https://api-timesheet.firsteconomy.com"
developer_name = "ankita_gholap"
api_token = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"

# Different endpoint configurations to test
test_configs = [
    {
        "name": "Original /api/sync",
        "url": f"{base_url}/api/sync",
        "payload": {
            "name": developer_name,
            "token": api_token,
            "data": [],
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "headers": {
            "Content-Type": "application/json"
        }
    },
    {
        "name": "Stateless Webhook",
        "url": f"{base_url}/api/v1/activitywatch/webhook",
        "payload": {
            "aw-watcher-window": []  # Webhook expects bucket data
        },
        "headers": {
            "Content-Type": "application/json",
            "Developer-ID": developer_name,
            "Authorization": f"Bearer {api_token}"
        }
    },
    {
        "name": "With trailing slash",
        "url": f"{base_url}/api/sync/",
        "payload": {
            "name": developer_name,
            "token": api_token,
            "data": [],
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "headers": {
            "Content-Type": "application/json"
        }
    },
    {
        "name": "Health check",
        "url": f"{base_url}/api/v1/health",
        "method": "GET",
        "headers": {}
    }
]

for config in test_configs:
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print(f"URL: {config['url']}")
    
    try:
        method = config.get('method', 'POST')
        
        if method == 'GET':
            response = requests.get(
                config['url'],
                headers=config.get('headers', {}),
                allow_redirects=False,
                timeout=10
            )
        else:
            response = requests.post(
                config['url'],
                json=config.get('payload'),
                headers=config.get('headers', {}),
                allow_redirects=False,
                timeout=10
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code in [301, 302, 307, 308]:
            redirect_location = response.headers.get('Location', 'Not specified')
            print(f"⚠️  Redirects to: {redirect_location}")
            
            if response.status_code == 308:
                print("❌ This is a 308 PERMANENT REDIRECT!")
                print("\nTrying the redirect location directly...")
                
                # Try the redirect location
                if method == 'GET':
                    redirect_response = requests.get(
                        redirect_location,
                        headers=config.get('headers', {}),
                        allow_redirects=False,
                        timeout=10
                    )
                else:
                    redirect_response = requests.post(
                        redirect_location,
                        json=config.get('payload'),
                        headers=config.get('headers', {}),
                        allow_redirects=False,
                        timeout=10
                    )
                
                print(f"Redirect location status: {redirect_response.status_code}")
                if redirect_response.status_code == 200:
                    print("✅ The redirect location works! Use this URL in your sync script.")
                    
        elif response.status_code == 200:
            print("✅ Success! This endpoint works without redirects.")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response: {response.text[:100]}...")
                
        elif response.status_code == 401:
            print("❌ Authentication failed (401)")
            
        elif response.status_code == 422:
            print("⚠️  Validation error (422) - might need different payload format")
            
        else:
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*60)
print("\nRECOMMENDATIONS:")
print("1. Use the endpoint that returns 200 without redirects")
print("2. If all endpoints redirect with 308, use the redirect location URL")
print("3. Consider using the stateless webhook endpoint if it works")
