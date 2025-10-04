# ActivityWatch Sync Script - Using Secure Credentials
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Function to get secure credentials
function Get-SecureCredentials {
    $credentials = @{
        DeveloperName = $null
        ApiToken = $null
    }
    
    # Get developer name from registry
    try {
        $credentials.DeveloperName = (Get-ItemProperty -Path "HKCU:\Software\TimesheetSync" -Name "DeveloperName" -ErrorAction Stop).DeveloperName
        Write-Host "Loaded developer name: $($credentials.DeveloperName)" -ForegroundColor Green
    } catch {
        Write-Host "No saved developer name found!" -ForegroundColor Red
        Write-Host "Please run manage_credentials.bat first to set up your credentials." -ForegroundColor Yellow
        return $null
    }
    
    # Get API token from secure storage
    $tokenPath = "$env:APPDATA\TimesheetSync\token.secure"
    if (Test-Path $tokenPath) {
        try {
            $encryptedToken = Get-Content $tokenPath
            $secureToken = ConvertTo-SecureString $encryptedToken
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
            $credentials.ApiToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
            Write-Host "Loaded API token: [SECURED]" -ForegroundColor Green
        } catch {
            Write-Host "Could not decrypt API token!" -ForegroundColor Red
            Write-Host "Please run manage_credentials.bat to reset your credentials." -ForegroundColor Yellow
            return $null
        }
    } else {
        Write-Host "No saved API token found!" -ForegroundColor Red
        Write-Host "Please run manage_credentials.bat first to set up your credentials." -ForegroundColor Yellow
        return $null
    }
    
    return $credentials
}

function Send-ActivityData {
    param(
        [string]$DeveloperName,
        [string]$ApiToken
    )
    
    try {
        Write-Host "$LOCAL_AW/buckets"
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets/" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                if ($events -and $events.Count -gt 0) {
                    # Transform events to match expected format
                    foreach ($event in $events) {
                        # Ensure data structure matches what the API expects
                        if (-not $event.data) {
                            $event | Add-Member -NotePropertyName "data" -NotePropertyValue @{} -Force
                        }
                        
                        # Make sure essential fields exist
                        if (-not $event.data.title) {
                            $event.data | Add-Member -NotePropertyName "title" -NotePropertyValue "Untitled" -Force
                        }
                        if (-not $event.data.app -and -not $event.data.application) {
                            $event.data | Add-Member -NotePropertyName "app" -NotePropertyValue "Unknown" -Force
                        }
                        
                        $allEvents += $event
                    }
                    Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                # Skip bucket if error
            }
        }
        
        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) events to server..." -ForegroundColor Cyan
            
            $payload = @{
                name = $DeveloperName
                token = $ApiToken
                data = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                    Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor Gray
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Write-Host "========================================"
Write-Host "ActivityWatch Sync - Secure Mode"
Write-Host "========================================"

# Get secure credentials
$credentials = Get-SecureCredentials
if (-not $credentials) {
    Write-Host ""
    Write-Host "Exiting due to missing credentials." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Configuration loaded from secure storage"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    Send-ActivityData -DeveloperName $credentials.DeveloperName -ApiToken $credentials.ApiToken
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}
