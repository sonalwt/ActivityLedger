# debug_sync_advanced.ps1 - Advanced debugging for 308 redirect issue

Clear-Host
Write-Host "=== Advanced Sync Debugging ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$HTTPS_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$HTTP_URL = "http://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Test payload
$testPayload = @{
    name = $DEVELOPER_NAME
    token = $API_TOKEN
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

Write-Host "1. Testing ActivityWatch Connection..." -ForegroundColor Yellow
try {
    $awTest = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
    Write-Host "   ✓ ActivityWatch is running" -ForegroundColor Green
    Write-Host "   Version: $($awTest.version)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ ActivityWatch is not running!" -ForegroundColor Red
    Write-Host "   Make sure ActivityWatch is started" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. Testing HTTPS Endpoint (Current)..." -ForegroundColor Yellow
try {
    # Test with no redirect following
    $httpsResponse = Invoke-WebRequest -Uri $HTTPS_URL `
        -Method POST `
        -Body $testPayload `
        -ContentType "application/json" `
        -MaximumRedirection 0 `
        -ErrorAction Stop
    
    Write-Host "   ✓ HTTPS works! Status: $($httpsResponse.StatusCode)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 308) {
        Write-Host "   ✗ 308 PERMANENT REDIRECT detected!" -ForegroundColor Red
        $location = $_.Exception.Response.Headers.Location
        Write-Host "   Redirects to: $location" -ForegroundColor Yellow
        
        # Test the redirect location
        if ($location) {
            Write-Host "   Testing redirect location..." -ForegroundColor Gray
            try {
                $redirectTest = Invoke-RestMethod -Uri $location.ToString() `
                    -Method POST `
                    -Body $testPayload `
                    -ContentType "application/json" `
                    -TimeoutSec 5
                Write-Host "   ✓ Redirect location works!" -ForegroundColor Green
            } catch {
                Write-Host "   ✗ Redirect location failed: $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "   ✗ HTTPS Error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "3. Testing HTTP Endpoint (Recommended)..." -ForegroundColor Yellow
try {
    $httpResponse = Invoke-RestMethod -Uri $HTTP_URL `
        -Method POST `
        -Body $testPayload `
        -ContentType "application/json" `
        -TimeoutSec 5
    
    Write-Host "   ✓ HTTP works!" -ForegroundColor Green
    if ($httpResponse.success) {
        Write-Host "   Server response: Success" -ForegroundColor Green
    } elseif ($httpResponse.error) {
        Write-Host "   Server response: $($httpResponse.error)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ HTTP Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "4. Checking Current sync.ps1..." -ForegroundColor Yellow
if (Test-Path "sync.ps1") {
    $syncContent = Get-Content "sync.ps1" -Raw
    if ($syncContent -match '\$SERVER_URL\s*=\s*"([^"]+)"') {
        $currentUrl = $matches[1]
        Write-Host "   Current URL: $currentUrl" -ForegroundColor $(if ($currentUrl -like "https://*") { "Red" } else { "Green" })
        
        if ($currentUrl -like "https://*") {
            Write-Host "   ⚠️  Using HTTPS - This causes 308 redirect!" -ForegroundColor Red
            Write-Host "   ✓ Solution: Change to HTTP" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "5. Testing Real Sync..." -ForegroundColor Yellow
try {
    # Get some real data from ActivityWatch
    $buckets = (Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10).PSObject.Properties.Name | Where-Object { $_ -like "aw-*" }
    
    $endTime = (Get-Date).ToUniversalTime()
    $startTime = $endTime.AddMinutes(-5)
    $events = @()
    
    foreach ($bucket in $buckets | Select-Object -First 1) {
        $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$($startTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ'))&end=$($endTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ'))"
        $bucketEvents = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
        $events += $bucketEvents | Select-Object -First 1
    }
    
    if ($events.Count -gt 0) {
        Write-Host "   Found $($events.Count) test event(s)" -ForegroundColor Gray
        
        $realPayload = @{
            name = $DEVELOPER_NAME
            token = $API_TOKEN
            data = $events
            timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        } | ConvertTo-Json -Depth 10
        
        # Test with HTTP
        Write-Host "   Testing sync with HTTP..." -ForegroundColor Gray
        try {
            $syncResponse = Invoke-RestMethod -Uri $HTTP_URL `
                -Method POST `
                -Body $realPayload `
                -ContentType "application/json" `
                -TimeoutSec 15
            
            Write-Host "   ✓ Sync successful with HTTP!" -ForegroundColor Green
        } catch {
            Write-Host "   ✗ Sync failed: $_" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "   ✗ Could not test real sync: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Recommendations ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "PROBLEM: Your sync.ps1 is using HTTPS which causes 308 redirect" -ForegroundColor Red
Write-Host ""
Write-Host "SOLUTION: Change your sync.ps1 file:" -ForegroundColor Green
Write-Host '  FROM: $SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"' -ForegroundColor Red
Write-Host '  TO:   $SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"' -ForegroundColor Green
Write-Host ""
Write-Host "Or run: .\fix_308_redirect.bat to fix automatically" -ForegroundColor Yellow
Write-Host ""
