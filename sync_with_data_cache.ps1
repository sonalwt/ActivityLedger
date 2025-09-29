# sync_with_data_cache.ps1 - Sync with data caching to avoid duplicate syncs

$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Cache configuration
$CACHE_DIR = "$env:TEMP\ActivityWatchCache"
$CACHE_FILE = "$CACHE_DIR\synced_events.json"
$LOG_FILE = "$CACHE_DIR\sync_log.txt"

# Create cache directory if it doesn't exist
if (!(Test-Path $CACHE_DIR)) {
    New-Item -ItemType Directory -Path $CACHE_DIR | Out-Null
}

# Function to get cached event IDs
function Get-CachedEventIds {
    if (Test-Path $CACHE_FILE) {
        try {
            $cached = Get-Content $CACHE_FILE -Raw | ConvertFrom-Json
            return $cached.syncedEventIds
        } catch {
            return @()
        }
    }
    return @()
}

# Function to save event IDs to cache
function Save-EventIdsToCache($eventIds) {
    $cache = @{
        lastSync = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        syncedEventIds = $eventIds
    }
    $cache | ConvertTo-Json -Depth 10 | Out-File $CACHE_FILE
}

# Function to log with timestamp
function Write-Log($message, $color = "White") {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $message"
    
    # Write to console
    Write-Host $logMessage -ForegroundColor $color
    
    # Write to log file
    Add-Content -Path $LOG_FILE -Value $logMessage
}

function Send-ActivityData {
    try {
        Write-Log "Checking ActivityWatch..." "Gray"
        
        # Get cached event IDs
        $cachedEventIds = Get-CachedEventIds()
        Write-Log "Found $($cachedEventIds.Count) cached events" "Gray"

        # Test ActivityWatch connection
        try {
            $testResponse = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
        } catch {
            Write-Log "ActivityWatch is not running" "Yellow"
            return
        }

        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name | Where-Object { $_ -like "aw-*" }

        # Time range - get last 24 hours to check for any missed events
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddHours(-24)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        # Collect new events only
        $newEvents = @()
        $allEventIds = @()
        
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                
                foreach ($event in $events) {
                    # Create unique event ID
                    $eventId = "$bucket-$($event.timestamp)-$($event.duration)"
                    $allEventIds += $eventId
                    
                    # Only add if not already synced
                    if ($cachedEventIds -notcontains $eventId) {
                        $newEvents += $event
                    }
                }
            } catch {
                # Skip buckets that error out
            }
        }

        Write-Log "Found $($newEvents.Count) new events to sync" "Cyan"

        if ($newEvents.Count -gt 0) {
            # Prepare payload
            $payload = @{
                name      = $DEVELOPER_NAME
                token     = $API_TOKEN
                data      = $newEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            
            # Send to server
            $headers = @{
                "Content-Type" = "application/json"
                "Accept" = "application/json"
            }
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Headers $headers -Body $jsonPayload -TimeoutSec 30
                
                if ($response.success) {
                    Write-Log "✓ Sync successful! Sent $($newEvents.Count) new events" "Green"
                    
                    # Update cache with all event IDs
                    Save-EventIdsToCache $allEventIds
                    Write-Log "Cache updated" "Gray"
                } else {
                    Write-Log "Server error: $($response.error)" "Red"
                }
            } catch {
                Write-Log "Error: $($_.Exception.Message)" "Red"
            }
        } else {
            Write-Log "No new events to sync" "Gray"
            # Still update cache to include any events from the time window
            Save-EventIdsToCache $allEventIds
        }
        
    } catch {
        Write-Log "Unexpected error: $($_.Exception.Message)" "Red"
    }
}

# Function to clear cache
function Clear-Cache {
    if (Test-Path $CACHE_FILE) {
        Remove-Item $CACHE_FILE -Force
        Write-Log "Cache cleared" "Yellow"
    }
}

# Main execution
Clear-Host
Write-Log "==========================================" "Cyan"
Write-Log "ActivityWatch Sync with Caching" "Cyan"
Write-Log "Cache location: $CACHE_DIR" "Gray"
Write-Log "Press Ctrl+C to stop" "Yellow"
Write-Log "Press 'C' to clear cache" "Yellow"
Write-Log "==========================================" "Cyan"

# Check for command line arguments
if ($args -contains "-clearcache") {
    Clear-Cache
}

# Initial sync
Send-ActivityData

# Continuous sync loop
while ($true) {
    # Check for key press (non-blocking)
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        if ($key.Key -eq 'C') {
            Clear-Cache
        }
    }
    
    # Wait 5 minutes
    Start-Sleep -Seconds 300
    Send-ActivityData
}
