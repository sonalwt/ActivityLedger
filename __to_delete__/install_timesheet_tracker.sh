#!/bin/bash
# install_timesheet_tracker.sh
# One-click installer for automatic timesheet tracking

set -e

echo "🚀 Installing Timesheet Activity Tracker..."

# Configuration
API_URL="https://api-timesheet.firsteconomy.com/api/multi-dev"
INSTALL_DIR="$HOME/.timesheet-tracker"
SERVICE_NAME="timesheet-tracker"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if ActivityWatch is running
check_activitywatch() {
    if curl -s http://localhost:5600/api/0/info >/dev/null 2>&1; then
        print_status "ActivityWatch is running ✅"
        return 0
    else
        print_error "ActivityWatch is not running!"
        echo "Please start ActivityWatch first:"
        echo "  - Download from: https://activitywatch.net/downloads/"
        echo "  - Install and start it"
        echo "  - Then run this installer again"
        exit 1
    fi
}

# Get user configuration
get_user_config() {
    echo ""
    echo "📝 Configuration Setup"
    echo "======================="
    
    read -p "Enter your name (e.g., john_doe): " DEVELOPER_NAME
    read -s -p "Enter your API token: " API_TOKEN
    echo ""
    
    if [[ -z "$DEVELOPER_NAME" || -z "$API_TOKEN" ]]; then
        print_error "Name and API token are required!"
        exit 1
    fi
    
    print_status "Configuration saved"
}

# Create installation directory
create_install_dir() {
    print_status "Creating installation directory..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Check if pip3 is available
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install --user requests schedule
    elif command -v pip >/dev/null 2>&1; then
        pip install --user requests schedule
    else
        print_error "Python pip not found. Please install Python first."
        exit 1
    fi
}

