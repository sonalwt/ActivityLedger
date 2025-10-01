# Find and follow 308 redirects
Write-Host "=== FOLLOWING 308 REDIRECTS ===" -ForegroundColor Cyan
Write-Host "Let's see where the server is redirecting to..." -ForegroundColor Yellow
Write-Host ""

$baseUrl = "http://api-timesheet.firsteconomy.com/api/sync"
$testPayload = @{
    name = "test"
    token = "AWToken_test"
    data = @()
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
} | ConvertTo-Json

Write-Host "Starting URL: $baseUrl" -ForegroundColor White
Write-Host ""

$currentUrl = $baseUrl
$redirectCount = 0
$maxRedirects = 5

while ($redirectCount -lt $maxRedirects) {
    Write-Host "Attempt $($redirectCount + 1):" -ForegroundColor Yellow
    Write-Host "  Testing: $currentUrl" -ForegroundColor Cyan
    
    try {
        $request = [System.Net.HttpWebRequest]::Create($currentUrl)
        $request.Method = "POST"
        $request.ContentType = "application/json"
        $request.AllowAutoRedirect = $false
        $request.Timeout = 10000
        
        # Add body
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($testPayload)
        $request.ContentLength = $bytes.Length
        $stream = $request.GetRequestStream()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Close()
        
        try {
            $response = $request.GetResponse()
            $statusCode = [int]$response.StatusCode
            Write-Host "  Status: $statusCode" -ForegroundColor Green
            
            # Success! No redirect
            $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
            $responseText = $reader.ReadToEnd()
            $reader.Close()
            $response.Close()
            
            Write-Host "  ✅ Success! No redirect needed." -ForegroundColor Green
            Write-Host "  Response: $($responseText.Substring(0, [Math]::Min(100, $responseText.Length)))..." -ForegroundColor Gray
            
            Write-Host ""
            Write-Host "WORKING URL FOUND!" -ForegroundColor Green
            Write-Host "Use this in your sync.ps1:" -ForegroundColor Yellow
            Write-Host '$SERVER_URL = "' -NoNewline
            Write-Host $currentUrl -ForegroundColor Cyan -NoNewline
            Write-Host '"'
            break
            
        } catch [System.Net.WebException] {
            $errorResponse = $_.Exception.Response
            if ($errorResponse) {
                $statusCode = [int]$errorResponse.StatusCode
                Write-Host "  Status: $statusCode" -ForegroundColor Yellow
                
                if ($statusCode -eq 308 -or $statusCode -eq 301 -or $statusCode -eq 302 -or $statusCode -eq 307) {
                    $location = $errorResponse.Headers["Location"]
                    Write-Host "  Redirects to: $location" -ForegroundColor Yellow
                    
                    if ($location) {
                        # Handle relative URLs
                        if ($location.StartsWith("http://") -or $location.StartsWith("https://")) {
                            $currentUrl = $location
                        } else {
                            # Relative URL - need to construct full URL
                            $uri = [System.Uri]$currentUrl
                            if ($location.StartsWith("/")) {
                                $currentUrl = "$($uri.Scheme)://$($uri.Host)$location"
                            } else {
                                $currentUrl = "$($uri.Scheme)://$($uri.Host)$($uri.AbsolutePath)/$location"
                            }
                        }
                        
                        Write-Host "  Following redirect..." -ForegroundColor Gray
                        Write-Host ""
                        $redirectCount++
                    } else {
                        Write-Host "  ❌ Redirect with no Location header!" -ForegroundColor Red
                        break
                    }
                } elseif ($statusCode -eq 400 -or $statusCode -eq 401 -or $statusCode -eq 422) {
                    Write-Host "  ✅ Endpoint responds! (Auth error is expected)" -ForegroundColor Green
                    
                    try {
                        $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
                        $errorText = $reader.ReadToEnd()
                        $reader.Close()
                        Write-Host "  Response: $errorText" -ForegroundColor Gray
                    } catch {}
                    
                    Write-Host ""
                    Write-Host "WORKING URL FOUND!" -ForegroundColor Green
                    Write-Host "Use this in your sync.ps1:" -ForegroundColor Yellow
                    Write-Host '$SERVER_URL = "' -NoNewline
                    Write-Host $currentUrl -ForegroundColor Cyan -NoNewline
                    Write-Host '"'
                    break
                } else {
                    Write-Host "  ❌ Error: Status $statusCode" -ForegroundColor Red
                    break
                }
                
                $errorResponse.Close()
            }
        }
    } catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        break
    }
}

if ($redirectCount -ge $maxRedirects) {
    Write-Host ""
    Write-Host "❌ Too many redirects!" -ForegroundColor Red
    Write-Host "The server is stuck in a redirect loop." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")