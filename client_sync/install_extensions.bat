@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM ActivityWatch Extensions Installer
REM Works on ANY Windows PC - No Python needed!
REM Installs browser + code tracking extensions
REM ============================================================

echo.
echo ============================================================
echo   ActivityWatch Extensions Installer
echo   Installs browser and code tracking extensions
echo ============================================================
echo.

REM ── 1. Chrome Browser Extension ──
echo [1/2] ActivityWatch Browser Extension (Chrome)...
echo.
echo       This tracks which websites you visit and for how long.
echo       A Chrome Web Store page will open now.
echo       Please click "Add to Chrome" to install.
echo.
start "" "https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi"
echo       [OK] Chrome Web Store opened
echo.
timeout /t 3 >nul

REM ── 2. VS Code Extension (only if VS Code is installed) ──
echo [2/2] ActivityWatch VS Code Extension...
where code >nul 2>&1
if !errorlevel! equ 0 (
    echo       VS Code found - installing extension...
    code --install-extension activitywatch.aw-watcher-vscode --force >nul 2>&1
    if !errorlevel! equ 0 (
        echo       [OK] aw-watcher-vscode installed successfully
    ) else (
        echo       [WARN] Auto-install failed.
        echo       Open VS Code ^> Extensions ^> Search "ActivityWatch" ^> Install
    )
) else (
    echo       [SKIP] VS Code not installed on this PC - skipping
)
echo.

REM ── Done ──
echo ============================================================
echo   DONE!
echo ============================================================
echo.
echo   Browser extension: Click "Add to Chrome" in the opened tab
echo   VS Code extension: Installed automatically (if VS Code found)
echo.
echo   After installing, restart ActivityWatch to start tracking.
echo ============================================================
echo.
pause
