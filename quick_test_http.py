# quick_test_http.py
import requests

print("Testing HTTP endpoint directly...")
response = requests.post(
    "http://api-timesheet.firsteconomy.com/api/sync",
    json={
        "name": "ankita gholap",
        "token": "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0",
        "data": [],
        "timestamp": "2024-01-01T00:00:00Z"
    },
    timeout=10
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ HTTP endpoint works!")
    print(f"Response: {response.json()}")
else:
    print(f"Response: {response.text}")
