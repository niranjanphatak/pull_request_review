#!/usr/bin/env python3
"""
Migration script to add status field to existing sessions that don't have it.

This is a one-time migration for sessions created before status tracking was added.
"""

from pymongo import MongoClient
from datetime import datetime
from config import Config

def migrate_sessions():
    """Add status field to sessions that don't have it"""
    try:
        # Connect to MongoDB
        client = MongoClient(Config.get_mongodb_uri(), serverSelectionTimeoutMS=5000)
        db = client[Config.get_mongodb_db_name()]
        sessions_collection = db['sessions']

        # Find sessions without status field
        sessions_without_status = sessions_collection.find({
            'status': {'$exists': False}
        })

        count = 0
        for session in sessions_without_status:
            # Set default status to 'Review completed successfully'
            # This is a reasonable default for old sessions that completed
            default_status = 'Review completed successfully'

            sessions_collection.update_one(
                {'_id': session['_id']},
                {'$set': {'status': default_status}}
            )
            count += 1
            print(f"Updated session {session['_id']}: status='{default_status}'")

        client.close()
        print(f"\n✅ Migration complete! Updated {count} sessions with status field.")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 80)
    print("Status Field Migration")
    print("=" * 80)
    print("This script will add a 'status' field to existing sessions that don't have it.")
    print("Default value: 'Review completed successfully'\n")

    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate_sessions()
    else:
        print("Migration cancelled.")
