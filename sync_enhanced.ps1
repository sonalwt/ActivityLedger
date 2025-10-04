# Enhanced ActivityWatch Sync Script with Categorization
$DEVELOPER_NAME = "mrunali"
$API_TOKEN = "[PASTE_THE_GENERATED_TOKEN_HERE]"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Categorization patterns
$ProductivePatterns = @(
    "visual studio", "vscode", "vs code", "cursor", "sublime", "atom",
    "intellij", "pycharm", "webstorm", "eclipse", "vim", "notepad\+\+",
    "git", "github desktop", "docker", "terminal", "cmd", "powershell",
    "\.js$", "\.py$", "\.php$", "\.html$", "\.css$", "\.json$",
    "timesheet", "project", "development", "localhost"
)

$BrowserPatterns = @(
    "chrome", "firefox", "edge", "safari", "opera", "brave",
    "claude", "chatgpt", "stackoverflow", "github\.com",
    "google", "docs\.", "documentation", "api\."
)

$ServerPatterns = @(
    "aws", "ec2", "s3", "azure", "gcp", "digitalocean",
    "ssh", "rdp", "cpanel", "kubernetes", "docker"
)

$NonWorkPatterns = @(
    "youtube", "netflix", "spotify", "twitch", "game",
    "lock screen", "locked", "idle"
)

function Get-Category {
    param($Title, $App)
    
    $Combined = "$Title $App".ToLower()
    
    # Check non-work first
    foreach ($pattern in $NonWorkPatterns) {
        if ($Combined -match $pattern) {
            return "non-work"
        }
    }
    
    # Check productive
    $productiveScore = 0
    foreach ($pattern in $ProductivePatterns) {
        if ($Combined -match $pattern) {
            $productiveScore++
        }
    }
    
    # Check browser
    $browserScore = 0
    foreach ($pattern in $BrowserPatterns) {
        if ($Combined -match $pattern) {
            $browserScore++
        }
    }
    
    # Check server
    $serverScore = 0
    foreach ($pattern in $ServerPatterns) {
        if ($Combined -match $pattern) {
            $serverScore++
        }
    }
    
    # Return highest scoring category
    if ($productiveScore -gt $browserScore -and $productiveScore -gt $serverScore) {
        return "productive"
    }
    elseif ($browserScore -gt $serverScore) {
        return "browser"
    }
    elseif ($serverScore -gt 0) {
        return "server"
    }
    else {
        # Default categorization based on app
        if ($App -match "code|cursor|studio|pycharm") {
            return "productive"
        }
        elseif ($App -match "chrome|firefox|edge") {
            return "browser"
        }
        else {
            return "uncategorized"
        }
    }
}

function Process-ActivityData {
    param($Events, $BucketName)
    
    $ProcessedActivities = @()
    
    foreach ($event in $Events) {
        $data = $event.data
        $duration = $event.duration
        
        # Skip very short activities (less than 5 seconds)
        if ($duration -lt 5) {
            continue
        }
        
        # Extract fields
        $windowTitle = if ($data.title) { $data.title } else { "Untitled" }
        $appName = if ($data.app) { $data.app } else { "Unknown" }
        
        # Clean window title
        $windowTitle = $windowTitle -replace " - Google Chrome$", ""
        $windowTitle = $windowTitle -replace " - Mozilla Firefox$", ""
        $windowTitle = $windowTitle -replace " - Visual Studio Code$", ""
        
        # Get category
        $category = Get-Category -Title $windowTitle -App $appName
        
        # Extract project name
        $projectName = "general"
        if ($windowTitle -match " - ([^-]+) - (?:Visual Studio Code|VS Code|Cursor)") {
            $projectName = $Matches[1].Trim()
        }
        elseif ($windowTitle -match "\\([^\\]+)\\[^\\]+\.[a-z]+$") {
            $projectName = $Matches[1]
        }
        
        $activity = @{
            developer_id = $DEVELOPER_NAME
            application_name = $appName
            window_title = $windowTitle.Substring(0, [Math]::Min($windowTitle.Length, 500))
            duration = [int]($duration * 1000)  # Convert to milliseconds
            timestamp = $event.timestamp
            category = $category
            project_name = $projectName
            url = if ($data.url) { $data.url } else { "" }
            file_path = if ($data.file) { $data.file } else { "" }
        }
        
        $ProcessedActivities += $activity
    }
    
    return $ProcessedActivities
}

function Send-ActivityData {
    try {
        # Get buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets/" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        # Time range
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        $allActivities = @()
        $categoryCount = @{
            productive = 0
            browser = 0
            server = 0
            "non-work" = 0
            uncategorized = 0
        }
        
        foreach ($bucket in $buckets) {
            # Skip AFK buckets
            if ($bucket -like "*afk*") {
                continue
            }
            
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO&limit=1000"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                
                if ($events -and $events.Count -gt 0) {
                    Write-Host "  - $bucket`: $($events.Count) events" -ForegroundColor DarkGray
                    
                    # Process and categorize events
                    $processedEvents = Process-ActivityData -Events $events -BucketName $bucket
                    
                    foreach ($activity in $processedEvents) {
                        $allActivities += $activity
                        $categoryCount[$activity.category]++
                    }
                }
            } catch {
                Write-Host "  - Error processing $bucket" -ForegroundColor Yellow
            }
        }
        
        if ($allActivities.Count -gt 0) {
            Write-Host ""
            Write-Host "Category breakdown:" -ForegroundColor Cyan
            foreach ($cat in $categoryCount.Keys) {
                if ($categoryCount[$cat] -gt 0) {
                    Write-Host "  - ${cat}: $($categoryCount[$cat]) activities" -ForegroundColor DarkGray
                }
            }
            
            Write-Host ""
            Write-Host "Sending $($allActivities.Count) categorized activities to server..." -ForegroundColor Cyan
            
            $payload = @{
                name = $DEVELOPER_NAME
                token = $API_TOKEN
                data = $allActivities
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allActivities.Count) activities" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new activities to sync"
        }
        
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "========================================"
Write-Host "Enhanced ActivityWatch Sync for $DEVELOPER_NAME"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}
