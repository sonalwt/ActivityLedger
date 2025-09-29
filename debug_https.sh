#!/bin/bash
# Run this on your server to debug HTTPS issues

echo "=== Debugging HTTPS 308 Redirect Issue ==="

# 1. Check if SSL is properly configured
echo -e "\n1. Checking SSL certificates:"
sudo certbot certificates | grep -A 3 "api-timesheet"

# 2. Check enabled Apache sites
echo -e "\n2. Enabled Apache sites:"
ls -la /etc/apache2/sites-enabled/

# 3. Check for SSL VirtualHost
echo -e "\n3. Looking for SSL configuration:"
sudo grep -r ":443" /etc/apache2/sites-available/
sudo grep -r "SSLEngine" /etc/apache2/

# 4. Test backend directly
echo -e "\n4. Testing backend directly (bypassing Apache):"
curl -I http://localhost:8090/api/sync

# 5. Check Apache SSL module
echo -e "\n5. Apache SSL modules:"
sudo apache2ctl -M | grep -E "(ssl|rewrite|proxy|headers)"

# 6. Check current Apache configuration
echo -e "\n6. Current VirtualHost configuration:"
sudo apache2ctl -S

# 7. Test with curl verbose
echo -e "\n7. Verbose HTTPS test:"
curl -Iv https://api-timesheet.firsteconomy.com/api/sync 2>&1 | head -20

# 8. Check if there's a global redirect
echo -e "\n8. Checking for global redirects:"
sudo grep -r "308\|R=permanent" /etc/apache2/conf-enabled/
sudo grep -r "308\|R=permanent" /etc/apache2/mods-enabled/

echo -e "\n=== End Debug ==="
