# Save this as fix-api-urls.ps1 in your frontend directory
# Run with: .\fix-api-urls.ps1

Write-Host "Fixing API URLs for production..." -ForegroundColor Green

# Step 1: Find all files with localhost:8000
Write-Host "`nStep 1: Finding files with localhost:8000..." -ForegroundColor Yellow
$files = Get-ChildItem -Path "src" -Recurse -Include "*.js","*.jsx" | 
         Select-String -Pattern "localhost:8000" | 
         Select-Object -Unique Path

if ($files.Count -eq 0) {
    Write-Host "No files found with localhost:8000" -ForegroundColor Red
    exit
}

Write-Host "Found $($files.Count) files to update:" -ForegroundColor Cyan
$files | ForEach-Object { Write-Host "  - $($_.Path)" }

# Step 2: Create backup
Write-Host "`nStep 2: Creating backup..." -ForegroundColor Yellow
$backupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

foreach ($file in $files) {
    $relativePath = $file.Path.Replace("$PWD\", "")
    $backupPath = Join-Path $backupDir $relativePath
    $backupFolder = Split-Path $backupPath -Parent
    New-Item -ItemType Directory -Path $backupFolder -Force -ErrorAction SilentlyContinue | Out-Null
    Copy-Item $file.Path $backupPath
}
Write-Host "Backup created in: $backupDir" -ForegroundColor Green

# Step 3: Replace URLs
Write-Host "`nStep 3: Replacing URLs..." -ForegroundColor Yellow
foreach ($file in $files) {
    $content = Get-Content $file.Path -Raw
    $newContent = $content -replace 'http://localhost:8000', 'https://api-timesheet.firsteconomy.com'
    
    if ($content -ne $newContent) {
        Set-Content -Path $file.Path -Value $newContent
        Write-Host "  ✓ Updated: $($file.Path)" -ForegroundColor Green
    }
}

# Step 4: Create environment config file
Write-Host "`nStep 4: Creating config file..." -ForegroundColor Yellow
$configContent = @"
// API Configuration
const config = {
  API_URL: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://api-timesheet.firsteconomy.com'
};

export default config;
"@

$configPath = "src/config.js"
if (-not (Test-Path "src")) {
    Write-Host "src directory not found. Make sure you're in the React app root!" -ForegroundColor Red
} else {
    Set-Content -Path $configPath -Value $configContent
    Write-Host "  ✓ Created: $configPath" -ForegroundColor Green
}

# Step 5: Show next steps
Write-Host "`n✅ URL replacement complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Review the changes (backup saved in: $backupDir)"
Write-Host "2. Run: npm run build"
Write-Host "3. Deploy the build folder to your server"
Write-Host "`nOptional: Update your code to use the config file:"
Write-Host "  import config from './config';"
Write-Host "  fetch(`${config.API_URL}/api/...`)"

# Offer to build now
$response = Read-Host "`nDo you want to run 'npm run build' now? (y/n)"
if ($response -eq 'y') {
    Write-Host "`nBuilding production version..." -ForegroundColor Yellow
    npm run build
    Write-Host "`n✅ Build complete! Deploy the 'build' folder to your server." -ForegroundColor Green
}