# Test the fixed syntax
$bucket = "test-bucket"
$events = @(1,2,3,4,5)

# This was causing the error:
# Write-Host "  - $bucket: $($events.Count) events"

# Fixed version:
Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray

Write-Host "✓ Syntax test passed!" -ForegroundColor Green