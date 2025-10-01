# sync_config.ps1 - Configuration file for sync.ps1

# Developer credentials
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"

# Server configuration
# Comment/uncomment the URL you want to use

# Option 1: HTTP (works, avoids 308 redirect)
$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"

# Option 2: HTTPS (may cause 308 redirect)
# $SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"

# Option 3: HTTPS with trailing slash (try if above doesn't work)
# $SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync/"

# ActivityWatch local URL
$LOCAL_AW = "http://localhost:5600/api/0"

# Sync interval (minutes)
$SYNC_INTERVAL = 5

# Display configuration
Write-Host "Configuration loaded:" -ForegroundColor Cyan
Write-Host "Developer: $DEVELOPER_NAME"
Write-Host "Server URL: $SERVER_URL"
Write-Host "Sync interval: $SYNC_INTERVAL minutes"
Write-Host ""