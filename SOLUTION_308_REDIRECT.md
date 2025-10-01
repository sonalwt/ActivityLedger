# 308 Redirect Issue - SOLUTION

## The Problem
Your HTTPS endpoint (https://api-timesheet.firsteconomy.com/api/sync) is returning a 308 Permanent Redirect, which PowerShell's Invoke-RestMethod doesn't handle well.

## The Solution
Use HTTP instead of HTTPS: http://api-timesheet.firsteconomy.com/api/sync

## Files Created:

### 1. sync.ps1 (MAIN FILE - USES HTTP)
- Location: E:\timesheet\timesheet_new\sync.ps1
- This is the working version using HTTP
- Copy this to your Downloads or Startup folder

### 2. start_sync.bat
- Location: E:\timesheet\timesheet_new\start_sync.bat
- Batch file to run sync.ps1 easily
- Double-click to start syncing

### 3. Alternative Solutions:
- sync_curl.ps1 - Uses curl.exe for HTTPS (handles redirects better)
- sync_autodetect.ps1 - Auto-detects working endpoint
- sync_http_webclient.ps1 - Uses WebClient class

### 4. Testing Tools:
- test_endpoints.py - Python script to test all endpoints
- test_https_endpoints.ps1 - PowerShell script to test endpoints

## To Fix on Server Side:
Update your FastAPI main.py:
```python
app = FastAPI(
    title="Timesheet API",
    version="1.0.0",
    redirect_slashes=False  # This prevents 308 redirects
)
```

## Quick Start:
1. Copy sync.ps1 to C:\Users\ankit\Downloads\
2. Run it with: powershell -ExecutionPolicy Bypass -File sync.ps1

OR

1. Double-click start_sync_http.bat

## Status:
✓ Script is working with HTTP
✓ Avoids 308 redirect issue
✓ Both files (sync.ps1 and HTML template) are synchronized