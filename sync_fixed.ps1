# ActivityWatch Sync Script - Fixed Version with Error Handling
$DEVELOPER_NAME = "mrunali"
$API_TOKEN = "[PASTE_THE_GENERATED_TOKEN_HERE]"

# Server URLs to try (in order)
$SERVER_URLS = @(
    "http://api-timesheet.firsteconomy.com/api/sync",   # HTTP version
    "https://api-timesheet.firsteconomy.com/api/sync",  # HTTPS version
    "http://timesheet.firsteconomy.com/api/sync",       # Alternative domain
    "https://timesheet.firsteconomy.com/api/sync"       # Alternative HTTPS
)

$LOCAL_AW = "http://localhost:5600/api/0"

# Function to test server connectivity
function Test-ServerConnection {
    param($url)
    try {
        $response = Invoke-WebRequest -Uri $url -Method HEAD -TimeoutSec 5
        return $true
    } catch {
        return $false
    }
}

# Find working server URL
$WORKING_SERVER_URL = $null
Write-Host "Testing server connections..." -ForegroundColor Yellow
foreach ($url in $SERVER_URLS) {
    Write-Host "  Testing: $url" -NoNewline
    if (Test-ServerConnection $url) {
        Write-Host " [OK]" -ForegroundColor Green
        $WORKING_SERVER_URL = $url
        break
    } else {
        Write-Host " [FAILED]" -ForegroundColor Red
    }
}

if (-not $WORKING_SERVER_URL) {
    Write-Host ""
    Write-Host "ERROR: Cannot connect to any timesheet server!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible solutions:" -ForegroundColor Yellow
    Write-Host "1. Check if you're connected to the company VPN"
    Write-Host "2. Verify the server address with your IT department"
    Write-Host "3. Check your internet connection"
    Write-Host "4. Try adding the server to your hosts file"
    Write-Host ""
    Write-Host "To manually add to hosts file (as administrator):"
    Write-Host "  Add this line to C:\Windows\System32\drivers\etc\hosts:"
    Write-Host "  [SERVER_IP] api-timesheet.firsteconomy.com"
    Write-Host ""
    exit 1
}

$SERVER_URL = $WORKING_SERVER_URL
Write-Host "Using server: $SERVER_URL" -ForegroundColor Green
Write-Host ""

function Send-ActivityData {
    try {
        # Check if ActivityWatch is running
        try {
            $awInfo = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
        } catch {
            Write-Host "ERROR: Cannot connect to ActivityWatch on localhost:5600" -ForegroundColor Red
            Write-Host "Make sure ActivityWatch is running!" -ForegroundColor Yellow
            return
        }

        # Get buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets/" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                if ($events -and $events.Count -gt 0) {
                    foreach ($event in $events) {
                        if (-not $event.data) {
                            $event | Add-Member -NotePropertyName "data" -NotePropertyValue @{} -Force
                        }
                        
                        if (-not $event.data.title) {
                            $event.data | Add-Member -NotePropertyName "title" -NotePropertyValue "Untitled" -Force
                        }
                        if (-not $event.data.app -and -not $event.data.application) {
                            $event.data | Add-Member -NotePropertyName "app" -NotePropertyValue "Unknown" -Force
                        }
                        
                        $allEvents += $event
                    }
                    Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                Write-Host "  - Error reading bucket $bucket : $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
        
        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) events to server..." -ForegroundColor Cyan
            
            $payload = @{
                name = $DEVELOPER_NAME
                token = $API_TOKEN  
                data = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
                if ($_.Exception.Response) {
                    $streamReader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
                    $errorBody = $streamReader.ReadToEnd()
                    Write-Host "Server response: $errorBody" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor DarkRed
    }
}

Write-Host "========================================"
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Test initial connection before starting loop
Write-Host "Testing initial sync..." -ForegroundColor Yellow
Send-ActivityData

if ($?) {
    Write-Host ""
    Write-Host "Starting continuous sync..." -ForegroundColor Green
    Write-Host ""
    
    while ($true) {
        $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
        Write-Host ""
        Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
        Write-Host "----------------------------------------" -ForegroundColor DarkGray
        Start-Sleep -Seconds 300
        
        Send-ActivityData
    }
} else {
    Write-Host ""
    Write-Host "Initial sync failed. Please fix the issues above and try again." -ForegroundColor Red
}