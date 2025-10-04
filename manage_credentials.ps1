# Secure Credential Management for Timesheet Sync
# This script manages credentials using Windows Credential Manager

function Set-TimesheetCredentials {
    param(
        [string]$DeveloperName = (Read-Host "Enter developer name"),
        [string]$ApiToken = (Read-Host "Enter API token" -AsSecureString | ConvertFrom-SecureString)
    )
    
    # Store developer name in registry (not sensitive)
    New-ItemProperty -Path "HKCU:\Software\TimesheetSync" -Name "DeveloperName" -Value $DeveloperName -Force | Out-Null
    
    # Store API token securely using Windows Data Protection API
    $tokenPath = "$env:APPDATA\TimesheetSync\token.secure"
    $tokenDir = Split-Path $tokenPath -Parent
    
    if (-not (Test-Path $tokenDir)) {
        New-Item -ItemType Directory -Path $tokenDir -Force | Out-Null
    }
    
    $ApiToken | Set-Content $tokenPath
    
    Write-Host "Credentials saved securely!" -ForegroundColor Green
    Write-Host "Developer name: $DeveloperName" -ForegroundColor Cyan
    Write-Host "API token: [SECURED]" -ForegroundColor Cyan
}

function Get-TimesheetCredentials {
    $credentials = @{
        DeveloperName = $null
        ApiToken = $null
    }
    
    # Get developer name from registry
    try {
        $credentials.DeveloperName = (Get-ItemProperty -Path "HKCU:\Software\TimesheetSync" -Name "DeveloperName" -ErrorAction Stop).DeveloperName
    } catch {
        Write-Host "No saved developer name found" -ForegroundColor Yellow
    }
    
    # Get API token from secure storage
    $tokenPath = "$env:APPDATA\TimesheetSync\token.secure"
    if (Test-Path $tokenPath) {
        try {
            $encryptedToken = Get-Content $tokenPath
            $secureToken = ConvertTo-SecureString $encryptedToken
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
            $credentials.ApiToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        } catch {
            Write-Host "Could not decrypt API token" -ForegroundColor Red
        }
    } else {
        Write-Host "No saved API token found" -ForegroundColor Yellow
    }
    
    return $credentials
}

function Remove-TimesheetCredentials {
    # Remove from registry
    Remove-ItemProperty -Path "HKCU:\Software\TimesheetSync" -Name "DeveloperName" -ErrorAction SilentlyContinue
    
    # Remove secure token file
    $tokenPath = "$env:APPDATA\TimesheetSync\token.secure"
    if (Test-Path $tokenPath) {
        Remove-Item $tokenPath -Force
    }
    
    Write-Host "Credentials removed!" -ForegroundColor Green
}

# Menu for credential management
Write-Host "========================================"
Write-Host "Timesheet Sync - Credential Manager"
Write-Host "========================================"
Write-Host ""
Write-Host "1. Set/Update credentials"
Write-Host "2. View saved developer name"
Write-Host "3. Test credentials"
Write-Host "4. Remove all credentials"
Write-Host "5. Exit"
Write-Host ""

$choice = Read-Host "Enter your choice (1-5)"

switch ($choice) {
    "1" {
        Set-TimesheetCredentials
    }
    "2" {
        $creds = Get-TimesheetCredentials
        if ($creds.DeveloperName) {
            Write-Host "Developer name: $($creds.DeveloperName)" -ForegroundColor Green
        } else {
            Write-Host "No developer name saved" -ForegroundColor Yellow
        }
    }
    "3" {
        $creds = Get-TimesheetCredentials
        if ($creds.DeveloperName -and $creds.ApiToken) {
            Write-Host "Credentials found:" -ForegroundColor Green
            Write-Host "Developer: $($creds.DeveloperName)" -ForegroundColor Cyan
            Write-Host "API Token: [PRESENT]" -ForegroundColor Cyan
        } else {
            Write-Host "Missing credentials:" -ForegroundColor Red
            if (-not $creds.DeveloperName) { Write-Host "- Developer name" -ForegroundColor Yellow }
            if (-not $creds.ApiToken) { Write-Host "- API token" -ForegroundColor Yellow }
        }
    }
    "4" {
        $confirm = Read-Host "Are you sure you want to remove all credentials? (y/n)"
        if ($confirm -eq 'y') {
            Remove-TimesheetCredentials
        }
    }
    "5" {
        exit
    }
    default {
        Write-Host "Invalid choice!" -ForegroundColor Red
    }
}
