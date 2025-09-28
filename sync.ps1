# ActivityWatch Sync Script - Improved
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"

        # Time range
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        # Collect events
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                $allEvents += $events
            } catch {
                Write-Host "Warning: Could not get events from bucket $bucket"
            }
        }

        if ($allEvents.Count -gt 0) {
            # Prepare payload
            $payload = @{
                name      = $DEVELOPER_NAME
                data      = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress

            # Use HttpClient to follow 308 redirects automatically
            Add-Type @"
using System.Net;
using System.Net.Http;
public class HttpClientHelper {
    public static string PostJson(string url, string json, string token) {
        var handler = new HttpClientHandler { AllowAutoRedirect = true };
        using (var client = new HttpClient(handler)) {
            client.DefaultRequestHeaders.Add("Authorization", "Bearer " + token);
            var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
            var response = client.PostAsync(url, content).Result;
            return response.Content.ReadAsStringAsync().Result;
        }
    }
}
"@

            $responseText = [HttpClientHelper]::PostJson($SERVER_URL, $jsonPayload, $API_TOKEN)
            $responseObj = $responseText | ConvertFrom-Json

            if ($responseObj.success) {
                Write-Host "Synced $($allEvents.Count) events successfully" -ForegroundColor Green
            } else {
                Write-Host "Server error: $($responseObj.error)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Write-Host "=========================================="
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME" -ForegroundColor Cyan
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Continuous sync loop
while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)"
    Start-Sleep -Seconds 300
}
