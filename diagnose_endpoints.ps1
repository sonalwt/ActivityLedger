# ActivityWatch Sync Diagnostic - Find Working Endpoint
Write-Host "=== ACTIVITYWATCH SYNC ENDPOINT DIAGNOSTICS ===" -ForegroundColor Cyan
Write-Host "Finding the correct endpoint that doesn't redirect..." -ForegroundColor Yellow
Write-Host ""

$testPayload = @{
    name = "test"
    token = "AWToken_test"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

# List of endpoints to test
$endpoints = @(
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/",
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/",
    "http://api-timesheet.firsteconomy.com/api/v1/sync",
    "http://api-timesheet.firsteconomy.com/api/v1/sync/",
    "https://api-timesheet.firsteconomy.com/api/v1/sync",
    "https://api-timesheet.firsteconomy.com/api/v1/sync/"
)

$workingEndpoint = $null

foreach ($endpoint in $endpoints) {
    Write-Host "`nTesting: $endpoint" -ForegroundColor Cyan
    Write-Host "----------------------------------------"
    
    try {
        # Create HTTP request manually to see redirects
        $request = [System.Net.HttpWebRequest]::Create($endpoint)
        $request.Method = "POST"
        $request.ContentType = "application/json"
        $request.AllowAutoRedirect = $false
        $request.Timeout = 10000
        
        # Add body
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($testPayload)
        $request.ContentLength = $bytes.Length
        $stream = $request.GetRequestStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Close()
        
        # Get response
        try {
            $response = $request.GetResponse()
            $statusCode = [int]$response.StatusCode
            Write-Host "  Status Code: $statusCode" -ForegroundColor Green
            
            # Read response body
            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            $responseText = $reader.ReadToEnd()
            $reader.Close()
            $response.Close()
            
            Write-Host "  Response: $($responseText.Substring(0, [Math]::Min(100, $responseText.Length)))..." -ForegroundColor Gray
            
            if ($statusCode -eq 200) {
                Write-Host "  ✅ SUCCESS! This endpoint works!" -ForegroundColor Green
                $workingEndpoint = $endpoint
                break
            }
        } catch [System.Net.WebException] {
            $errorResponse = $_.Exception.Response
            if ($errorResponse) {
                $statusCode = [int]$errorResponse.StatusCode
                Write-Host "  Status Code: $statusCode" -ForegroundColor Yellow
                
                if ($statusCode -eq 308) {
                    $location = $errorResponse.Headers["Location"]
                    Write-Host "  ❌ 308 Redirect to: $location" -ForegroundColor Red
                } elseif ($statusCode -eq 301 -or $statusCode -eq 302 -or $statusCode -eq 307) {
                    $location = $errorResponse.Headers["Location"]
                    Write-Host "  ⚠️ $statusCode Redirect to: $location" -ForegroundColor Yellow
                } elseif ($statusCode -eq 400 -or $statusCode -eq 401 -or $statusCode -eq 422) {
                    Write-Host "  ✅ Endpoint responds! (Auth error is expected)" -ForegroundColor Green
                    
                    # Try to read error response
                    try {
                        $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
                        $errorText = $reader.ReadToEnd()
                        $reader.Close()
                        Write-Host "  Response: $errorText" -ForegroundColor Gray
                    } catch {}
                    
                    $workingEndpoint = $endpoint
                    break
                } else {
                    Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
                }
                
                $errorResponse.Close()
            }
        }
    } catch {
        Write-Host "  ❌ Connection Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "DIAGNOSIS COMPLETE" -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

if ($workingEndpoint) {
    Write-Host "✅ WORKING ENDPOINT FOUND!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Add this to your sync.ps1:" -ForegroundColor Yellow
    Write-Host '$SERVER_URL = "' -NoNewline
    Write-Host $workingEndpoint -ForegroundColor Cyan -NoNewline
    Write-Host '"'
    Write-Host ""
    
    # Create a fixed sync.ps1
    $syncContent = @"
# ActivityWatch Sync Script - Fixed Endpoint
`$DEVELOPER_NAME = "ankita gholap"
`$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
# Fixed endpoint that works
`$SERVER_URL = "$workingEndpoint"
`$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "`$LOCAL_AW/buckets"
        `$bucketsResponse = Invoke-RestMethod -Uri "`$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        `$buckets = `$bucketsResponse.PSObject.Properties.Name
        Write-Host "Found `$(`$buckets.Count) ActivityWatch buckets"
        
        `$endTime = (Get-Date).ToUniversalTime()
        `$startTime = `$endTime.AddMinutes(-6)
        `$startISO = `$startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        `$endISO = `$endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        `$allEvents = @()
        foreach (`$bucket in `$buckets) {
            try {
                `$eventsUrl = "`$LOCAL_AW/buckets/`$bucket/events?start=`$startISO&end=`$endISO"
                `$events = Invoke-RestMethod -Uri `$eventsUrl -Method GET -TimeoutSec 10
                if (`$events -and `$events.Count -gt 0) {
                    `$allEvents += `$events
                    Write-Host ("  - " + `$bucket + ": " + `$events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                # Skip bucket if error
            }
        }
        
        if (`$allEvents.Count -gt 0) {
            Write-Host "Sending `$(`$allEvents.Count) events to server..." -ForegroundColor Cyan
            
            `$payload = @{
                name = `$DEVELOPER_NAME
                token = `$API_TOKEN  
                data = `$allEvents
                timestamp = `$endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            `$jsonPayload = `$payload | ConvertTo-Json -Depth 10
            
            try {
                `$response = Invoke-RestMethod -Uri `$SERVER_URL -Method POST -Body `$jsonPayload -ContentType "application/json" -TimeoutSec 15
                
                if (`$response.success) {
                    Write-Host "[SUCCESS] Synced `$(`$allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: `$(`$response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: `$(`$_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: `$(`$_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "========================================"
Write-Host "ActivityWatch Sync for `$DEVELOPER_NAME"
Write-Host "Server: `$SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while (`$true) {
    Send-ActivityData
    `$nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at `$nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}
"@
    
    $syncContent | Out-File -FilePath "sync_fixed.ps1" -Encoding UTF8
    Write-Host "Created: sync_fixed.ps1 with the working endpoint" -ForegroundColor Green
    
} else {
    Write-Host "❌ NO WORKING ENDPOINT FOUND!" -ForegroundColor Red
    Write-Host ""
    Write-Host "All endpoints are redirecting or failing." -ForegroundColor Yellow
    Write-Host "This suggests a server configuration issue." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please contact your server administrator and share these results." -ForegroundColor White
    Write-Host "The server needs to be configured to accept POST requests without redirecting." -ForegroundColor White
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")