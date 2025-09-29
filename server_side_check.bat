@echo off
REM server_side_check.bat - Commands to run ON THE SERVER to check configuration

cls
echo ========================================
echo Server-Side 308 Redirect Check
echo ========================================
echo.
echo Run these commands ON YOUR SERVER (via SSH) to find the issue:
echo.
echo 1. Check Apache configuration:
echo    grep -r "308\|permanent\|Redirect" /etc/apache2/
echo.
echo 2. Check enabled sites:
echo    ls -la /etc/apache2/sites-enabled/
echo    cat /etc/apache2/sites-enabled/api-timesheet*
echo.
echo 3. Check if backend is actually running:
echo    sudo netstat -tlnp | grep 8090
echo    curl http://localhost:8090/api/sync
echo.
echo 4. Check Apache access logs:
echo    sudo tail -f /var/log/apache2/api-timesheet-backend_access.log
echo.
echo 5. Check for .htaccess files:
echo    find /var/www -name .htaccess -exec grep -H "Redirect\|Rewrite" {} \;
echo.
echo 6. Test locally on server:
echo    curl -X POST http://localhost:8090/api/sync -H "Content-Type: application/json" -d '{"test":true}' -v
echo.
pause
