"""
MongoDB Session Storage for PR Reviews
"""
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, List, Optional
import os


class SessionStorage:
    """Store and retrieve PR review sessions in MongoDB"""

    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/"):
        """
        Initialize MongoDB connection

        Args:
            mongodb_uri: MongoDB connection URI (default: local)
        """
        try:
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client['pr_review']
            self.sessions = self.db['sessions']
            self.connected = True
            print("✅ MongoDB connected successfully")
        except Exception as e:
            print(f"⚠️  MongoDB not available: {e}")
            print("   Session storage disabled. Reviews will not be saved.")
            self.connected = False

    def save_session(self, session_data: Dict) -> Optional[str]:
        """
        Save a review session to MongoDB

        Args:
            session_data: Dictionary containing review results

        Returns:
            Session ID (str) or None if storage failed
        """
        if not self.connected:
            return None

        try:
            # Add timestamp
            session_data['timestamp'] = datetime.utcnow()
            session_data['created_at'] = datetime.utcnow().isoformat()

            # Insert into MongoDB
            result = self.sessions.insert_one(session_data)
            session_id = str(result.inserted_id)

            print(f"✅ Session saved: {session_id}")
            return session_id

        except Exception as e:
            print(f"❌ Failed to save session: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a specific session by ID

        Args:
            session_id: MongoDB ObjectId as string

        Returns:
            Session data dictionary or None
        """
        if not self.connected:
            return None

        try:
            from bson.objectid import ObjectId
            session = self.sessions.find_one({'_id': ObjectId(session_id)})

            if session:
                session['_id'] = str(session['_id'])
                return session
            return None

        except Exception as e:
            print(f"❌ Failed to retrieve session: {e}")
            return None

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent review sessions

        Args:
            limit: Number of sessions to retrieve

        Returns:
            List of session dictionaries
        """
        if not self.connected:
            return []

        try:
            sessions = list(
                self.sessions
                .find()
                .sort('timestamp', -1)
                .limit(limit)
            )

            # Convert ObjectId to string
            for session in sessions:
                session['_id'] = str(session['_id'])

            return sessions

        except Exception as e:
            print(f"❌ Failed to retrieve sessions: {e}")
            return []

    def search_sessions(self, pr_url: Optional[str] = None,
                       repo_url: Optional[str] = None,
                       limit: int = 10) -> List[Dict]:
        """
        Search for sessions by PR or repo URL

        Args:
            pr_url: Pull request URL to search for
            repo_url: Repository URL to search for
            limit: Maximum number of results

        Returns:
            List of matching session dictionaries
        """
        if not self.connected:
            return []

        try:
            query = {}
            if pr_url:
                query['pr_url'] = pr_url
            if repo_url:
                query['repo_url'] = repo_url

            sessions = list(
                self.sessions
                .find(query)
                .sort('timestamp', -1)
                .limit(limit)
            )

            # Convert ObjectId to string
            for session in sessions:
                session['_id'] = str(session['_id'])

            return sessions

        except Exception as e:
            print(f"❌ Failed to search sessions: {e}")
            return []

    def get_statistics(self) -> Dict:
        """
        Get statistics about stored sessions

        Returns:
            Dictionary with statistics
        """
        if not self.connected:
            return {
                'total_sessions': 0,
                'connected': False
            }

        try:
            total = self.sessions.count_documents({})

            # Get most reviewed repos
            pipeline = [
                {'$group': {
                    '_id': '$repo_url',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 5}
            ]
            top_repos = list(self.sessions.aggregate(pipeline))

            return {
                'total_sessions': total,
                'connected': True,
                'top_repos': top_repos
            }

        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {
                'total_sessions': 0,
                'connected': False,
                'error': str(e)
            }

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by ID

        Args:
            session_id: MongoDB ObjectId as string

        Returns:
            True if deleted, False otherwise
        """
        if not self.connected:
            return False

        try:
            from bson.objectid import ObjectId
            result = self.sessions.delete_one({'_id': ObjectId(session_id)})
            return result.deleted_count > 0

        except Exception as e:
            print(f"❌ Failed to delete session: {e}")
            return False

    def close(self):
        """Close MongoDB connection"""
        if self.connected:
            self.client.close()
            print("MongoDB connection closed")
