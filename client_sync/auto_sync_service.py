#!/usr/bin/env python3
"""
ActivityWatch Auto-Sync Service
Zero-configuration background service that automatically syncs ActivityWatch data.
Auto-detects developer identity from system and installs itself to run on startup.
"""

import os
import sys
import time
import socket
import getpass
import hashlib
import threading
import logging
import subprocess
import ctypes
import winreg
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional

# Constants
SCRIPT_DIR = Path(__file__).parent.absolute()
LOG_FILE = SCRIPT_DIR / "auto_sync.log"
CONFIG_FILE = SCRIPT_DIR / "sync_config.json"

# Server configuration - UPDATE THIS TO YOUR SERVER
SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
ACTIVITYWATCH_HOST = "http://localhost:5600"
SYNC_INTERVAL_MINUTES = 5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Only add console handler if not running hidden
if not getattr(sys, 'frozen', False) and '--hidden' not in sys.argv:
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def is_admin():
    """Check if running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def get_machine_id() -> str:
    """Generate a unique machine identifier"""
    hostname = socket.gethostname()
    username = getpass.getuser()
    unique_string = f"{hostname}-{username}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]


def get_developer_identity() -> tuple:
    """Auto-detect developer identity from system"""
    hostname = socket.gethostname()
    username = getpass.getuser()

    # Create a developer ID from username and hostname
    developer_id = f"{username.lower().replace(' ', '-')}"

    # Create a token from machine-specific info (for authentication)
    machine_id = get_machine_id()
    api_token = f"auto-{machine_id}-{hashlib.md5(f'{hostname}{username}'.encode()).hexdigest()[:16]}"

    return developer_id, api_token, hostname


def ensure_dependencies():
    """Ensure required packages are installed"""
    required = ['requests', 'pystray', 'pillow']

    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            logger.info(f"Installing {package}...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package, '-q'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def install_autostart():
    """Install this script to run on Windows startup"""
    script_path = str(SCRIPT_DIR / "auto_sync_service.py")
    python_exe = sys.executable

    # Create a VBS launcher for hidden execution
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{SCRIPT_DIR}"
WshShell.Run """{python_exe}"" ""{script_path}"" --hidden", 0, False
'''
    vbs_path = SCRIPT_DIR / "run_hidden.vbs"
    vbs_path.write_text(vbs_content)

    # Method 1: Add to Windows Startup folder
    startup_folder = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_vbs = startup_folder / "ActivityWatch-AutoSync.vbs"

    try:
        startup_vbs.write_text(vbs_content)
        logger.info(f"Added to Startup folder: {startup_vbs}")
    except Exception as e:
        logger.warning(f"Could not add to Startup folder: {e}")

    # Method 2: Add to Registry
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ActivityWatchAutoSync", 0, winreg.REG_SZ, f'wscript.exe "{vbs_path}"')
        winreg.CloseKey(key)
        logger.info("Added to Registry startup")
    except Exception as e:
        logger.warning(f"Could not add to Registry: {e}")

    logger.info("Auto-start installation complete")


def check_already_running() -> bool:
    """Check if another instance is already running"""
    lock_file = SCRIPT_DIR / ".sync_lock"

    if lock_file.exists():
        try:
            # Check if the PID in the lock file is still running
            pid = int(lock_file.read_text().strip())
            # Try to check if process exists (Windows)
            subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True)
            if str(pid) in subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True).decode():
                return True
        except:
            pass

    # Write our PID
    lock_file.write_text(str(os.getpid()))
    return False


class AutoSyncService:
    """Main sync service that runs in background"""

    def __init__(self):
        self.developer_id, self.api_token, self.hostname = get_developer_identity()
        self.running = True
        self.last_sync = None
        self.sync_count = 0
        self.error_count = 0
        self.icon = None

        logger.info(f"Developer ID: {self.developer_id}")
        logger.info(f"Hostname: {self.hostname}")
        logger.info(f"Server: {SERVER_URL}")

    def get_activity_data(self, hours_back: float = 1.0) -> List[Dict]:
        """Fetch activity data from local ActivityWatch"""
        import requests

        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)

            # Get buckets
            buckets_resp = requests.get(f"{ACTIVITYWATCH_HOST}/api/0/buckets/", timeout=10)
            buckets_resp.raise_for_status()
            buckets = buckets_resp.json()

            activities = []

            for bucket_name in buckets.keys():
                if 'afk' in bucket_name.lower():
                    continue

                params = {
                    'start': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'end': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'limit': 5000
                }

                try:
                    events_resp = requests.get(
                        f"{ACTIVITYWATCH_HOST}/api/0/buckets/{bucket_name}/events",
                        params=params, timeout=15
                    )
                    events_resp.raise_for_status()

                    for event in events_resp.json():
                        data = event.get('data', {})
                        duration = event.get('duration', 0)

                        if duration < 5:  # Skip very short activities
                            continue

                        app_name = data.get('app', data.get('application', ''))
                        if not app_name:
                            continue

                        activities.append({
                            "timestamp": event.get('timestamp', ''),
                            "duration": duration,
                            "data": {
                                "app": app_name,
                                "title": data.get('title', ''),
                                "url": data.get('url')
                            }
                        })
                except Exception as e:
                    logger.debug(f"Error fetching {bucket_name}: {e}")

            return activities

        except Exception as e:
            logger.error(f"Error connecting to ActivityWatch: {e}")
            return []

    def sync_to_server(self, activities: List[Dict]) -> bool:
        """Send activities to central server"""
        import requests

        if not activities:
            logger.debug("No activities to sync")
            return True

        payload = {
            "name": self.developer_id,
            "token": self.api_token,
            "hostname": self.hostname,
            "data": activities,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            response = requests.post(
                SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            result = response.json()

            if result.get("success"):
                logger.info(f"Synced {len(activities)} activities")
                return True
            else:
                logger.error(f"Server error: {result.get('error', 'Unknown')}")
                return False

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False

    def do_sync(self, hours_back: float = None):
        """Perform a sync operation"""
        if hours_back is None:
            hours_back = (SYNC_INTERVAL_MINUTES / 60) + 0.5

        try:
            self.update_icon("yellow")

            activities = self.get_activity_data(hours_back)
            success = self.sync_to_server(activities)

            self.last_sync = datetime.now()

            if success:
                self.sync_count += 1
                self.update_icon("green")
            else:
                self.error_count += 1
                self.update_icon("red")

        except Exception as e:
            self.error_count += 1
            self.update_icon("red")
            logger.error(f"Sync error: {e}")

    def create_icon_image(self, color="green"):
        """Create system tray icon"""
        from PIL import Image, ImageDraw

        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        colors = {
            "green": (0, 200, 0, 255),
            "yellow": (255, 200, 0, 255),
            "red": (200, 0, 0, 255),
            "gray": (128, 128, 128, 255)
        }

        draw.ellipse([4, 4, size-4, size-4], fill=colors.get(color, colors["gray"]))

        try:
            draw.text((size//2 - 12, size//2 - 8), "AW", fill=(255, 255, 255, 255))
        except:
            pass

        return image

    def update_icon(self, color):
        """Update tray icon color"""
        if self.icon:
            try:
                self.icon.icon = self.create_icon_image(color)
                self.icon.title = f"ActivityWatch Sync\n{self.developer_id}\nSyncs: {self.sync_count}"
            except:
                pass

    def sync_loop(self):
        """Background sync loop"""
        logger.info("Starting sync loop...")

        # Initial sync - last 24 hours
        logger.info("Initial sync (last 24 hours)...")
        self.do_sync(hours_back=24)

        # Regular sync loop
        while self.running:
            try:
                # Wait for next interval
                for _ in range(SYNC_INTERVAL_MINUTES * 60):
                    if not self.running:
                        break
                    time.sleep(1)

                if self.running:
                    self.do_sync()

            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(60)

        logger.info("Sync loop stopped")

    def on_quit(self, icon, item):
        """Quit the service"""
        self.running = False
        icon.stop()

    def on_sync_now(self, icon, item):
        """Manual sync trigger"""
        threading.Thread(target=self.do_sync, daemon=True).start()

    def run(self):
        """Main entry point"""
        logger.info("=" * 50)
        logger.info("ActivityWatch Auto-Sync Service")
        logger.info(f"Developer: {self.developer_id}")
        logger.info("=" * 50)

        try:
            import pystray
            from pystray import MenuItem as item

            menu = pystray.Menu(
                item('Sync Now', self.on_sync_now),
                item(f'ID: {self.developer_id}', lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                item('Quit', self.on_quit)
            )

            self.icon = pystray.Icon(
                "ActivityWatch AutoSync",
                self.create_icon_image("green"),
                f"ActivityWatch Sync\n{self.developer_id}",
                menu
            )

            # Start sync in background thread
            sync_thread = threading.Thread(target=self.sync_loop, daemon=True)
            sync_thread.start()

            # Run tray icon (blocks)
            self.icon.run()

        except ImportError:
            # No tray support, just run sync loop
            logger.warning("No tray support, running headless")
            self.sync_loop()
        except Exception as e:
            logger.error(f"Error: {e}")
            self.sync_loop()


def main():
    """Main entry with auto-setup"""

    # Check if already running
    if check_already_running():
        logger.info("Another instance is already running. Exiting.")
        sys.exit(0)

    # Ensure dependencies
    try:
        ensure_dependencies()
    except Exception as e:
        logger.error(f"Could not install dependencies: {e}")

    # Install autostart if first run
    marker_file = SCRIPT_DIR / ".installed"
    if not marker_file.exists():
        logger.info("First run - installing autostart...")
        install_autostart()
        marker_file.write_text(datetime.now().isoformat())

    # Run the service
    service = AutoSyncService()
    service.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
