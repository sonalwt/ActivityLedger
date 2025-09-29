# test_308_endpoints.py
import requests

# Test common endpoints that might cause 308 redirects
base_url = "http://localhost:8000"
endpoints_to_test = [
    ("/token", "POST"),
    ("/token/", "POST"),
    ("/register", "POST"),
    ("/register/", "POST"),
    ("/api/sync", "POST"),
    ("/api/sync/", "POST"),
    ("/api/register-developer", "POST"),
    ("/api/register-developer/", "POST"),
    ("/users/me", "GET"),
    ("/users/me/", "GET"),
]

print("=== Testing for 308 Redirects ===\n")
print("Make sure your backend is running on http://localhost:8000\n")

for endpoint, method in endpoints_to_test:
    url = base_url + endpoint
    
    try:
        if method == "GET":
            response = requests.get(url, allow_redirects=False)
        else:
            response = requests.post(url, json={}, allow_redirects=False)
        
        if response.status_code == 308:
            print(f"❌ 308 REDIRECT: {method} {endpoint}")
            print(f"   Redirects to: {response.headers.get('location')}")
        elif response.status_code in [200, 401, 422, 405]:
            print(f"✅ OK: {method} {endpoint} -> {response.status_code}")
        else:
            print(f"⚠️  {method} {endpoint} -> {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {url} - Is the backend running?")
        break
    except Exception as e:
        print(f"❌ Error testing {endpoint}: {e}")

print("\n=== Test Complete ===")
print("\nIf you see 308 redirects above, check if the redirect is adding/removing trailing slashes.")
