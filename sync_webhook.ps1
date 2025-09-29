# ActivityWatch Sync Script - Using Stateless Webhook
$DEVELOPER_NAME = "ankita_gholap"  # Use underscore format for ID
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
# Use the stateless webhook endpoint instead
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Test ActivityWatch connection first
        try {
            $testResponse = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
        } catch {
            Write-Host "ActivityWatch is not running. Make sure it's started." -ForegroundColor Yellow
            return
        }

        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        
        # Time range (last 5 minutes)
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-5)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        # Prepare webhook data matching stateless format
        $webhookData = @{}
        
        foreach ($bucketName in $bucketsResponse.PSObject.Properties.Name) {
            if ($bucketName -like "aw-*") {
                try {
                    $eventsUrl = "$LOCAL_AW/buckets/$bucketName/events?start=$startISO&end=$endISO"
                    $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                    
                    if ($events -and $events.Count -gt 0) {
                        $webhookData[$bucketName] = $events
                        Write-Host "  - $bucketName`: $($events.Count) events" -ForegroundColor DarkGray
                    }
                } catch {
                    # Skip buckets that error
                }
            }
        }

        $totalEvents = ($webhookData.Values | ForEach-Object { $_.Count } | Measure-Object -Sum).Sum
        
        if ($totalEvents -gt 0) {
            Write-Host "Sending $totalEvents events to webhook..." -ForegroundColor Cyan
            
            $jsonPayload = $webhookData | ConvertTo-Json -Depth 10 -Compress
            
            # Headers for stateless webhook
            $headers = @{
                "Content-Type" = "application/json"
                "Developer-ID" = $DEVELOPER_NAME
                "Authorization" = "Bearer $API_TOKEN"
            }
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Headers $headers -Body $jsonPayload -TimeoutSec 30
                
                if ($response.status -eq "success") {
                    Write-Host "✓ Webhook sync successful! Processed $($response.message)" -ForegroundColor Green
                } else {
                    Write-Host "Server response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Yellow
                }
            } catch {
                $statusCode = $_.Exception.Response.StatusCode.Value__
                $errorBody = $_.ErrorDetails.Message
                
                if ($statusCode -eq 308) {
                    Write-Host "❌ 308 Redirect. Check server configuration." -ForegroundColor Red
                } elseif ($statusCode -eq 401) {
                    Write-Host "❌ Authentication failed. Check token and developer ID." -ForegroundColor Red
                } else {
                    Write-Host "❌ Error $statusCode`: $errorBody" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "No new activity data to sync" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Clear-Host
Write-Host "=========================================="
Write-Host "ActivityWatch Webhook Sync" -ForegroundColor Cyan
Write-Host "Developer: $DEVELOPER_NAME" -ForegroundColor Gray
Write-Host "Endpoint: $SERVER_URL" -ForegroundColor Gray
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Initial sync
Send-ActivityData

# Continuous sync loop
while ($true) {
    Start-Sleep -Seconds 300  # 5 minutes
    Send-ActivityData
}