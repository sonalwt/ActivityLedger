@echo off
REM comprehensive_fix.bat - Comprehensive fix for persistent 308 redirect

cls
echo ========================================
echo Comprehensive 308 Redirect Diagnostic
echo ========================================
echo.

REM 1. Check DNS resolution
echo 1. Checking DNS resolution...
nslookup api-timesheet.firsteconomy.com
echo.

REM 2. Check if going through proxy
echo 2. Checking proxy settings...
echo HTTP_PROXY: %HTTP_PROXY%
echo HTTPS_PROXY: %HTTPS_PROXY%
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2>nul | find "0x1" >nul
if %errorlevel%==0 (
    echo System proxy is ENABLED
    reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2>nul
) else (
    echo No system proxy detected
)
echo.

REM 3. Try different approaches
echo 3. Testing different connection methods...
echo.

powershell -ExecutionPolicy Bypass -Command "
Write-Host 'Testing with different methods:' -ForegroundColor Yellow
Write-Host ''

$payload = @{
    name = 'ankita gholap'
    token = 'AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs'
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
} | ConvertTo-Json

# Method 1: Direct IP (bypass DNS)
Write-Host 'Method 1: Using direct IP address...' -ForegroundColor Cyan
try {
    $ip = [System.Net.Dns]::GetHostAddresses('api-timesheet.firsteconomy.com')[0].IPAddressToString
    Write-Host \"  Resolved to IP: $ip\"
    
    $ipUrl = \"http://$ip/api/sync\"
    $response = Invoke-WebRequest -Uri $ipUrl `
        -Method POST `
        -Body $payload `
        -ContentType 'application/json' `
        -Headers @{'Host' = 'api-timesheet.firsteconomy.com'} `
        -MaximumRedirection 0 `
        -ErrorAction Stop
    
    Write-Host '  ✓ Success with direct IP!' -ForegroundColor Green
} catch {
    Write-Host \"  ✗ Failed: $($_.Exception.Message)\" -ForegroundColor Red
}

Write-Host ''

# Method 2: No proxy
Write-Host 'Method 2: Bypassing proxy...' -ForegroundColor Cyan
try {
    $webClient = New-Object System.Net.WebClient
    $webClient.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
    $webClient.Headers.Add('Content-Type', 'application/json')
    
    $result = $webClient.UploadString('http://api-timesheet.firsteconomy.com/api/sync', 'POST', $payload)
    Write-Host '  ✓ Success without proxy!' -ForegroundColor Green
    Write-Host \"  Response: $result\" -ForegroundColor Gray
} catch {
    Write-Host \"  ✗ Failed: $_\" -ForegroundColor Red
}

Write-Host ''

# Method 3: Test port 8090 directly
Write-Host 'Method 3: Testing port 8090 directly...' -ForegroundColor Cyan
$testUrls = @(
    'http://api-timesheet.firsteconomy.com:8090/api/sync',
    'http://api-timesheet.firsteconomy.com:8090/sync',
    'http://api-timesheet.firsteconomy.com:80/api/sync'
)

foreach ($url in $testUrls) {
    Write-Host \"  Testing: $url\"
    try {
        $response = Invoke-WebRequest -Uri $url `
            -Method POST `
            -Body $payload `
            -ContentType 'application/json' `
            -MaximumRedirection 0 `
            -TimeoutSec 3 `
            -ErrorAction Stop
        
        Write-Host \"    ✓ Success! Use this URL!\" -ForegroundColor Green
        break
    } catch {
        if ($_.Exception.Response.StatusCode.Value__ -eq 308) {
            Write-Host \"    → 308 to: $($_.Exception.Response.Headers.Location)\" -ForegroundColor Red
        } else {
            Write-Host \"    → Failed: $($_.Exception.Response.StatusCode.Value__)\" -ForegroundColor DarkGray
        }
    }
}

Write-Host ''
Write-Host '=== CREATING FIXED sync.ps1 ===' -ForegroundColor Green

# Find working endpoint
$workingUrl = $null
$testUrls = @(
    'http://api-timesheet.firsteconomy.com:8090/api/sync',
    'http://api-timesheet.firsteconomy.com/api/sync/',
    'http://api-timesheet.firsteconomy.com/sync'
)

