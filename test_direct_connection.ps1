# Direct connection test - no redirect handling
Write-Host "=== DIRECT CONNECTION TEST ===" -ForegroundColor Cyan
Write-Host "Testing raw connection to see exact server response..." -ForegroundColor Yellow
Write-Host ""

$testPayload = '{"name":"test","token":"test","data":[],"timestamp":"2024-01-01T00:00:00Z"}'

# Test with .NET HttpClient (different from WebRequest)
Add-Type -AssemblyName System.Net.Http

$endpoints = @(
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/",
    "http://timesheet.firsteconomy.com/api/sync",
    "http://timesheet-api.firsteconomy.com/api/sync"
)

foreach ($url in $endpoints) {
    Write-Host "`nTesting: $url" -ForegroundColor Cyan
    
    try {
        $client = New-Object System.Net.Http.HttpClient
        $client.DefaultRequestHeaders.Add("User-Agent", "PowerShell-Sync")
        
        # Disable auto redirect
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.AllowAutoRedirect = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        
        $content = New-Object System.Net.Http.StringContent($testPayload, [System.Text.Encoding]::UTF8, "application/json")
        
        $response = $client.PostAsync($url, $content).Result
        
        Write-Host "  Status: $($response.StatusCode) ($([int]$response.StatusCode))" -ForegroundColor Yellow
        Write-Host "  Reason: $($response.ReasonPhrase)" -ForegroundColor Gray
        
        if ($response.Headers.Location) {
            Write-Host "  Location: $($response.Headers.Location)" -ForegroundColor Cyan
        }
        
        $responseContent = $response.Content.ReadAsStringAsync().Result
        if ($responseContent) {
            Write-Host "  Body: $($responseContent.Substring(0, [Math]::Min(200, $responseContent.Length)))..." -ForegroundColor Gray
        }
        
        # Check if it's a success or acceptable error
        $statusCode = [int]$response.StatusCode
        if ($statusCode -eq 200 -or $statusCode -eq 400 -or $statusCode -eq 401 -or $statusCode -eq 422) {
            Write-Host "  ✅ This could work!" -ForegroundColor Green
        }
        
        $response.Dispose()
        $client.Dispose()
        
    } catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== CHECKING ALTERNATIVE PORTS ===" -ForegroundColor Cyan
Write-Host ""

# Try different ports
$altPorts = @("8000", "8080", "80", "443")
$baseHost = "api-timesheet.firsteconomy.com"

foreach ($port in $altPorts) {
    $url = "http://${baseHost}:${port}/api/sync"
    Write-Host "Testing port $port : $url" -ForegroundColor Yellow
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 3000
        $tcpClient.SendTimeout = 3000
        
        $asyncResult = $tcpClient.BeginConnect($baseHost, $port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne(3000, $false)
        
        if ($wait -and $tcpClient.Connected) {
            Write-Host "  ✅ Port $port is open!" -ForegroundColor Green
            $tcpClient.Close()
        } else {
            Write-Host "  ✗ Port $port is closed or filtered" -ForegroundColor Gray
            $tcpClient.Close()
        }
    } catch {
        Write-Host "  ✗ Cannot connect to port $port" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")