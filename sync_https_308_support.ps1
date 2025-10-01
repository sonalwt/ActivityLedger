# ActivityWatch Sync Script - HTTPS with manual redirect handling
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Function to handle HTTP requests with 308 redirect support
function Invoke-WebRequestWith308Support {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [string]$Body = $null,
        [hashtable]$Headers = @{}
    )
    
    $maxRedirects = 5
    $redirectCount = 0
    $currentUri = $Uri
    
    while ($redirectCount -lt $maxRedirects) {
        try {
            $request = [System.Net.WebRequest]::Create($currentUri)
            $request.Method = $Method
            $request.ContentType = "application/json"
            $request.AllowAutoRedirect = $false
            
            # Add headers
            foreach ($key in $Headers.Keys) {
                $request.Headers.Add($key, $Headers[$key])
            }
            
            # Add body if POST
            if ($Method -eq "POST" -and $Body) {
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($Body)
                $request.ContentLength = $bytes.Length
                $stream = $request.GetRequestStream()
                $stream.Write($bytes, 0, $bytes.Length)
                $stream.Close()
            }
            
            $response = $request.GetResponse()
            $statusCode = [int]$response.StatusCode
            
            # Check if it's a redirect
            if ($statusCode -eq 308 -or $statusCode -eq 301 -or $statusCode -eq 302 -or $statusCode -eq 307) {
                $redirectUri = $response.Headers["Location"]
                Write-Host "Redirect detected to: $redirectUri" -ForegroundColor Yellow
                $currentUri = $redirectUri
                $redirectCount++
                $response.Close()
                continue
            }
            
            # Read response
            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            $responseText = $reader.ReadToEnd()
            $reader.Close()
            $response.Close()
            
            return $responseText | ConvertFrom-Json
            
        } catch {
            if ($_.Exception.InnerException -and $_.Exception.InnerException.Response) {
                $errorResponse = $_.Exception.InnerException.Response
                $statusCode = [int]$errorResponse.StatusCode
                
                # Handle expected errors
                if ($statusCode -eq 400 -or $statusCode -eq 401 -or $statusCode -eq 422) {
                    $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
                    $errorText = $reader.ReadToEnd()
                    $reader.Close()
                    return $errorText | ConvertFrom-Json
                }
            }
            throw $_
        }
    }
    
    throw "Too many redirects"
}

function Send-ActivityData {
    try {
        Write-Host "$LOCAL_AW/buckets"
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
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
                    $allEvents += $events
                    Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                # Skip bucket if error
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
                # Use custom function that handles 308 redirects
                $response = Invoke-WebRequestWith308Support -Uri $SERVER_URL -Method "POST" -Body $jsonPayload
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "========================================"
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Using HTTPS with 308 redirect support"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}