foreach ($url in $testUrls) {
    try {
        $r = Invoke-WebRequest -Uri $url -Method POST -Body $payload -ContentType 'application/json' -MaximumRedirection 5 -TimeoutSec 5 -ErrorAction Stop
        $workingUrl = $url
        break
    } catch {
        # Continue trying
    }
}

if ($workingUrl) {
    Write-Host \"Found working URL: $workingUrl\" -ForegroundColor Green
    
    # Create new sync script
    $syncScript = @\"
# ActivityWatch Sync Script - FIXED
\$DEVELOPER_NAME = 'ankita gholap'
\$API_TOKEN = 'AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs'
\$SERVER_URL = '$workingUrl'
\$LOCAL_AW = 'http://localhost:5600/api/0'

# Disable proxy for this script
[System.Net.WebRequest]::DefaultWebProxy = New-Object System.Net.WebProxy

function Send-ActivityData {
    try {
        Write-Host \"Checking ActivityWatch at \$(Get-Date -Format 'HH:mm:ss')\"
        
        \$bucketsResponse = Invoke-RestMethod -Uri \"\$LOCAL_AW/buckets\" -Method GET -TimeoutSec 10
        \$buckets = \$bucketsResponse.PSObject.Properties.Name
        Write-Host \"Found \$(\$buckets.Count) ActivityWatch buckets\"
        
        \$endTime = (Get-Date).ToUniversalTime()
        \$startTime = \$endTime.AddMinutes(-6)
        \$startISO = \$startTime.ToString(\"yyyy-MM-ddTHH:mm:ss.fffZ\")
        \$endISO = \$endTime.ToString(\"yyyy-MM-ddTHH:mm:ss.fffZ\")
        
        \$allEvents = @()
        foreach (\$bucket in \$buckets) {
            try {
                \$eventsUrl = \"\$LOCAL_AW/buckets/\$bucket/events?start=\$startISO&end=\$endISO\"
                \$events = Invoke-RestMethod -Uri \$eventsUrl -Method GET -TimeoutSec 10
                \$allEvents += \$events
            } catch {
                # Skip
            }
        }
        
        if (\$allEvents.Count -gt 0) {
            \$payload = @{
                name = \$DEVELOPER_NAME
                token = \$API_TOKEN  
                data = \$allEvents
                timestamp = \$endTime.ToString(\"yyyy-MM-ddTHH:mm:ss.fffZ\")
            } | ConvertTo-Json -Depth 10
            
            \$response = Invoke-RestMethod -Uri \$SERVER_URL -Method POST -Body \$payload -ContentType \"application/json\" -TimeoutSec 15
            
            if (\$response.success) {
                Write-Host \"✓ Synced \$(\$allEvents.Count) events successfully\" -ForegroundColor Green
            } else {
                Write-Host \"Server error: \$(\$response.error)\" -ForegroundColor Red
            }
        } else {
            Write-Host \"No new data to sync\"
        }
        
    } catch {
        Write-Host \"Sync error: \$(\$_.Exception.Message)\" -ForegroundColor Red
    }
}

Write-Host \"ActivityWatch Sync for \$DEVELOPER_NAME\" -ForegroundColor Cyan
Write-Host \"Server: \$SERVER_URL\" -ForegroundColor Gray
Write-Host \"Press Ctrl+C to stop\"
Write-Host \"\"

while (\$true) {
    Send-ActivityData
    \$nextSync = (Get-Date).AddMinutes(5).ToString(\"HH:mm:ss\")
    Write-Host \"Waiting 5 minutes... (next sync at \$nextSync)\"
    Start-Sleep -Seconds 300
}
\"@
    
    \$syncScript | Out-File -FilePath 'sync_fixed_final.ps1' -Encoding UTF8
    Write-Host ''
    Write-Host '✓ Created sync_fixed_final.ps1 with working URL!' -ForegroundColor Green
    Write-Host 'Run: .\\sync_fixed_final.ps1' -ForegroundColor Yellow
} else {
    Write-Host 'Could not find a working URL automatically.' -ForegroundColor Red
    Write-Host 'Please contact your system administrator.' -ForegroundColor Yellow
}
"

echo.
pause
