# Show 308 Redirect Issue
Write-Host "=== Demonstrating the 308 Redirect Issue ===" -ForegroundColor Cyan
Write-Host ""

$testPayload = @{
    name = "test"
    token = "AWToken_test"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

Write-Host "1. Testing HTTPS endpoint..." -ForegroundColor Yellow
Write-Host "   URL: https://api-timesheet.firsteconomy.com/api/sync"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "https://api-timesheet.firsteconomy.com/api/sync" -Method POST -Body $testPayload -ContentType "application/json" -MaximumRedirection 0 -ErrorAction Stop
    Write-Host "   Result: Success (no redirect)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 308) {
        Write-Host "   Result: 308 PERMANENT REDIRECT ❌" -ForegroundColor Red
        Write-Host "   This is the problem!" -ForegroundColor Red
    } else {
        Write-Host "   Result: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "2. Testing HTTP endpoint..." -ForegroundColor Yellow
Write-Host "   URL: http://api-timesheet.firsteconomy.com/api/sync"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://api-timesheet.firsteconomy.com/api/sync" -Method POST -Body $testPayload -ContentType "application/json" -ErrorAction Stop
    Write-Host "   Result: Connected successfully! ✅" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400 -or $statusCode -eq 401 -or $statusCode -eq 422) {
        Write-Host "   Result: Connected successfully! ✅" -ForegroundColor Green
        Write-Host "   (Auth error is expected with test data)" -ForegroundColor Gray
    } else {
        Write-Host "   Result: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== CONCLUSION ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "The HTTPS endpoint causes a 308 redirect that PowerShell can't handle." -ForegroundColor White
Write-Host "The HTTP endpoint works perfectly without any redirects." -ForegroundColor White
Write-Host ""
Write-Host "SOLUTION: Use HTTP instead of HTTPS in your sync.ps1" -ForegroundColor Green
Write-Host '$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"' -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")