#!/usr/bin/env python3
"""
Daily Statistics Snapshot Script

This script should be run daily (via cron or task scheduler) to create
historical snapshots of statistics for trend analysis.

Usage:
  python create_daily_snapshot.py

Cron setup (daily at midnight):
  0 0 * * * cd /path/to/pull_request_review && python create_daily_snapshot.py >> logs/snapshots.log 2>&1

Cron setup (weekly on Sunday at midnight):
  0 0 * * 0 cd /path/to/pull_request_review && python create_daily_snapshot.py --weekly >> logs/snapshots.log 2>&1
"""

import sys
import argparse
from datetime import datetime
from utils.session_storage import SessionStorage


def create_snapshot(snapshot_type='daily'):
    """Create a statistics snapshot"""
    print(f"\n{'='*80}")
    print(f"Creating {snapshot_type} statistics snapshot...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"{'='*80}\n")

    # Initialize MongoDB connection
    storage = SessionStorage()

    if not storage.connected:
        print("❌ ERROR: Cannot connect to MongoDB")
        print("   Make sure MongoDB is running on localhost:27017")
        sys.exit(1)

    # Create snapshot
    snapshot_id = storage.save_statistics_snapshot(snapshot_type)

    if snapshot_id:
        print(f"\n✅ SUCCESS: Snapshot created successfully")
        print(f"   Snapshot ID: {snapshot_id}")
        print(f"   Type: {snapshot_type}")

        # Display snapshot details
        snapshot = storage.get_latest_snapshot(snapshot_type)
        if snapshot:
            print(f"\n📊 Snapshot Statistics:")
            print(f"   Total Sessions: {snapshot.get('total_sessions', 0)}")
            print(f"   Average DDD Score: {snapshot.get('average_ddd_score', 0):.2f}%")
            print(f"   Average Test Count: {snapshot.get('average_test_count', 0):.2f}")
            print(f"   Average Files: {snapshot.get('average_files', 0):.2f}")
            print(f"   Top Repositories: {len(snapshot.get('top_repos', []))}")
    else:
        print("\n❌ ERROR: Failed to create snapshot")
        sys.exit(1)

    # Close connection
    storage.close()

    print(f"\n{'='*80}")
    print("Snapshot creation completed")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Create statistics snapshot for historical tracking')
    parser.add_argument('--weekly', action='store_true', help='Create weekly snapshot instead of daily')
    parser.add_argument('--monthly', action='store_true', help='Create monthly snapshot instead of daily')

    args = parser.parse_args()

    # Determine snapshot type
    if args.weekly:
        snapshot_type = 'weekly'
    elif args.monthly:
        snapshot_type = 'monthly'
    else:
        snapshot_type = 'daily'

    create_snapshot(snapshot_type)


if __name__ == '__main__':
    main()
