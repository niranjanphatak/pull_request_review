#!/usr/bin/env python3
"""
Migration script to add source_branch and target_branch fields to existing sessions.

This backfills branch information from results.pr_details for sessions that don't have it.
"""

from pymongo import MongoClient
from datetime import datetime
from config import Config

def migrate_sessions():
    """Add source_branch and target_branch fields to sessions that don't have them"""
    try:
        # Connect to MongoDB
        client = MongoClient(Config.get_mongodb_uri(), serverSelectionTimeoutMS=5000)
        db = client[Config.get_mongodb_db_name()]
        sessions_collection = db['sessions']

        # Find sessions without branch fields or with null branch fields
        sessions_to_update = sessions_collection.find({
            '$or': [
                {'source_branch': {'$exists': False}},
                {'source_branch': None},
                {'target_branch': {'$exists': False}},
                {'target_branch': None}
            ]
        })

        count = 0
        updated = 0
        skipped = 0

        for session in sessions_to_update:
            count += 1
            pr_details = session.get('results', {}).get('pr_details', {})

            # Extract branch names using the same logic as server.py
            # GitHub format: head_branch and base_branch
            # GitLab format: source_branch and target_branch
            source_branch = (
                pr_details.get('source_branch') or
                pr_details.get('head_branch') or
                pr_details.get('head', {}).get('ref') if isinstance(pr_details.get('head'), dict) else None
            )

            target_branch = (
                pr_details.get('target_branch') or
                pr_details.get('base_branch') or
                pr_details.get('base', {}).get('ref') if isinstance(pr_details.get('base'), dict) else None
            )

            # Only update if we found at least one branch
            if source_branch or target_branch:
                update_fields = {}
                if source_branch:
                    update_fields['source_branch'] = source_branch
                if target_branch:
                    update_fields['target_branch'] = target_branch

                sessions_collection.update_one(
                    {'_id': session['_id']},
                    {'$set': update_fields}
                )
                updated += 1
                print(f"Updated session {session['_id']}: source='{source_branch or 'N/A'}', target='{target_branch or 'N/A'}'")
            else:
                skipped += 1
                print(f"Skipped session {session['_id']}: No branch info found in pr_details")

        client.close()
        print(f"\n✅ Migration complete!")
        print(f"   Total sessions checked: {count}")
        print(f"   Updated with branch info: {updated}")
        print(f"   Skipped (no branch info available): {skipped}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 80)
    print("Branch Fields Migration")
    print("=" * 80)
    print("This script will add source_branch and target_branch fields to existing sessions")
    print("by extracting them from results.pr_details.\n")

    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate_sessions()
    else:
        print("Migration cancelled.")
