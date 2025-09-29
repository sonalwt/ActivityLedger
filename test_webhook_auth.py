# test_webhook_auth.py
import requests
import hashlib
import base64
from datetime import datetime

print("=== Testing Webhook Authentication ===\n")

# Test different authentication methods
developer_id = "ankita_gholap"
api_token = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
webhook_url = "https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"
validate_url = "https://api-timesheet.firsteconomy.com/api/v1/activitywatch/validate-token"

# First test token validation endpoint
print(f"Testing token validation endpoint...")
try:
    response = requests.get(
        validate_url,
        params={
            "developer_id": developer_id,
            "token": api_token
        },
        timeout=10
    )
    print(f"Validation endpoint status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Token valid: {data.get('token_valid')}")
        if not data.get('token_valid'):
            print("\n⚠️  Token is not valid for this developer ID!")
            print("The token might need to be regenerated using the stateless format.")
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test webhook with current token
print(f"\nTesting webhook with current token...")
test_payload = {
    "aw-watcher-window": [{
        "timestamp": "2024-01-01T00:00:00Z",
        "duration": 60,
        "data": {"app": "test", "title": "Test"}
    }]
}

headers = {
    "Content-Type": "application/json",
    "Developer-ID": developer_id,
    "Authorization": f"Bearer {api_token}"
}

try:
    response = requests.post(webhook_url, json=test_payload, headers=headers, timeout=10)
    print(f"Webhook status: {response.status_code}")
    if response.status_code == 401:
        print("❌ Authentication failed")
        print("\nTrying to generate stateless token...")
        
        # Try to generate a stateless token based on the validation logic
        master_secret = "TimesheetMaster2025258c362c"  # From your .env.production
        current_year = datetime.now().year
        
        # Generate token like the server expects
        token_input = f"{developer_id}:{master_secret}:{current_year}"
        token_hash = hashlib.sha256(token_input.encode()).hexdigest()
        token_bytes = bytes.fromhex(token_hash[:48])
        stateless_token = base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
        
        print(f"\nGenerated stateless token: AWToken_{stateless_token}")
        print("\nTesting with generated token...")
        
        headers["Authorization"] = f"Bearer AWToken_{stateless_token}"
        response2 = requests.post(webhook_url, json=test_payload, headers=headers, timeout=10)
        print(f"Status with generated token: {response2.status_code}")
        
        if response2.status_code == 200:
            print("✅ Success with generated token!")
            print(f"\nUse this token in your sync script:")
            print(f'$API_TOKEN = "AWToken_{stateless_token}"')
        else:
            print(f"Response: {response2.text[:200]}")
            
    elif response.status_code == 200:
        print("✅ Current token works!")
        print(f"Response: {response.json()}")
    else:
        print(f"Response: {response.text[:200]}")
        
except Exception as e:
    print(f"Error: {e}")