# Create the tracker script
create_tracker_script() {
    print_status "Creating tracker script..."
    
    cat > "$INSTALL_DIR/tracker.py" << 'EOF'
#!/usr/bin/env python3
import json
import time
import requests
import schedule
from datetime import datetime, timezone, timedelta
import logging
import os

# Configure logging
log_file = os.path.join(os.path.dirname(__file__), 'logs', 'tracker.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoTracker:
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        self.config = self.load_config()
        self.last_sync = datetime.now(timezone.utc) - timedelta(minutes=5)
        
    def load_config(self):
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def get_activitywatch_data(self):
        """Get data from ActivityWatch"""
        try:
            # Get buckets
            response = requests.get('http://localhost:5600/api/0/buckets', timeout=10)
            response.raise_for_status()
            buckets = response.json()
            
            activities = []
            now = datetime.now(timezone.utc)
            
            for bucket_name in buckets:
                if 'afk' in bucket_name.lower():
                    continue
                
                # Get events since last sync
                params = {
                    'start': self.last_sync.isoformat(),
                    'end': now.isoformat(),
                    'limit': 1000
                }
                
                events_response = requests.get(
                    f'http://localhost:5600/api/0/buckets/{bucket_name}/events',
                    params=params,
                    timeout=10
                )
                
                if events_response.status_code != 200:
                    continue
                
                events = events_response.json()
                
                for event in events:
                    data = event.get('data', {})
                    duration = event.get('duration', 0)
                    
                    if duration < 5:  # Skip short activities
                        continue
                    
                    app_name = data.get('app', data.get('application', 'Unknown'))
                    if not app_name or app_name == 'Unknown':
                        continue
                    
                    activities.append({
                        'application_name': app_name,
                        'window_title': data.get('title', ''),
                        'duration': duration,
                        'timestamp': event.get('timestamp'),
                        'category': self.categorize_activity(app_name, data.get('title', '')),
                        'url': data.get('url')
                    })
            
            self.last_sync = now
            return activities
            
        except Exception as e:
            logger.error(f"Error getting ActivityWatch data: {e}")
            return []
    
    def categorize_activity(self, app_name, window_title):
        """Simple categorization"""
        app_lower = app_name.lower()
        
        if any(dev in app_lower for dev in ['code', 'cursor', 'pycharm', 'intellij']):
            return 'development'
        elif any(browser in app_lower for browser in ['chrome', 'firefox', 'edge']):
            return 'browser'
        elif any(db in app_lower for db in ['datagrip', 'pgadmin', 'dbeaver']):
            return 'database'
        else:
            return 'other'
    
    def upload_activities(self, activities):
        """Upload activities to server"""
        if not activities:
            return True
        
        try:
            headers = {
                'Authorization': f'Bearer {self.config["api_token"]}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.config["api_url"]}/activity/upload',
                headers=headers,
                json=activities,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Uploaded {result.get('processed', 0)} activities")
                return True
            else:
                logger.error(f"Upload failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def sync_job(self):
        """Scheduled sync job"""
        logger.info("Starting sync...")
        
        activities = self.get_activitywatch_data()
        if activities:
            self.upload_activities(activities)
        else:
            logger.info("No new activities to sync")
    
    def run(self):
        """Main loop"""
        logger.info(f"Starting auto-tracker for {self.config['developer_id']}")
        
        # Schedule syncs every 5 minutes
        schedule.every(5).minutes.do(self.sync_job)
        
        # Initial sync
        self.sync_job()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    tracker = AutoTracker()
    tracker.run()
EOF
    
    chmod +x "$INSTALL_DIR/tracker.py"
}

# Create configuration file
create_config() {
    print_status "Creating configuration file..."
    
    cat > "$INSTALL_DIR/config.json" << EOF
{
    "api_url": "$API_URL",
    "api_token": "$API_TOKEN",
    "developer_id": "$DEVELOPER_NAME",
    "sync_interval": 300
}
EOF
}

# Create systemd service (Linux) or launchd (macOS)
create_service() {
    print_status "Creating system service..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux systemd service
        mkdir -p ~/.config/systemd/user
        
        cat > ~/.config/systemd/user/timesheet-tracker.service << EOF
[Unit]
Description=Timesheet Activity Tracker
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $INSTALL_DIR/tracker.py
Restart=always
RestartSec=10
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF
        
        # Enable and start service
        systemctl --user daemon-reload
        systemctl --user enable timesheet-tracker.service
        systemctl --user start timesheet-tracker.service
        
        print_status "Service installed and started ✅"
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS launchd service
        mkdir -p ~/Library/LaunchAgents
        
        cat > ~/Library/LaunchAgents/com.timesheet.tracker.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.timesheet.tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/tracker.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/error.log</string>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/output.log</string>
</dict>
</plist>
EOF
        
        # Load and start service
        launchctl load ~/Library/LaunchAgents/com.timesheet.tracker.plist
        launchctl start com.timesheet.tracker
        
        print_status "Service installed and started ✅"
        
    else
        print_warning "Automatic service creation not supported on this OS"
        echo "To start manually, run: python3 $INSTALL_DIR/tracker.py"
    fi
}

# Test connection
test_connection() {
    print_status "Testing connection..."
    
    if python3 -c "
import requests
try:
    response = requests.get('$API_URL/health', timeout=10)
    print('✅ Server connection successful')
except:
    print('❌ Cannot reach server')
    exit(1)
"; then
        print_status "Connection test passed ✅"
    else
        print_error "Connection test failed ❌"
        exit 1
    fi
}

# Create uninstall script
create_uninstaller() {
    cat > "$INSTALL_DIR/uninstall.sh" << EOF
#!/bin/bash
echo "Uninstalling Timesheet Tracker..."

# Stop service
if [[ "\$OSTYPE" == "linux-gnu"* ]]; then
    systemctl --user stop timesheet-tracker.service
    systemctl --user disable timesheet-tracker.service
    rm -f ~/.config/systemd/user/timesheet-tracker.service
    systemctl --user daemon-reload
elif [[ "\$OSTYPE" == "darwin"* ]]; then
    launchctl unload ~/Library/LaunchAgents/com.timesheet.tracker.plist
    rm -f ~/Library/LaunchAgents/com.timesheet.tracker.plist
fi

# Remove installation directory
rm -rf "$INSTALL_DIR"

echo "✅ Timesheet Tracker uninstalled"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
}

# Main installation process
main() {
    echo "🕒 Timesheet Activity Tracker Installer"
    echo "========================================"
    
    # Check prerequisites
    check_activitywatch
    
    # Get configuration
    get_user_config
    
    # Install
    create_install_dir
    install_dependencies
    create_tracker_script
    create_config
    test_connection
    create_service
    create_uninstaller
    
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================="
    echo "✅ Activity tracker is now running automatically"
    echo "✅ Data will sync every 5 minutes"
    echo "✅ Logs: $INSTALL_DIR/logs/tracker.log"
    echo ""
    echo "Commands:"
    echo "  Status:    systemctl --user status timesheet-tracker"
    echo "  Stop:      systemctl --user stop timesheet-tracker"
    echo "  Start:     systemctl --user start timesheet-tracker"
    echo "  Uninstall: $INSTALL_DIR/uninstall.sh"
    echo ""
    print_status "Setup complete! Your activities are now being tracked automatically."
}

# Run main function
main
