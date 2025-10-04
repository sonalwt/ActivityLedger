# ActivityWatch Sync Script - Dynamic Configuration
# Option 1: Use environment variables
# Option 2: Use config file
# Option 3: Use command line parameters
# Option 4: Interactive prompt

param(
    [string]$DeveloperName,
    [string]$ApiToken,
    [string]$ConfigFile = "sync_config.json"
)

# Server configuration
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Function to get configuration
function Get-SyncConfiguration {
    # Priority order: 
    # 1. Command line parameters
    # 2. Environment variables
    # 3. Config file
    # 4. Interactive prompt
    
    $config = @{
        DeveloperName = $null
        ApiToken = $null
    }
    
    # Check command line parameters
    if ($DeveloperName) {
        $config.DeveloperName = $DeveloperName
        Write-Host "Using developer name from command line: $DeveloperName" -ForegroundColor Green
    }
    if ($ApiToken) {
        $config.ApiToken = $ApiToken
        Write-Host "Using API token from command line" -ForegroundColor Green
    }
    
    # Check environment variables if not set
    if (-not $config.DeveloperName -and $env:TIMESHEET_DEVELOPER_NAME) {
        $config.DeveloperName = $env:TIMESHEET_DEVELOPER_NAME
        Write-Host "Using developer name from environment variable: $($config.DeveloperName)" -ForegroundColor Green
    }
    if (-not $config.ApiToken -and $env:TIMESHEET_API_TOKEN) {
        $config.ApiToken = $env:TIMESHEET_API_TOKEN
        Write-Host "Using API token from environment variable" -ForegroundColor Green
    }
    
    # Check config file if not set
    if ((-not $config.DeveloperName -or -not $config.ApiToken) -and (Test-Path $ConfigFile)) {
        try {
            $fileConfig = Get-Content $ConfigFile | ConvertFrom-Json
            if (-not $config.DeveloperName -and $fileConfig.DeveloperName) {
                $config.DeveloperName = $fileConfig.DeveloperName
                Write-Host "Using developer name from config file: $($config.DeveloperName)" -ForegroundColor Green
            }
            if (-not $config.ApiToken -and $fileConfig.ApiToken) {
                $config.ApiToken = $fileConfig.ApiToken
                Write-Host "Using API token from config file" -ForegroundColor Green
            }
        } catch {
            Write-Host "Warning: Could not read config file: $ConfigFile" -ForegroundColor Yellow
        }
    }
    
    # Interactive prompt if still not set
    if (-not $config.DeveloperName) {
        $config.DeveloperName = Read-Host "Enter your developer name"
    }
    if (-not $config.ApiToken) {
        $config.ApiToken = Read-Host "Enter your API token" -AsSecureString
        # Convert SecureString back to plain text
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($config.ApiToken)
        $config.ApiToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    }
    
    # Optionally save to config file
    if (-not (Test-Path $ConfigFile)) {
        $saveConfig = Read-Host "Would you like to save these credentials for future use? (y/n)"
        if ($saveConfig -eq 'y') {
            @{
                DeveloperName = $config.DeveloperName
                ApiToken = $config.ApiToken
            } | ConvertTo-Json | Set-Content $ConfigFile
            Write-Host "Configuration saved to $ConfigFile" -ForegroundColor Green
            Write-Host "WARNING: API token is stored in plain text. Keep this file secure!" -ForegroundColor Yellow
        }
    }
    
    return $config
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
Write-Host "ActivityWatch Sync Script"
Write-Host "========================================"

# Get configuration
$syncConfig = Get-SyncConfiguration

Write-Host ""
Write-Host "Configuration loaded:"
Write-Host "Developer: $($syncConfig.DeveloperName)"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    Send-ActivityData -DeveloperName $syncConfig.DeveloperName -ApiToken $syncConfig.ApiToken
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}
