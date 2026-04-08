@echo off
setlocal enabledelayedexpansion
title AFK Data Backfill - Timesheet
echo ============================================
echo   AFK Data Backfill Tool
echo   Sends keyboard/mouse activity data to server
echo ============================================
echo.

:: Check if Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH.
        echo Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

:: Check if requests module is available
%PYTHON_CMD% -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required module: requests...
    %PYTHON_CMD% -m pip install requests -q
)

:: Check if ActivityWatch is running
curl -s http://localhost:5600/api/0/buckets/ >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: ActivityWatch is not running on this machine.
    echo Please start ActivityWatch first and try again.
    pause
    exit /b 1
)

echo Select your name:
echo.
echo   1. Riddhi Dhakhara
echo   2. Mrunali
echo   3. Ankita Gholap
echo   4. Sonal
echo.
set /p CHOICE="Enter number (1-4): "

if "!CHOICE!"=="1" (
    set DEV_ID=riddhidhakhara
    set DEV_TOKEN=AWToken_vkeY5pcMmyvUkfh_6Jh8JMHVOWhyz0YirwxNuw2NhLI
)
if "!CHOICE!"=="2" (
    set DEV_ID=mrunali
    set DEV_TOKEN=AWToken_1CEPGEXcx1rlfDHHAtQjbMotUMn5MDAajhBYkoWCur0
)
if "!CHOICE!"=="3" (
    set DEV_ID=ankita_gholap
    set DEV_TOKEN=AWToken_k6kNaTg86QRjwgmxktgajNd4yj_IDMnxRCvSWiOqA64
)
if "!CHOICE!"=="4" (
    set DEV_ID=sonal
    set DEV_TOKEN=AWToken_1UUMoHeIyPHecX84YshfRg
)

if "!DEV_ID!"=="" (
    echo Invalid choice. Exiting.
    pause
    exit /b 1
)

echo.
echo Backfilling AFK data for: !DEV_ID!
echo.

:: Extract embedded Python script from this bat file and run it
set BATFILE=%~f0
set TMPPY=%TEMP%\_backfill_afk_tmp.py
%PYTHON_CMD% -c "f=open(r'%BATFILE%','r',encoding='utf-8');lines=f.readlines();f.close();idx=[i for i,l in enumerate(lines) if l.strip()=='#PY_CODE_BELOW'][-1];g=open(r'%TMPPY%','w',encoding='utf-8');g.writelines(lines[idx+1:]);g.close()"
%PYTHON_CMD% "%TMPPY%" "!DEV_ID!" "!DEV_TOKEN!"
del "%TMPPY%" 2>nul

echo.
echo ============================================
pause
exit /b 0

#PY_CODE_BELOW
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
