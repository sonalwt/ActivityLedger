# test_https_redirect_location.py
import requests

print("=== Testing HTTPS Redirect Location ===\n")

url = "https://api-timesheet.firsteconomy.com/api/sync"
test_payload = {
    "name": "ankita gholap",
    "token": "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0",
    "data": [],
    "timestamp": "2024-01-01T00:00:00Z"
}

print(f"Testing: {url}")
print("-" * 60)

# Make request without following redirects
try:
    response = requests.post(url, json=test_payload, allow_redirects=False, verify=True, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    if response.status_code in [301, 302, 307, 308]:
        location = response.headers.get('Location', 'Not specified')
        print(f"\n⚠️  REDIRECT TO: {location}")
        print(f"\nUpdate your sync.ps1 to use this URL:")
        print(f'$SERVER_URL = "{location}"')
        
        # Try the redirect location
        print(f"\nTesting redirect location...")
        try:
            response2 = requests.post(location, json=test_payload, timeout=10)
            print(f"Redirect location status: {response2.status_code}")
            if response2.status_code == 200:
                print("✅ The redirect location works!")
        except Exception as e:
            print(f"Error testing redirect location: {e}")
            
except requests.exceptions.SSLError as e:
    print(f"❌ SSL Error: {e}")
    print("\nYour server might not have proper SSL certificates configured.")
    print("Try using HTTP instead, or fix SSL certificates on the server.")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
print("\nPossible solutions:")
print("1. Set up proper SSL certificates on your server")
print("2. Configure Apache to handle HTTPS without redirects")
print("3. Use the redirect location URL in your sync script")
print("4. Use HTTP if your backend doesn't require HTTPS")
