# ActivityWatch Sync Client

Automatically syncs your local ActivityWatch data to the central timesheet server with **reliable auto-start** and **system tray visibility**.

## Quick Start (Windows)

### 1. Setup and Configure

```batch
# Double-click to run
setup.bat
```

This creates a virtual environment and installs dependencies.

### 2. Configure Your Credentials

Edit the `.env` file with your details:
```env
SERVER_URL=https://api-timesheet.firsteconomy.com/api/sync
DEVELOPER_ID=your-name-here
API_TOKEN=your-api-token-from-registration
```

### 3. Install Auto-Start

```batch
# Double-click to install
install_autostart.bat
```

This will:
- Set up **3 redundant auto-start methods** (Startup folder, Registry, Scheduled Task)
- Create a **system tray icon** so you can see it's running
- Start the sync client immediately

**That's it!** The sync will now:
- Start automatically when Windows starts
- Show a green icon in your system tray (near the clock)
- Sync your ActivityWatch data every 5 minutes

---

## Files Overview

| File | Purpose |
|------|---------|
| `install_autostart.bat` | **One-click installer** - sets up everything |
| `check_status.bat` | **Troubleshooter** - diagnoses problems |
| `uninstall_autostart.bat` | Removes auto-start (keeps files) |
| `start_visible.bat` | Start sync with visible console window |
| `run_sync.bat` | Start sync in background with tray icon |

---

## Troubleshooting

### Sync Not Starting Automatically?

Run `check_status.bat` to diagnose issues:

```batch
check_status.bat
```

It will check:
- Python installation
- ActivityWatch connection
- Configuration file
- Running processes
- Auto-start settings

### Common Issues

| Problem | Solution |
|---------|----------|
| No tray icon visible | Click the ^ arrow in taskbar to see hidden icons |
| ActivityWatch not running | Start ActivityWatch application first |
| "Python not found" | Install Python from python.org |
| Sync errors in log | Check your API_TOKEN in .env file |

### View Logs

Open `sync_service.log` or `activitywatch_sync.log` to see what's happening.

---

## Manual Commands

```batch
# Activate virtual environment
venv\Scripts\activate.bat

# Test connections
python activitywatch_sync.py --test

# One-time sync (last 24 hours)
python activitywatch_sync.py --sync-hours 24

# Run continuous sync
python activitywatch_sync.py --continuous
```

---

## System Tray Icon

When running, you'll see a small icon near your clock:

- 🟢 **Green** = Sync OK
- 🟡 **Yellow** = Syncing in progress
- 🔴 **Red** = Error (check logs)

**Right-click the icon** for options:
- Sync Now
- Open Log
- Quit

---

## Configuration Options

Edit `.env` to customize:

```env
# Server to sync to
SERVER_URL=https://api-timesheet.firsteconomy.com/api/sync

# Your credentials
DEVELOPER_ID=john-doe
API_TOKEN=your-token-here

# How often to sync (minutes)
SYNC_INTERVAL_MINUTES=5

# Log detail level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# ActivityWatch location (usually don't change)
ACTIVITYWATCH_HOST=http://localhost:5600
```

---

## Linux/macOS

### Setup
```bash
chmod +x setup.sh
./setup.sh
```

### Configure
```bash
cp .env.template .env
nano .env  # Edit with your credentials
```

### Run
```bash
source venv/bin/activate
python activitywatch_sync.py --continuous
```

### Auto-Start (Linux systemd)

Create `/etc/systemd/system/activitywatch-sync.service`:
```ini
[Unit]
Description=ActivityWatch Sync
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/client_sync
ExecStart=/path/to/client_sync/venv/bin/python activitywatch_sync.py --continuous
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable activitywatch-sync
sudo systemctl start activitywatch-sync
```

---

## Privacy

The sync client only sends:
- Application names (e.g., "VSCode", "Chrome")
- Window titles
- Activity durations
- Timestamps

**Never sent:** File contents, screenshots, keystrokes, passwords

---

## Support

1. Run `check_status.bat` first
2. Check the log files
3. Contact your system administrator with:
   - Your DEVELOPER_ID
   - Error messages from logs
