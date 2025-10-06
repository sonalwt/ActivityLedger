import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API base URL
API_BASE = "http://localhost:8000"

print("=== Activity Categorization Update ===")
print(f"Connecting to: {API_BASE}")

try:
    # Call the update endpoint
    response = requests.post(f"{API_BASE}/api/update-activity-categories")
    
    if response.ok:
        result = response.json()
        print(f"\n✅ Success!")
        print(f"Updated {result['updated_count']} activities")
        print(f"Message: {result['message']}")
    else:
        print(f"\n❌ Error: HTTP {response.status_code}")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to the API. Make sure your backend is running on http://localhost:8000")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\nDone!")
