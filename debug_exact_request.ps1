# debug_exact_request.ps1 - Debug the exact request causing 308

Clear-Host
Write-Host "=== Debugging Exact Sync Request ===" -ForegroundColor Cyan
Write-Host ""

$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Server URL: $SERVER_URL"
Write-Host "  Developer: $DEVELOPER_NAME"
Write-Host ""

# First, let's get some real ActivityWatch data
Write-Host "1. Getting real ActivityWatch data..." -ForegroundColor Yellow
try {
    $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
    $buckets = $bucketsResponse.PSObject.Properties.Name | Where-Object { $_ -like "aw-*" }
    Write-Host "   Found $($buckets.Count) buckets" -ForegroundColor Gray
    
    # Get some real events
    $endTime = (Get-Date).ToUniversalTime()
    $startTime = $endTime.AddMinutes(-5)
    $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    
    $realEvents = @()
    foreach ($bucket in $buckets | Select-Object -First 1) {
        $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
        $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
        if ($events) {
            $realEvents += $events | Select-Object -First 2
        }
    }
    
    Write-Host "   Got $($realEvents.Count) real events for testing" -ForegroundColor Gray
} catch {
    Write-Host "   Could not get ActivityWatch data: $_" -ForegroundColor Red
    $realEvents = @()
}

Write-Host ""
Write-Host "2. Testing with different payloads..." -ForegroundColor Yellow

# Test different payload sizes and formats
$testPayloads = @(
    @{
        name = "Minimal test payload"
        payload = @{
            name = $DEVELOPER_NAME
            token = $API_TOKEN
            data = @()
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }
    },
    @{
        name = "Payload with fake event"
        payload = @{
            name = $DEVELOPER_NAME
            token = $API_TOKEN
            data = @(@{
                timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
                duration = 60
                data = @{ app = "test"; title = "Test" }
            })
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }
    },
    @{
        name = "Payload with real events"
        payload = @{
            name = $DEVELOPER_NAME
            token = $API_TOKEN
            data = $realEvents
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }
    }
)

foreach ($test in $testPayloads) {
    Write-Host ""
    Write-Host "Testing: $($test.name)" -ForegroundColor Cyan
    
    $jsonPayload = $test.payload | ConvertTo-Json -Depth 10
    Write-Host "  Payload size: $($jsonPayload.Length) characters" -ForegroundColor Gray
    
    # Method 1: Using Invoke-RestMethod (what sync.ps1 uses)
    Write-Host "  Method 1 - Invoke-RestMethod: " -NoNewline
    try {
        $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host "    Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    } catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 308) {
            Write-Host "308 REDIRECT!" -ForegroundColor Red
            Write-Host "    Error details: $($_.Exception.Message)" -ForegroundColor Red
        } else {
            Write-Host "Error: $($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
        }
    }
    
    # Method 2: Using Invoke-WebRequest with explicit settings
    Write-Host "  Method 2 - Invoke-WebRequest: " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $SERVER_URL `
            -Method POST `
            -Body $jsonPayload `
            -ContentType "application/json" `
            -Headers @{
                "Accept" = "application/json"
                "User-Agent" = "ActivityWatch-Sync/1.0"
            } `
            -UseBasicParsing `
            -TimeoutSec 15
        
        Write-Host "SUCCESS! Status: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 308) {
            Write-Host "308 REDIRECT!" -ForegroundColor Red
        } else {
            Write-Host "Error: $($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
        }
    }
    
    # Method 3: Using .NET HttpClient directly
    Write-Host "  Method 3 - .NET HttpClient: " -NoNewline
    try {
        Add-Type -AssemblyName System.Net.Http
        $httpClient = New-Object System.Net.Http.HttpClient
        $httpClient.DefaultRequestHeaders.Add("User-Agent", "ActivityWatch-Sync/1.0")
        
        $content = New-Object System.Net.Http.StringContent($jsonPayload, [System.Text.Encoding]::UTF8, "application/json")
        $httpResponse = $httpClient.PostAsync($SERVER_URL, $content).Result
        
        if ($httpResponse.StatusCode -eq 308) {
            Write-Host "308 REDIRECT!" -ForegroundColor Red
            Write-Host "    Location: $($httpResponse.Headers.Location)" -ForegroundColor Red
        } else {
            Write-Host "SUCCESS! Status: $($httpResponse.StatusCode)" -ForegroundColor Green
        }
        
        $httpClient.Dispose()
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "3. Testing exact URL variations..." -ForegroundColor Yellow

$urlVariations = @(
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/",
    "https://www.api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com:443/api/sync"
)

$testJson = @{
    name = $DEVELOPER_NAME
    token = $API_TOKEN
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

foreach ($url in $urlVariations) {
    Write-Host -NoNewline "  $url ... "
    try {
        $response = Invoke-RestMethod -Uri $url -Method POST -Body $testJson -ContentType "application/json" -TimeoutSec 5
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "$($_.Exception.Response.StatusCode.Value__)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== ANALYSIS ===" -ForegroundColor Green
Write-Host "If certain payloads cause 308 but others don't, the issue might be:"
Write-Host "  - Payload size limits"
Write-Host "  - Special characters in the data"
Write-Host "  - Server-side validation redirecting certain requests"
Write-Host ""
