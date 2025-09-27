#!/usr/bin/env python3
"""
Unified Database Monitor - Shows real-time sync status
"""

import os
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import sys

load_dotenv('.env')
DATABASE_URL = os.getenv("DATABASE_URL")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def monitor_sync():
    engine = create_engine(DATABASE_URL)
    
    while True:
        try:
            clear_screen()
            with engine.connect() as conn:
                print("🔴 TIMESHEET SYNC MONITOR")
                print("=" * 60)
                print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                # Active syncs in last 5 minutes
                result = conn.execute(text("""
                    SELECT 
                        developer_id,
                        COUNT(*) as sync_count,
                        MAX(created_at) as last_sync
                    FROM activity_records
                    WHERE created_at > NOW() - INTERVAL '5 minutes'
                    GROUP BY developer_id
                    ORDER BY last_sync DESC
                """)).fetchall()
                
                print("🔄 ACTIVE SYNCS (Last 5 minutes):")
                print("-" * 40)
                if result:
                    for dev_id, count, last_sync in result:
                        age = (datetime.now() - last_sync).total_seconds()
                        status = "🟢" if age < 60 else "🟡" if age < 300 else "🔴"
                        print(f"{status} {dev_id:<20} {count:>4} events   {int(age)}s ago")
                else:
                    print("❌ No active syncs")
                
                # Today's summary
                result = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT developer_id) as active_devs,
                        COUNT(*) as total_events,
                        SUM(duration) / 3600.0 as total_hours
                    FROM activity_records
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)).fetchone()
                
                print(f"\n📊 TODAY'S SUMMARY:")
                print("-" * 40)
                print(f"Active Developers: {result[0]}")
                print(f"Total Events: {result[1]}")
                print(f"Total Hours: {result[2]:.2f}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n[Press Ctrl+C to exit]")
        time.sleep(5)  # Refresh every 5 seconds

if __name__ == "__main__":
    try:
        monitor_sync()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
