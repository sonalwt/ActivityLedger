more +!PYSTART! "%~f0" > "%TEMP%\_backfill_afk.py"
%PYTHON_CMD% "%TEMP%\_backfill_afk.py" "!DEV_ID!" "!DEV_TOKEN!"
del "%TEMP%\_backfill_afk.py" 2>nul

echo.
echo ============================================
pause
exit /b

#PYTHON_SCRIPT_START
import requests, sys
from datetime import datetime, timedelta, timezone

DEV_ID = sys.argv[1]
TOKEN = sys.argv[2]
SERVER = "https://api-timesheet.firsteconomy.com/api/sync"
AW = "http://localhost:5600/api/0"
DAYS = 30

end = datetime.now(timezone.utc)
start = end - timedelta(days=DAYS)
print(f"Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({DAYS} days)")
print()

# Find AFK bucket
try:
    buckets = requests.get(f"{AW}/buckets/", timeout=10).json()
except Exception as e:
    print(f"ERROR connecting to ActivityWatch: {e}")
    sys.exit(1)

afk_buckets = [b for b in buckets if "afk" in b.lower()]
if not afk_buckets:
    print("ERROR: No AFK watcher bucket found.")
    sys.exit(1)

# Fetch AFK events day by day
all_events = []
for bucket in afk_buckets:
    print(f"Fetching from {bucket}...")
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=1), end)
        params = {
            "start": current.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": 50000
        }
        try:
            events = requests.get(
                f"{AW}/buckets/{bucket}/events",
                params=params, timeout=30
            ).json()
            count = 0
            for ev in events:
                d = ev.get("data", {})
                s = d.get("status", "")
                dur = ev.get("duration", 0)
                if s in ("afk", "not-afk") and dur >= 1:
                    all_events.append({
                        "status": s,
                        "duration": dur,
                        "timestamp": ev.get("timestamp", "")
                    })
                    count += 1
            if count:
                print(f"  {current.strftime('%Y-%m-%d')}: {count} events")
        except Exception as e:
            print(f"  {current.strftime('%Y-%m-%d')}: Error - {e}")
        current = chunk_end

print()
not_afk = sum(1 for e in all_events if e["status"] == "not-afk")
afk_count = sum(1 for e in all_events if e["status"] == "afk")
print(f"Total: {len(all_events)} events (active: {not_afk}, idle: {afk_count})")

if not all_events:
    print("No AFK data found. Nothing to send.")
    sys.exit(0)

# Send to server
print()
print("Sending to server...")
total_saved = 0
batch_size = 2000
for i in range(0, len(all_events), batch_size):
    batch = all_events[i:i+batch_size]
    payload = {
        "name": DEV_ID,
        "token": TOKEN,
        "data": [],
        "afk_data": batch,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        r = requests.post(
            SERVER, json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        result = r.json()
        if result.get("success"):
            saved = result.get("afk_saved", 0)
            total_saved += saved
            print(f"  Batch {i//batch_size+1}: saved {saved}")
        else:
            print(f"  Batch {i//batch_size+1}: ERROR - {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"  Batch {i//batch_size+1}: FAILED - {e}")

print()
print(f"Done! Total AFK events saved: {total_saved}")
print("Your dashboard will now show accurate active time.")
