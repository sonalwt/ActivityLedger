#!/usr/bin/env python3
"""
One-time AFK data backfill script.

Fetches historical AFK watcher data from local ActivityWatch and sends it
to the timesheet server so that past activity durations can be adjusted
for idle time.

Usage:
    python backfill_afk.py                  # Backfill last 30 days
    python backfill_afk.py --days 90        # Backfill last 90 days
    python backfill_afk.py --dry-run        # Preview without sending
"""

import os
import sys
import argparse
import requests
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env from script directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

SERVER_URL = os.getenv("SERVER_URL", "https://api-timesheet.firsteconomy.com/api/sync")
DEVELOPER_ID = os.getenv("DEVELOPER_ID", "")
API_TOKEN = os.getenv("API_TOKEN", "")
ACTIVITYWATCH_HOST = os.getenv("ACTIVITYWATCH_HOST", "http://localhost:5600")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def fetch_afk_events(start: datetime, end: datetime) -> list:
    """Fetch AFK events from local ActivityWatch for the given date range."""
    aw_api = f"{ACTIVITYWATCH_HOST}/api/0"

    # Find AFK bucket
    buckets = requests.get(f"{aw_api}/buckets/", timeout=10).json()
    afk_buckets = [name for name in buckets if 'afk' in name.lower()]

    if not afk_buckets:
        logger.error("No AFK bucket found in ActivityWatch. Is aw-watcher-afk running?")
        return []

    all_events = []
    for bucket_name in afk_buckets:
        logger.info(f"Fetching from bucket: {bucket_name}")

        # Fetch in daily chunks to avoid hitting limits
        current = start
        while current < end:
            chunk_end = min(current + timedelta(days=1), end)
            params = {
                'start': current.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': chunk_end.strftime('%Y-%m-%dT%H:%M:%S'),
                'limit': 50000
            }

            try:
                resp = requests.get(
                    f"{aw_api}/buckets/{bucket_name}/events",
                    params=params, timeout=30
                )
                resp.raise_for_status()
                events = resp.json()

                for event in events:
                    data = event.get('data', {})
                    status = data.get('status', '')
                    duration = event.get('duration', 0)
                    timestamp = event.get('timestamp', '')

                    if status not in ('afk', 'not-afk') or duration < 1:
                        continue

                    all_events.append({
                        "status": status,
                        "duration": duration,
                        "timestamp": timestamp
                    })

                if events:
                    logger.info(f"  {current.strftime('%Y-%m-%d')}: {len(events)} events")
            except Exception as e:
                logger.error(f"  {current.strftime('%Y-%m-%d')}: Error - {e}")

            current = chunk_end

    return all_events


def send_to_server(afk_events: list, batch_size: int = 2000) -> int:
    """Send AFK events to the server in batches."""
    total_saved = 0

    for i in range(0, len(afk_events), batch_size):
        batch = afk_events[i:i + batch_size]
        payload = {
            "name": DEVELOPER_ID,
            "token": API_TOKEN,
            "data": [],
            "afk_data": batch,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            resp = requests.post(
                SERVER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            result = resp.json()

            if result.get("success"):
                saved = result.get("afk_saved", 0)
                total_saved += saved
                logger.info(f"  Batch {i // batch_size + 1}: sent {len(batch)}, saved {saved}")
            else:
                logger.error(f"  Batch {i // batch_size + 1}: server error - {result.get('error')}")
        except Exception as e:
            logger.error(f"  Batch {i // batch_size + 1}: failed - {e}")

    return total_saved


def main():
    parser = argparse.ArgumentParser(description='Backfill AFK data from ActivityWatch')
    parser.add_argument('--days', type=int, default=30, help='Number of days to backfill (default: 30)')
    parser.add_argument('--dry-run', action='store_true', help='Fetch but do not send to server')
    args = parser.parse_args()

    if not DEVELOPER_ID or not API_TOKEN:
        logger.error("DEVELOPER_ID and API_TOKEN must be set in .env file")
        sys.exit(1)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    logger.info(f"Developer: {DEVELOPER_ID}")
    logger.info(f"Server: {SERVER_URL}")
    logger.info(f"Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({args.days} days)")
    logger.info("")

    # Fetch from local ActivityWatch
    logger.info("Fetching AFK data from local ActivityWatch...")
    afk_events = fetch_afk_events(start, end)
    logger.info(f"Total AFK events collected: {len(afk_events)}")

    if not afk_events:
        logger.info("No AFK events found. Nothing to backfill.")
        return

    # Count not-afk vs afk
    not_afk = sum(1 for e in afk_events if e['status'] == 'not-afk')
    afk = sum(1 for e in afk_events if e['status'] == 'afk')
    logger.info(f"  not-afk (active): {not_afk} events")
    logger.info(f"  afk (idle): {afk} events")

    if args.dry_run:
        logger.info("Dry run - not sending to server.")
        return

    # Send to server
    logger.info("")
    logger.info("Sending to server...")
    total_saved = send_to_server(afk_events)
    logger.info(f"Done! Total AFK events saved: {total_saved}")


if __name__ == "__main__":
    main()
