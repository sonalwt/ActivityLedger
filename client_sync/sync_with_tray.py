#!/usr/bin/env python3
"""
ActivityWatch Sync Client with System Tray Icon
Provides visual feedback that the sync is running
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add script directory to path
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

# Setup logging first
log_file = SCRIPT_DIR / "sync_service.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import system tray libraries
TRAY_AVAILABLE = False
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    logger.warning("pystray/pillow not installed. Running without system tray icon.")
    logger.warning("Install with: pip install pystray pillow")

# Import the main sync functionality
try:
    from activitywatch_sync import ActivityWatchSyncer, SYNC_INTERVAL_MINUTES
except ImportError as e:
    logger.error(f"Could not import activitywatch_sync: {e}")
    sys.exit(1)


class SyncServiceWithTray:
    def __init__(self):
        self.syncer = None
        self.icon = None
        self.running = True
        self.last_sync_time = None
        self.last_sync_status = "Starting..."
        self.sync_count = 0
        self.error_count = 0

    def create_icon_image(self, color="green"):
        """Create a simple colored circle icon"""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        colors = {
            "green": (0, 200, 0, 255),      # Syncing OK
            "yellow": (255, 200, 0, 255),   # Syncing in progress
            "red": (200, 0, 0, 255),        # Error
            "gray": (128, 128, 128, 255)    # Stopped
        }
        fill_color = colors.get(color, colors["gray"])

        # Draw filled circle
        draw.ellipse([4, 4, size-4, size-4], fill=fill_color, outline=(255, 255, 255, 255))

        # Draw "AW" text
        try:
            draw.text((size//2 - 12, size//2 - 8), "AW", fill=(255, 255, 255, 255))
        except:
            pass

        return image

    def get_status_text(self):
        """Get current status for tooltip"""
        lines = [
            "ActivityWatch Sync",
            f"Status: {self.last_sync_status}",
            f"Syncs: {self.sync_count} | Errors: {self.error_count}"
        ]
        if self.last_sync_time:
            lines.append(f"Last sync: {self.last_sync_time.strftime('%H:%M:%S')}")
        return "\n".join(lines)

    def update_icon(self, color="green"):
        """Update the tray icon color"""
        if self.icon and TRAY_AVAILABLE:
            try:
                self.icon.icon = self.create_icon_image(color)
                self.icon.title = self.get_status_text()
            except Exception as e:
                logger.debug(f"Could not update icon: {e}")

    def show_notification(self, title, message):
        """Show a Windows notification"""
        if self.icon and TRAY_AVAILABLE:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.debug(f"Could not show notification: {e}")

    def do_sync(self):
        """Perform a single sync operation"""
        try:
            self.update_icon("yellow")
            self.last_sync_status = "Syncing..."

            # Calculate time window (sync interval + buffer)
            hours_back = (SYNC_INTERVAL_MINUTES / 60) + 0.5
            success = self.syncer.sync_recent_data(hours_back=hours_back)

            self.last_sync_time = datetime.now()

            if success:
                self.sync_count += 1
                self.last_sync_status = "OK"
                self.update_icon("green")
                logger.info(f"Sync #{self.sync_count} completed successfully")
            else:
                self.error_count += 1
                self.last_sync_status = "Error"
                self.update_icon("red")
                logger.error(f"Sync failed (error #{self.error_count})")

        except Exception as e:
            self.error_count += 1
            self.last_sync_status = f"Error: {str(e)[:30]}"
            self.update_icon("red")
            logger.error(f"Sync exception: {e}")

    def sync_loop(self):
        """Main sync loop running in background thread"""
        logger.info("Starting sync loop...")

        # Initial sync
        logger.info("Performing initial sync (last 24 hours)...")
        try:
            self.syncer.sync_recent_data(hours_back=24)
            self.sync_count += 1
            self.last_sync_time = datetime.now()
            self.last_sync_status = "OK"
            self.update_icon("green")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
            self.error_count += 1

        # Regular sync loop
        while self.running:
            try:
                # Wait for next sync interval
                for _ in range(SYNC_INTERVAL_MINUTES * 60):
                    if not self.running:
                        break
                    time.sleep(1)

                if self.running:
                    self.do_sync()

            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

        logger.info("Sync loop stopped")

    def on_sync_now(self, icon, item):
        """Menu action: Sync now"""
        logger.info("Manual sync triggered")
        threading.Thread(target=self.do_sync, daemon=True).start()

    def on_open_log(self, icon, item):
        """Menu action: Open log file"""
        try:
            os.startfile(str(log_file))
        except Exception as e:
            logger.error(f"Could not open log file: {e}")

    def on_quit(self, icon, item):
        """Menu action: Quit"""
        logger.info("Quit requested by user")
        self.running = False
        if icon:
            icon.stop()

    def run(self):
        """Main entry point"""
        logger.info("=" * 50)
        logger.info("ActivityWatch Sync Service Starting")
        logger.info("=" * 50)

        # Initialize syncer
        try:
            self.syncer = ActivityWatchSyncer()
        except SystemExit:
            logger.error("Failed to initialize syncer. Check your .env configuration.")
            input("Press Enter to exit...")
            return
        except Exception as e:
            logger.error(f"Failed to initialize syncer: {e}")
            input("Press Enter to exit...")
            return

        # Test connections
        logger.info("Testing connections...")
        if not self.syncer.test_connections():
            logger.warning("Some connection tests failed. Will retry during sync.")

        if TRAY_AVAILABLE:
            # Create system tray icon with menu
            menu = pystray.Menu(
                item('Sync Now', self.on_sync_now),
                item('Open Log', self.on_open_log),
                pystray.Menu.SEPARATOR,
                item('Quit', self.on_quit)
            )

            self.icon = pystray.Icon(
                "ActivityWatch Sync",
                self.create_icon_image("green"),
                "ActivityWatch Sync - Starting...",
                menu
            )

            # Start sync loop in background thread
            sync_thread = threading.Thread(target=self.sync_loop, daemon=True)
            sync_thread.start()

            # Show startup notification
            logger.info("System tray icon created. Look for it near your clock.")

            # Run the icon (blocks until quit)
            try:
                self.icon.run()
            except Exception as e:
                logger.error(f"Tray icon error: {e}")
                self.running = False
        else:
            # No tray available, just run the sync loop
            logger.info("Running without system tray (install pystray for tray icon)")
            self.sync_loop()

        logger.info("Service stopped")


def main():
    """Entry point with error handling"""
    try:
        service = SyncServiceWithTray()
        service.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
