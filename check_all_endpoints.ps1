# check_all_endpoints.ps1 - Check all possible endpoint variations

Clear-Host
Write-Host "=== Checking All Possible Endpoints ===" -ForegroundColor Cyan
Write-Host ""

$baseUrls = @(
    "http://api-timesheet.firsteconomy.com",
    "https://api-timesheet.firsteconomy.com"
)

$paths = @(
    "/api/sync",
    "/api/sync/",
    "/sync",
    "/sync/",
    "/api/v1/sync",
    "/api/v1/sync/",
    "/api/v1/activitywatch/webhook",
    "/api/v1/activitywatch/webhook/"
)

$testPayload = @{
    name = "ankita gholap"
    token = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

$workingEndpoints = @()

foreach ($baseUrl in $baseUrls) {
    Write-Host "`nBase URL: $baseUrl" -ForegroundColor Yellow
    Write-Host "─" * 50
    
    foreach ($path in $paths) {
        $fullUrl = $baseUrl + $path
        Write-Host -NoNewline "Testing: $path "
        Write-Host -NoNewline ("." * (30 - $path.Length)) " "
        
        try {
            $response = Invoke-WebRequest -Uri $fullUrl `
                -Method POST `
                -Body $testPayload `
                -ContentType "application/json" `
                -MaximumRedirection 0 `
                -TimeoutSec 5 `
                -ErrorAction Stop
            
            Write-Host "[OK - $($response.StatusCode)]" -ForegroundColor Green
            $workingEndpoints += $fullUrl
            
        } catch {
            if ($_.Exception.Response.StatusCode.Value__ -eq 308) {
                $location = $_.Exception.Response.Headers.Location
                Write-Host "[308 → $location]" -ForegroundColor Red
            } elseif ($_.Exception.Response.StatusCode.Value__ -in @(301, 302, 307)) {
                Write-Host "[$($_.Exception.Response.StatusCode.Value__) Redirect]" -ForegroundColor Yellow
            } elseif ($_.Exception.Response.StatusCode.Value__ -eq 404) {
                Write-Host "[404 Not Found]" -ForegroundColor DarkGray
            } else {
                Write-Host "[Error: $($_.Exception.Response.StatusCode.Value__)]" -ForegroundColor DarkRed
            }
        }
    }
}

Write-Host "`n`n=== RESULTS ===" -ForegroundColor Green

if ($workingEndpoints.Count -gt 0) {
    Write-Host "`nWorking endpoints found:" -ForegroundColor Green
    foreach ($endpoint in $workingEndpoints) {
        Write-Host "  ✓ $endpoint" -ForegroundColor Green
    }
    Write-Host "`nUse one of these in your sync.ps1!" -ForegroundColor Yellow
} else {
    Write-Host "`nNo working endpoints found!" -ForegroundColor Red
    Write-Host "The server might be:" -ForegroundColor Yellow
    Write-Host "  - Down or unreachable"
    Write-Host "  - Using a different endpoint path"
    Write-Host "  - Requiring authentication headers"
    Write-Host "  - Behind a proxy that's causing redirects"
}

Write-Host "`n"
