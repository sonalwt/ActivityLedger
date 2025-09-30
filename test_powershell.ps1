# Simple test to verify PowerShell is working
Write-Host "Testing PowerShell execution..."

# Test 1: Basic function
function TestFunction {
    Write-Host "Function works!"
}

# Call function
TestFunction

# Test 2: Try-catch
try {
    Write-Host "Try block works!"
} catch {
    Write-Host "Catch block works!"
}

Write-Host "All tests passed!"