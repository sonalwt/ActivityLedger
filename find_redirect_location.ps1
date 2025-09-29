# find_redirect_location.ps1 - Find exactly where the 308 redirect is pointing

Clear-Host
Write-Host "=== Finding 308 Redirect Location ===" -ForegroundColor Cyan
Write-Host ""

$urls = @(
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/",  # with trailing slash
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/"
)

$testPayload = @{
    name = "ankita gholap"
    token = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

foreach ($url in $urls) {
    Write-Host "Testing: $url" -ForegroundColor Yellow
    
    try {
        # Use .NET WebRequest to get exact redirect location
        $request = [System.Net.HttpWebRequest]::Create($url)
        $request.Method = "POST"
        $request.ContentType = "application/json"
        $request.AllowAutoRedirect = $false
        
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($testPayload)
        $request.ContentLength = $bytes.Length
        
        $stream = $request.GetRequestStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Close()
        
        $response = $request.GetResponse()
        Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
        $response.Close()
        
    } catch [System.Net.WebException] {
        $response = $_.Exception.Response
        $statusCode = [int]$response.StatusCode
        
        if ($statusCode -eq 308) {
            Write-Host "  Status: 308 REDIRECT" -ForegroundColor Red
            $location = $response.Headers["Location"]
            Write-Host "  REDIRECTS TO: $location" -ForegroundColor Cyan
            Write-Host "  ^^^ USE THIS URL IN YOUR sync.ps1 ^^^" -ForegroundColor Green
            Write-Host ""
        } else {
            Write-Host "  Status: $statusCode" -ForegroundColor Yellow
        }
        
        if ($response) { $response.Close() }
    }
    
    Write-Host ""
}

Write-Host "=== SOLUTION ===" -ForegroundColor Green
Write-Host "Update your sync.ps1 to use the exact URL shown in 'REDIRECTS TO' above" -ForegroundColor Yellow
Write-Host ""
