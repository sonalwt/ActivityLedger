#!/bin/bash
# debug_redirect.sh - Run this on your server

echo "=== Debugging 308 Redirect ==="

# 1. Check all Apache configs
echo -e "\n1. Searching for redirect rules in Apache configs:"
sudo grep -r "308\|permanent\|https" /etc/apache2/ | grep -E "(RewriteRule|Redirect)" | grep -v "#"

# 2. Check which config file is active
echo -e "\n2. Active VirtualHosts:"
sudo apache2ctl -S

# 3. Check loaded modules
echo -e "\n3. Loaded Apache modules:"
sudo apache2ctl -M | grep -E "(rewrite|ssl|headers)"

# 4. Test endpoints
echo -e "\n4. Testing endpoints:"
echo "Direct to backend:"
curl -I http://localhost:8090/api/sync 2>/dev/null | head -n 1

echo -e "\nThrough Apache:"
curl -I http://api-timesheet.firsteconomy.com/api/sync 2>/dev/null | head -n 1

# 5. Check for .htaccess
echo -e "\n5. Checking for .htaccess files:"
sudo find /var/www -name ".htaccess" 2>/dev/null

# 6. Check Apache error log
echo -e "\n6. Recent Apache errors:"
sudo tail -n 20 /var/log/apache2/error.log | grep -i "rewrite\|redirect"

# 7. Check if there's an SSL VirtualHost
echo -e "\n7. SSL VirtualHosts:"
sudo ls -la /etc/apache2/sites-enabled/*ssl* 2>/dev/null
sudo ls -la /etc/apache2/sites-enabled/*443* 2>/dev/null

echo -e "\n=== End of debug ==="
