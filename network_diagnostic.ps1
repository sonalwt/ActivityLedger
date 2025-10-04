# Network Diagnostic Script for Timesheet API
Write-Host "=== Network Diagnostics for api-timesheet.firsteconomy.com ===" -ForegroundColor Yellow
Write-Host ""

# Test DNS resolution
Write-Host "1. Testing DNS resolution..." -ForegroundColor Cyan
try {
    $dns = [System.Net.Dns]::GetHostAddresses("api-timesheet.firsteconomy.com")
    Write-Host "   SUCCESS: DNS resolved to:" -ForegroundColor Green
    foreach ($ip in $dns) {
        Write-Host "   - $($ip.IPAddressToString)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   FAILED: Cannot resolve hostname" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test with nslookup
Write-Host "2. Running nslookup..." -ForegroundColor Cyan
$nslookup = nslookup api-timesheet.firsteconomy.com 2>&1
Write-Host $nslookup -ForegroundColor Gray

Write-Host ""

# Test ping
Write-Host "3. Testing ping..." -ForegroundColor Cyan
$ping = ping api-timesheet.firsteconomy.com -n 2 2>&1
Write-Host $ping -ForegroundColor Gray

Write-Host ""

# Test alternative DNS servers
Write-Host "4. Testing with Google DNS (8.8.8.8)..." -ForegroundColor Cyan
$googleDns = nslookup api-timesheet.firsteconomy.com 8.8.8.8 2>&1
Write-Host $googleDns -ForegroundColor Gray

Write-Host ""

# Test localhost ActivityWatch
Write-Host "5. Testing local ActivityWatch connection..." -ForegroundColor Cyan
try {
    $localTest = Invoke-RestMethod -Uri "http://localhost:5600/api/0/info" -Method GET -TimeoutSec 5
    Write-Host "   SUCCESS: ActivityWatch is running locally" -ForegroundColor Green
} catch {
    Write-Host "   FAILED: Cannot connect to local ActivityWatch" -ForegroundColor Red
    Write-Host "   Make sure ActivityWatch is running on localhost:5600" -ForegroundColor Yellow
}

Write-Host ""

# Check hosts file
Write-Host "6. Checking hosts file for manual entries..." -ForegroundColor Cyan
$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$hostsContent = Get-Content $hostsPath | Where-Object { $_ -like "*firsteconomy*" }
if ($hostsContent) {
    Write-Host "   Found entries in hosts file:" -ForegroundColor Yellow
    $hostsContent | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   No entries found in hosts file" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Diagnostics Complete ===" -ForegroundColor Yellow