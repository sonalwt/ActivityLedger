# check_api_logs.py
# Guide to checking API logs for the 500 error

print("=== How to Debug the 500 Error on Your Server ===\n")

print("1. SSH into your server:")
print("   ssh your-user@timesheet.firsteconomy.com")

print("\n2. Check the application logs:")
print("   # If using systemd:")
print("   sudo journalctl -u your-timesheet-service -f")
print("   \n   # If using PM2:")
print("   pm2 logs timesheet")
print("   \n   # If using Docker:")
print("   docker logs -f timesheet-container")
print("   \n   # If using traditional logs:")
print("   tail -f /var/log/timesheet/error.log")

print("\n3. Check the web server logs:")
print("   # Nginx:")
print("   sudo tail -f /var/log/nginx/error.log")
print("   \n   # Apache:")
print("   sudo tail -f /var/log/apache2/error.log")

print("\n4. Common 500 error causes and fixes:")

print("\n   A) Database Connection Error:")
print("      - Check if database is running")
print("      - Verify connection credentials")
print("      - Check if connection pool is exhausted")

print("\n   B) Query Error (most likely):")
print("      - Case sensitivity: 'riddhidhakhara' vs 'RiddhiDhakhara'")
print("      - Missing columns: category, application_name")
print("      - Date format issues")

print("\n   C) Memory/Resource Issues:")
print("      - Check server memory: free -h")
print("      - Check disk space: df -h")
print("      - Restart the application")

print("\n5. Quick test on the server:")
print("""
   # Create a test script on the server:
   python3 << 'EOF'
import psycopg2
import json
from datetime import date

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    database="timesheet_db",
    user="your_db_user",
    password="your_db_password"
)

cur = conn.cursor()

# Test the problematic query
developer_id = 'riddhidhakhara'
start_date = '2025-09-30'
end_date = '2025-10-08'

try:
    # Case-insensitive query
    cur.execute('''
        SELECT COUNT(*) 
        FROM activity_records 
        WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(%s)
        AND DATE(timestamp) BETWEEN %s AND %s
    ''', (developer_id, start_date, end_date))
    
    count = cur.fetchone()[0]
    print(f"Found {count} records")
    
except Exception as e:
    print(f"Error: {e}")

cur.close()
conn.close()
EOF
""")

print("\n6. Emergency fix - Update the API code:")
print("""
   Find your API endpoint file and update the query to be case-insensitive.
   
   Look for something like:
   - api/routes/activity.py
   - controllers/activityController.js
   - src/api/activities.js
   
   And change queries from:
   WHERE developer_id = ?
   
   To:
   WHERE LOWER(CAST(developer_id AS VARCHAR)) = LOWER(?)
""")
