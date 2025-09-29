@echo off
REM trace_redirect.bat - Trace the full redirect chain

cls
echo ========================================
echo Tracing 308 Redirect Chain
echo ========================================
echo.

REM Use curl if available
where curl >nul 2>&1
if %errorlevel%==0 (
    echo Using curl to trace redirects...
    echo.
    echo HTTP Test:
    curl -I -L -X POST http://api-timesheet.firsteconomy.com/api/sync -H "Content-Type: application/json" -d "{\"test\":true}" 2>&1 | findstr /i "HTTP Location"
    echo.
) else (
    echo curl not found, using PowerShell...
)

REM PowerShell detailed trace
powershell.exe -ExecutionPolicy Bypass -Command "
Write-Host ''
Write-Host 'Detailed redirect trace:' -ForegroundColor Yellow
Write-Host ''

$urls = @(
    'http://api-timesheet.firsteconomy.com/api/sync',
    'http://www.api-timesheet.firsteconomy.com/api/sync',
    'http://api-timesheet.firsteconomy.com:8090/api/sync',
    'http://api-timesheet.firsteconomy.com/api/sync/'
)

$headers = @{
    'Content-Type' = 'application/json'
}

$body = @{
    name = 'ankita gholap'
    token = 'AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs'
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
} | ConvertTo-Json

foreach ($url in $urls) {
    Write-Host \"Testing: $url\" -ForegroundColor Cyan
    
    $redirectCount = 0
    $currentUrl = $url
    $maxRedirects = 5
    
    while ($redirectCount -lt $maxRedirects) {
        try {
            $response = Invoke-WebRequest -Uri $currentUrl `
                -Method POST `
                -Headers $headers `
                -Body $body `
                -MaximumRedirection 0 `
                -ErrorAction Stop
            
            Write-Host \"  → Success! Status: $($response.StatusCode)\" -ForegroundColor Green
            break
            
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            
            if ($statusCode -in @(301, 302, 307, 308)) {
                $newLocation = $_.Exception.Response.Headers.Location
                Write-Host \"  → $statusCode redirect to: $newLocation\" -ForegroundColor Yellow
                
                if ($statusCode -eq 308) {
                    Write-Host \"    ⚠️  This is the 308 PERMANENT REDIRECT!\" -ForegroundColor Red
                }
                
                if ($newLocation) {
                    # Handle relative redirects
                    if (-not $newLocation.IsAbsoluteUri) {
                        $baseUri = [System.Uri]::new($currentUrl)
                        $newLocation = [System.Uri]::new($baseUri, $newLocation)
                    }
                    
                    $currentUrl = $newLocation.ToString()
                    $redirectCount++
                } else {
                    Write-Host \"  → No redirect location provided!\" -ForegroundColor Red
                    break
                }
            } else {
                Write-Host \"  → Error: $statusCode - $($_.Exception.Message)\" -ForegroundColor Red
                break
            }
        }
    }
    
    if ($redirectCount -eq $maxRedirects) {
        Write-Host \"  → Too many redirects!\" -ForegroundColor Red
    }
    
    Write-Host ''
}

Write-Host '=== ANALYSIS ===' -ForegroundColor Green
Write-Host 'Look for the URL that gives 200 OK status above'
Write-Host 'That is the URL you should use in sync.ps1'
Write-Host ''
"

pause
