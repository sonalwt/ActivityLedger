# test_https_endpoints.ps1 - Find the correct HTTPS endpoint
Write-Host "=== Testing HTTPS Endpoints ===" -ForegroundColor Cyan
Write-Host ""

$testPayload = @{
    name = "test"
    token = "AWToken_test"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

$endpoints = @(
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/",
    "https://api-timesheet.firsteconomy.com/api/v1/sync",
    "https://api-timesheet.firsteconomy.com/api/v1/sync/"
)

foreach ($endpoint in $endpoints) {
    Write-Host "Testing: $endpoint" -ForegroundColor Yellow
    
    try {
        # Test without following redirects
        $response = Invoke-WebRequest -Uri $endpoint -Method POST -Body $testPayload -ContentType "application/json" -MaximumRedirection 0 -ErrorAction SilentlyContinue
        
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ SUCCESS - No redirect needed!" -ForegroundColor Green
            Write-Host "  Use this URL in your sync.ps1: $endpoint" -ForegroundColor Green
        } elseif ($response.StatusCode -eq 400 -or $response.StatusCode -eq 422) {
            Write-Host "  ✓ Endpoint works (auth/validation error is expected)" -ForegroundColor Green
            Write-Host "  Use this URL in your sync.ps1: $endpoint" -ForegroundColor Green
        } else {
            Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            if ($statusCode -eq 308) {
                $location = $_.Exception.Response.Headers.Location
                Write-Host "  ✗ 308 Redirect to: $location" -ForegroundColor Red
            } elseif ($statusCode -eq 400 -or $statusCode -eq 422) {
                Write-Host "  ✓ Endpoint works (auth/validation error is expected)" -ForegroundColor Green
                Write-Host "  Use this URL in your sync.ps1: $endpoint" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Error: Status $statusCode" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✗ Connection error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

Write-Host "=== Testing with Following Redirects ===" -ForegroundColor Cyan
Write-Host ""

# Test the main endpoint with redirect following
try {
    Write-Host "Testing with redirect following enabled..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "https://api-timesheet.firsteconomy.com/api/sync" -Method POST -Body $testPayload -ContentType "application/json" -MaximumRedirection 5
    Write-Host "✓ Connection successful with redirect following!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Error even with redirects: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Recommendation ===" -ForegroundColor Cyan
Write-Host "Based on the tests above, update your sync.ps1 with the URL that shows '✓'" -ForegroundColor White
Write-Host "Or use the redirect-handling version of sync.ps1" -ForegroundColor White