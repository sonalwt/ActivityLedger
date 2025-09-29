#!/bin/bash
# fix_https_redirect.sh - Run this on your server

echo "=== Fixing HTTPS Redirect Issues ==="

# 1. Backup current nginx config
sudo cp /etc/nginx/sites-available/api-timesheet.firsteconomy.com /etc/nginx/sites-available/api-timesheet.firsteconomy.com.backup

# 2. Install SSL certificate if not already done
if [ ! -f "/etc/letsencrypt/live/api-timesheet.firsteconomy.com/fullchain.pem" ]; then
    echo "Installing SSL certificate..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
    sudo certbot --nginx -d api-timesheet.firsteconomy.com
fi

# 3. Update backend configuration
BACKEND_DIR="/path/to/timesheet_new/backend"  # Update this path
if [ -f "$BACKEND_DIR/.env.production" ]; then
    echo "Updating backend .env.production..."
    sed -i 's|PRODUCTION_DOMAIN=http://|PRODUCTION_DOMAIN=https://|g' $BACKEND_DIR/.env.production
fi

# 4. Update frontend configuration
FRONTEND_DIR="/path/to/timesheet_new/frontend"  # Update this path
if [ -f "$FRONTEND_DIR/.env.production" ]; then
    echo "Updating frontend .env.production..."
    sed -i 's|REACT_APP_API_URL=http://|REACT_APP_API_URL=https://|g' $FRONTEND_DIR/.env.production
fi

# 5. Test nginx configuration
echo "Testing nginx configuration..."
sudo nginx -t

# 6. Reload nginx
if [ $? -eq 0 ]; then
    echo "Reloading nginx..."
    sudo systemctl reload nginx
else
    echo "Nginx configuration has errors. Please fix them."
fi

# 7. Restart backend service
echo "Restarting backend service..."
sudo systemctl restart timesheet-backend  # Update with your service name

echo "=== Done! ==="
echo "Test your API with: curl -I https://api-timesheet.firsteconomy.com/api/sync"
