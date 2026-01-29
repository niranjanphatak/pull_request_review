"""
MongoDB Session Storage for PR Reviews
"""
from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from config import Config
from utils.database_interface import DatabaseInterface


class SessionStorage(DatabaseInterface):
    """Store and retrieve PR review sessions in MongoDB"""

    def __init__(self, mongodb_uri: str = None, **kwargs):
        """
        Initialize MongoDB connection

        Args:
            mongodb_uri: MongoDB connection URI (default: from Config)
            **kwargs: Additional configuration (for interface compatibility)
        """
        # Use Config if no URI provided
        if mongodb_uri is None:
            mongodb_uri = Config.get_mongodb_uri()

        db_name = Config.get_mongodb_db_name()

        try:
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.sessions = self.db['sessions']
            self.snapshots = self.db['statistics_snapshots']
            self.prompt_versions = self.db['prompt_versions']
            self.prompt_candidates = self.db['prompt_candidates']
            self.onboarding = self.db['onboarding']
            self.code_analysis_reports = self.db['code_analysis_reports']
            self.repo_analyses = self.db['repo_analyses']
            self._connected = True
            print("✅ MongoDB connected successfully")
        except Exception as e:
            print(f"⚠️  MongoDB not available: {e}")
            print("   Session storage disabled. Reviews will not be saved.")
            self._connected = False

    @property
    def connected(self) -> bool:
        """Check if database is connected"""
        return self._connected

    def save_session(self, session_data: Dict) -> Optional[str]:
        """
        Save a review session to MongoDB

        Args:
            session_data: Dictionary containing review results

        Returns:
            Session ID (str) or None if storage failed
        """
        if not self._connected:
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
        if not self._connected:
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
        if not self._connected:
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
        if not self._connected:
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
            Dictionary with statistics including token usage
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

            # Calculate average DDD score
            avg_ddd_pipeline = [
                {'$match': {'ddd_score': {'$exists': True, '$ne': None}}},
                {'$group': {
                    '_id': None,
                    'average_ddd_score': {'$avg': '$ddd_score'}
                }}
            ]
            avg_ddd_result = list(self.sessions.aggregate(avg_ddd_pipeline))
            average_ddd_score = avg_ddd_result[0]['average_ddd_score'] if avg_ddd_result else 0

            # Calculate total token usage across all stages
            token_usage_pipeline = [
                {'$match': {'token_usage': {'$exists': True}}},
                {'$project': {
                    'total_tokens': {
                        '$add': [
                            {'$ifNull': ['$token_usage.architecture.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.security.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.bugs.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.style.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.performance.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.tests.total_tokens', 0]}
                        ]
                    }
                }},
                {'$group': {
                    '_id': None,
                    'total_tokens_used': {'$sum': '$total_tokens'},
                    'avg_tokens_per_review': {'$avg': '$total_tokens'}
                }}
            ]
            token_result = list(self.sessions.aggregate(token_usage_pipeline))
            token_stats = token_result[0] if token_result else {'total_tokens_used': 0, 'avg_tokens_per_review': 0}

            return {
                'total_sessions': total,
                'connected': True,
                'top_repos': top_repos,
                'average_ddd_score': average_ddd_score,
                'total_tokens_used': int(token_stats.get('total_tokens_used', 0)),
                'avg_tokens_per_review': int(token_stats.get('avg_tokens_per_review', 0))
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
        if not self._connected:
            return False

        try:
            from bson.objectid import ObjectId
            result = self.sessions.delete_one({'_id': ObjectId(session_id)})
            return result.deleted_count > 0

        except Exception as e:
            print(f"❌ Failed to delete session: {e}")
            return False

    def get_all_repositories(self) -> List[str]:
        """
        Get all unique repository URLs from sessions

        Returns:
            List of unique repository URLs
        """
        if not self._connected:
            return []

        try:
            repos = self.sessions.distinct('repo_url')
            # Filter out None/empty values and sort
            repos = [r for r in repos if r]
            repos.sort()
            return repos

        except Exception as e:
            print(f"❌ Failed to get repositories: {e}")
            return []

    def get_sessions_by_repositories(self, repo_urls: List[str]) -> List[Dict]:
        """
        Get sessions for specific repositories

        Args:
            repo_urls: List of repository URLs to filter by

        Returns:
            List of matching session dictionaries
        """
        if not self._connected:
            return []

        try:
            query = {'repo_url': {'$in': repo_urls}}
            sessions = list(
                self.sessions
                .find(query)
                .sort('timestamp', -1)
            )

            # Convert ObjectId to string
            for session in sessions:
                session['_id'] = str(session['_id'])

            return sessions

        except Exception as e:
            print(f"❌ Failed to get sessions by repositories: {e}")
            return []

    def get_filtered_statistics(self, repo_urls: List[str]) -> Dict:
        """
        Get statistics for specific repositories

        Args:
            repo_urls: List of repository URLs to filter by (empty list = all repos)

        Returns:
            Dictionary with filtered statistics
        """
        if not self.connected:
            return {
                'total_sessions': 0,
                'connected': False
            }

        try:
            # Build query
            query = {}
            if repo_urls:
                query['repo_url'] = {'$in': repo_urls}

            total = self.sessions.count_documents(query)

            # Get top repos within filter
            pipeline = [
                {'$match': query},
                {'$group': {
                    '_id': '$repo_url',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 5}
            ]
            top_repos = list(self.sessions.aggregate(pipeline))

            # Calculate average DDD score
            avg_ddd_pipeline = [
                {'$match': {**query, 'ddd_score': {'$exists': True, '$ne': None}}},
                {'$group': {
                    '_id': None,
                    'average_ddd_score': {'$avg': '$ddd_score'}
                }}
            ]
            avg_ddd_result = list(self.sessions.aggregate(avg_ddd_pipeline))
            average_ddd_score = avg_ddd_result[0]['average_ddd_score'] if avg_ddd_result else 0

            # Count recent reviews (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_query = {**query, 'timestamp': {'$gte': yesterday}}
            recent_count = self.sessions.count_documents(recent_query)

            return {
                'total_sessions': total,
                'recent_sessions': recent_count,
                'connected': True,
                'top_repos': top_repos,
                'average_ddd_score': average_ddd_score,
                'filtered': bool(repo_urls),
                'filter_count': len(repo_urls) if repo_urls else 0
            }

        except Exception as e:
            print(f"❌ Failed to get filtered statistics: {e}")
            return {
                'total_sessions': 0,
                'connected': False,
                'error': str(e)
            }

    def save_statistics_snapshot(self, snapshot_type: str = 'daily') -> Optional[str]:
        """
        Save a snapshot of current statistics for historical tracking

        Args:
            snapshot_type: Type of snapshot ('daily', 'weekly', 'monthly')

        Returns:
            Snapshot ID (str) or None if save failed
        """
        if not self._connected:
            return None

        try:
            # Get current statistics
            stats = self.get_statistics()

            if not stats.get('connected'):
                print("Cannot create snapshot: database not connected")
                return None

            # Create snapshot document
            snapshot = {
                'snapshot_type': snapshot_type,
                'timestamp': datetime.utcnow(),
                'created_at': datetime.utcnow().isoformat(),
                'total_sessions': stats.get('total_sessions', 0),
                'average_ddd_score': stats.get('average_ddd_score', 0),
                'top_repos': stats.get('top_repos', [])
            }

            # Calculate additional metrics
            # Average test count
            avg_test_pipeline = [
                {'$match': {'test_count': {'$exists': True, '$ne': None}}},
                {'$group': {
                    '_id': None,
                    'average_test_count': {'$avg': '$test_count'}
                }}
            ]
            avg_test_result = list(self.sessions.aggregate(avg_test_pipeline))
            snapshot['average_test_count'] = avg_test_result[0]['average_test_count'] if avg_test_result else 0

            # Average files per review
            avg_files_pipeline = [
                {'$match': {'files_count': {'$exists': True, '$ne': None}}},
                {'$group': {
                    '_id': None,
                    'average_files': {'$avg': '$files_count'}
                }}
            ]
            avg_files_result = list(self.sessions.aggregate(avg_files_pipeline))
            snapshot['average_files'] = avg_files_result[0]['average_files'] if avg_files_result else 0

            # Insert snapshot
            result = self.snapshots.insert_one(snapshot)
            snapshot_id = str(result.inserted_id)

            print(f"✅ Statistics snapshot saved: {snapshot_id} (type: {snapshot_type})")
            return snapshot_id

        except Exception as e:
            print(f"❌ Failed to save statistics snapshot: {e}")
            return None

    def get_latest_snapshot(self, snapshot_type: str = 'daily') -> Optional[Dict]:
        """
        Get the most recent statistics snapshot

        Args:
            snapshot_type: Type of snapshot to retrieve

        Returns:
            Snapshot dictionary or None
        """
        if not self._connected:
            return None

        try:
            snapshot = self.snapshots.find_one(
                {'snapshot_type': snapshot_type},
                sort=[('timestamp', -1)]
            )

            if snapshot:
                snapshot['_id'] = str(snapshot['_id'])
                return snapshot

            return None

        except Exception as e:
            print(f"❌ Failed to get latest snapshot: {e}")
            return None

    def get_snapshot_by_date_range(self, start_date: datetime, end_date: datetime,
                                   snapshot_type: str = 'daily') -> List[Dict]:
        """
        Get snapshots within a date range

        Args:
            start_date: Start date (datetime)
            end_date: End date (datetime)
            snapshot_type: Type of snapshots to retrieve

        Returns:
            List of snapshot dictionaries
        """
        if not self._connected:
            return []

        try:
            snapshots = list(
                self.snapshots
                .find({
                    'snapshot_type': snapshot_type,
                    'timestamp': {
                        '$gte': start_date,
                        '$lte': end_date
                    }
                })
                .sort('timestamp', 1)
            )

            # Convert ObjectId to string
            for snapshot in snapshots:
                snapshot['_id'] = str(snapshot['_id'])

            return snapshots

        except Exception as e:
            print(f"❌ Failed to get snapshots by date range: {e}")
            return []

    def calculate_trend(self, metric_name: str, days_back: int = 7) -> Dict:
        """
        Calculate trend for a specific metric

        Args:
            metric_name: Name of metric to track (e.g., 'total_sessions', 'average_ddd_score')
            days_back: Number of days to look back (7 for week, 30 for month)

        Returns:
            Dictionary with current value, previous value, change, and percentage change
        """
        if not self.connected:
            return {
                'current': 0,
                'previous': 0,
                'change': 0,
                'percentage_change': 0,
                'trend': 'neutral'
            }

        try:
            # Get current statistics
            current_stats = self.get_statistics()
            current_value = current_stats.get(metric_name, 0)

            # Get snapshot from N days ago
            target_date = datetime.utcnow() - timedelta(days=days_back)

            # Find closest snapshot to target date
            snapshot = self.snapshots.find_one(
                {'timestamp': {'$lte': target_date}},
                sort=[('timestamp', -1)]
            )

            if snapshot:
                previous_value = snapshot.get(metric_name, 0)
            else:
                # No historical data, return neutral trend
                return {
                    'current': current_value,
                    'previous': 0,
                    'change': 0,
                    'percentage_change': 0,
                    'trend': 'neutral',
                    'message': 'No historical data available'
                }

            # Calculate change
            change = current_value - previous_value
            percentage_change = ((change / previous_value) * 100) if previous_value > 0 else 0

            # Determine trend direction
            if change > 0:
                trend = 'up'
            elif change < 0:
                trend = 'down'
            else:
                trend = 'neutral'

            return {
                'current': current_value,
                'previous': previous_value,
                'change': change,
                'percentage_change': percentage_change,
                'trend': trend,
                'days_back': days_back
            }

        except Exception as e:
            print(f"❌ Failed to calculate trend: {e}")
            return {
                'current': 0,
                'previous': 0,
                'change': 0,
                'percentage_change': 0,
                'trend': 'neutral',
                'error': str(e)
            }

    # ============================================================================
    # PROMPT VERSIONING METHODS
    # ============================================================================

    def save_prompt_version(self, stage: str, version: str, prompt_content: str,
                           description: str, criteria: List[str]) -> Optional[str]:
        """
        Save a new prompt version to MongoDB

        Args:
            stage: Review stage ('security', 'bugs', 'style', 'tests')
            version: Version string (e.g., '1.0.0', '1.1.0')
            prompt_content: The full prompt text
            description: Description of how this prompt evaluates code
            criteria: List of evaluation criteria

        Returns:
            Prompt version ID or None
        """
        if not self._connected:
            return None

        try:
            prompt_data = {
                'stage': stage,
                'version': version,
                'prompt_content': prompt_content,
                'description': description,
                'criteria': criteria,
                'created_at': datetime.utcnow().isoformat(),
                'timestamp': datetime.utcnow(),
                'active': True
            }

            result = self.prompt_versions.insert_one(prompt_data)
            prompt_id = str(result.inserted_id)

            print(f"✅ Prompt version saved: {stage} v{version} ({prompt_id})")
            return prompt_id

        except Exception as e:
            print(f"❌ Failed to save prompt version: {e}")
            return None

    def get_prompt_version(self, stage: str, version: Optional[str] = None) -> Optional[Dict]:
        """
        Get a specific prompt version or the latest active one

        Args:
            stage: Review stage ('security', 'bugs', 'style', 'tests')
            version: Specific version or None for latest

        Returns:
            Prompt version dictionary or None
        """
        if not self._connected:
            return None

        try:
            query = {'stage': stage, 'active': True}
            if version:
                query['version'] = version

            # Get the latest version if no specific version requested
            prompt = self.prompt_versions.find_one(
                query,
                sort=[('timestamp', -1)]
            )

            if prompt:
                prompt['_id'] = str(prompt['_id'])
                return prompt
            return None

        except Exception as e:
            print(f"❌ Failed to retrieve prompt version: {e}")
            return None

    def get_all_prompt_versions(self, stage: Optional[str] = None) -> List[Dict]:
        """
        Get all prompt versions, optionally filtered by stage

        Args:
            stage: Optional stage filter

        Returns:
            List of prompt version dictionaries
        """
        if not self._connected:
            return []

        try:
            query = {}
            if stage:
                query['stage'] = stage

            prompts = list(self.prompt_versions.find(
                query,
                sort=[('timestamp', -1)]
            ))

            for prompt in prompts:
                prompt['_id'] = str(prompt['_id'])

            return prompts

        except Exception as e:
            print(f"❌ Failed to retrieve prompt versions: {e}")
            return []

    def deactivate_prompt_version(self, stage: str, version: str) -> bool:
        """
        Deactivate a specific prompt version

        Args:
            stage: Review stage
            version: Version string

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            result = self.prompt_versions.update_one(
                {'stage': stage, 'version': version},
                {'$set': {'active': False}}
            )
            return result.modified_count > 0

        except Exception as e:
            print(f"❌ Failed to deactivate prompt version: {e}")
            return False

    def get_sessions_with_token_stats(self, limit: int = 50) -> List[Dict]:
        """
        Get recent sessions with token usage statistics for the statistics table

        Args:
            limit: Number of sessions to retrieve

        Returns:
            List of session dictionaries with calculated token totals
        """
        if not self._connected:
            return []

        try:
            pipeline = [
                {'$sort': {'timestamp': -1}},
                {'$limit': limit},
                {'$project': {
                    '_id': {'$toString': '$_id'},
                    'pr_url': 1,
                    'pr_title': 1,
                    'repo_url': 1,
                    'timestamp': 1,
                    'created_at': 1,
                    'status': 1,
                    'ddd_score': 1,
                    'source_branch': 1,
                    'target_branch': 1,
                    'token_usage': 1,
                    # Calculate total tokens across all stages
                    'total_tokens': {
                        '$add': [
                            {'$ifNull': ['$token_usage.architecture.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.security.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.bugs.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.style.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.performance.total_tokens', 0]},
                            {'$ifNull': ['$token_usage.tests.total_tokens', 0]}
                        ]
                    }
                }}
            ]

            sessions = list(self.sessions.aggregate(pipeline))
            return sessions

        except Exception as e:
            print(f"❌ Failed to retrieve sessions with token stats: {e}")
            return []

    def close(self):
        """Close MongoDB connection"""
        if self.connected:
            self.client.close()
            print("MongoDB connection closed")

    # ============================================
    # Onboarding Methods
    # ============================================

    def save_onboarding(self, onboarding_data: Dict) -> Optional[str]:
        """
        Save onboarding information (team and repositories)

        Args:
            onboarding_data: Dictionary containing:
                - team_name: Name of the team
                - repositories: List of repository objects with url and description

        Returns:
            Onboarding ID (str) or None if save failed
        """
        if not self._connected:
            return None

        try:
            onboarding_data['created_at'] = datetime.now().isoformat()
            onboarding_data['updated_at'] = datetime.now().isoformat()
            onboarding_data['timestamp'] = datetime.now()

            result = self.onboarding.insert_one(onboarding_data)
            onboarding_id = str(result.inserted_id)
            print(f"✅ Onboarding saved: {onboarding_id}")
            return onboarding_id

        except Exception as e:
            print(f"❌ Failed to save onboarding: {e}")
            return None

    def get_onboarding(self, onboarding_id: str = None) -> Optional[Dict]:
        """
        Get onboarding data by ID or get the latest

        Args:
            onboarding_id: Optional onboarding ID to retrieve specific entry

        Returns:
            Onboarding data dictionary or None
        """
        if not self._connected:
            return None

        try:
            if onboarding_id:
                from bson import ObjectId
                result = self.onboarding.find_one({'_id': ObjectId(onboarding_id)})
            else:
                # Get most recent onboarding
                result = self.onboarding.find_one(sort=[('timestamp', -1)])

            if result:
                result['_id'] = str(result['_id'])
                return result
            return None

        except Exception as e:
            print(f"❌ Failed to get onboarding: {e}")
            return None

    def get_all_onboardings(self, limit: int = 50) -> List[Dict]:
        """
        Get all onboarding entries

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of onboarding data dictionaries
        """
        if not self._connected:
            return []

        try:
            results = list(self.onboarding.find().sort('timestamp', -1).limit(limit))
            for result in results:
                result['_id'] = str(result['_id'])
            return results

        except Exception as e:
            print(f"❌ Failed to get all onboardings: {e}")
            return []

    def update_onboarding(self, onboarding_id: str, updates: Dict) -> bool:
        """
        Update existing onboarding data

        Args:
            onboarding_id: ID of onboarding to update
            updates: Dictionary with fields to update

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            from bson import ObjectId
            updates['updated_at'] = datetime.now().isoformat()

            result = self.onboarding.update_one(
                {'_id': ObjectId(onboarding_id)},
                {'$set': updates}
            )

            if result.modified_count > 0:
                print(f"✅ Onboarding updated: {onboarding_id}")
                return True
            return False

        except Exception as e:
            print(f"❌ Failed to update onboarding: {e}")
            return False

    def delete_onboarding(self, onboarding_id: str) -> bool:
        """
        Delete onboarding data

        Args:
            onboarding_id: ID of onboarding to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            from bson import ObjectId
            result = self.onboarding.delete_one({'_id': ObjectId(onboarding_id)})

            if result.deleted_count > 0:
                print(f"✅ Onboarding deleted: {onboarding_id}")
                return True
            return False

        except Exception as e:
            print(f"❌ Failed to delete onboarding: {e}")
            return False

    # ============================================================================
    # PROMPT CANDIDATE METHODS
    # ============================================================================

    def save_prompt_candidate(self, candidate_data: Dict) -> Optional[str]:
        """
        Save a generated prompt candidate to MongoDB

        Args:
            candidate_data: Dictionary containing candidate details

        Returns:
            Candidate ID or None
        """
        if not self._connected:
            return None

        try:
            candidate_data['created_at'] = datetime.utcnow().isoformat()
            candidate_data['timestamp'] = datetime.utcnow()
            candidate_data['accepted'] = False

            result = self.prompt_candidates.insert_one(candidate_data)
            candidate_id = str(result.inserted_id)

            print(f"✅ Prompt candidate saved: {candidate_id}")
            return candidate_id

        except Exception as e:
            print(f"❌ Failed to save prompt candidate: {e}")
            return None

    def get_prompt_candidates(self, accepted: bool = False, limit: int = 50) -> List[Dict]:
        """
        Get prompt candidates, optionally filtering by acceptance status

        Args:
            accepted: Filter by acceptance status
            limit: Maximum number of entries to return

        Returns:
            List of candidate dictionaries
        """
        if not self._connected:
            return []

        try:
            candidates = list(
                self.prompt_candidates
                .find({'accepted': accepted})
                .sort('timestamp', -1)
                .limit(limit)
            )

            for candidate in candidates:
                candidate['_id'] = str(candidate['_id'])

            return candidates

        except Exception as e:
            print(f"❌ Failed to get prompt candidates: {e}")
            return []

    def get_prompt_candidate(self, candidate_id: str) -> Optional[Dict]:
        """
        Get a specific prompt candidate by ID

        Args:
            candidate_id: MongoDB ObjectId as string

        Returns:
            Candidate dictionary or None
        """
        if not self._connected:
            return None

        try:
            from bson.objectid import ObjectId
            candidate = self.prompt_candidates.find_one({'_id': ObjectId(candidate_id)})

            if candidate:
                candidate['_id'] = str(candidate['_id'])
                return candidate
            return None

        except Exception as e:
            print(f"❌ Failed to get prompt candidate: {e}")
            return None

    def accept_prompt_candidate(self, candidate_id: str) -> bool:
        """
        Mark a prompt candidate as accepted

        Args:
            candidate_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            from bson.objectid import ObjectId
            result = self.prompt_candidates.update_one(
                {'_id': ObjectId(candidate_id)},
                {'$set': {
                    'accepted': True,
                    'accepted_at': datetime.utcnow().isoformat()
                }}
            )
            return result.modified_count > 0

        except Exception as e:
            print(f"❌ Failed to accept prompt candidate: {e}")
            return False

    def delete_prompt_candidate(self, candidate_id: str) -> bool:
        """
        Delete a prompt candidate

        Args:
            candidate_id: MongoDB ObjectId as string

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            from bson.objectid import ObjectId
            result = self.prompt_candidates.delete_one({'_id': ObjectId(candidate_id)})
            
            if result.deleted_count > 0:
                print(f"✅ Prompt candidate deleted: {candidate_id}")
                return True
            return False

        except Exception as e:
            print(f"❌ Failed to delete prompt candidate: {e}")
            return False

    def save_repo_analysis(self, analysis_data: Dict) -> Optional[str]:
        """Save a repository analysis report"""
        if not self._connected:
            return None

        try:
            # Add timestamp if not present
            if 'timestamp' not in analysis_data:
                analysis_data['timestamp'] = datetime.utcnow().isoformat()
            
            result = self.repo_analyses.insert_one(analysis_data)
            return str(result.inserted_id)

        except Exception as e:
            print(f"❌ Failed to save repo analysis: {e}")
            return None

    def get_repo_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Retrieve a repository analysis by ID"""
        if not self._connected:
            return None

        try:
            from bson.objectid import ObjectId
            analysis = self.repo_analyses.find_one({'_id': ObjectId(analysis_id)})

            if analysis:
                analysis['_id'] = str(analysis['_id'])
                return analysis
            return None

        except Exception as e:
            print(f"❌ Failed to get repo analysis: {e}")
            return None

    def get_recent_repo_analyses(self, limit: int = 10) -> List[Dict]:
        """Get recent repository analyses"""
        if not self._connected:
            return []

        try:
            cursor = self.repo_analyses.find().sort('timestamp', -1).limit(limit)
            analyses = list(cursor)

            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])

            return analyses

        except Exception as e:
            print(f"❌ Failed to get recent repo analyses: {e}")
            return []

    def get_repo_analysis_history(self, repo_url: str, branch: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get analysis history for a specific repository with optional branch filtering"""
        if not self._connected:
            return []

        try:
            # Build query
            query = {'repo_url': repo_url}
            if branch:
                query['branch'] = branch

            # Get analyses sorted by timestamp (newest first)
            cursor = self.repo_analyses.find(query).sort('timestamp', -1).limit(limit)
            analyses = list(cursor)

            # Convert ObjectId to string and format for frontend
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
                # Extract summary info for list view
                if 'summary' in analysis:
                    summary = analysis.get('summary', {})
                    analysis['file_count'] = summary.get('file_count', 0)
                    analysis['total_loc'] = summary.get('total_loc', 0)
                    
                    # Get test coverage if available
                    test_coverage = summary.get('test_coverage', {})
                    analysis['test_coverage'] = test_coverage.get('estimated_coverage', 0)
                    
                    # Get API info if available
                    api_detection = summary.get('api_detection', {})
                    analysis['has_apis'] = api_detection.get('has_apis', False)
                    analysis['api_count'] = api_detection.get('total_endpoints', 0)

            return analyses

        except Exception as e:
            print(f"❌ Failed to get repo analysis history: {e}")
            return []



