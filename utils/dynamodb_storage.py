"""
DynamoDB Session Storage for PR Reviews
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
import json
import uuid
from config import Config
from utils.database_interface import DatabaseInterface


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to int/float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def convert_floats_to_decimal(obj):
    """Convert floats to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


def convert_decimals_to_float(obj):
    """Convert Decimal to float/int for Python usage"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    return obj


class DynamoDBStorage(DatabaseInterface):
    """Store and retrieve PR review sessions in DynamoDB"""

    def __init__(self, **kwargs):
        """
        Initialize DynamoDB connection

        Args:
            **kwargs: DynamoDB configuration from Config
        """
        config = kwargs if kwargs else Config.get_dynamodb_config()

        self.table_prefix = config.get('table_prefix', 'pr_review')
        self._connected = False

        try:
            # Create boto3 session
            session_config = {
                'region_name': config.get('region_name', 'us-east-1')
            }

            if config.get('aws_access_key_id') and config.get('aws_secret_access_key'):
                session_config['aws_access_key_id'] = config['aws_access_key_id']
                session_config['aws_secret_access_key'] = config['aws_secret_access_key']

            # Create DynamoDB resource
            dynamodb_config = session_config.copy()
            if config.get('endpoint_url'):
                dynamodb_config['endpoint_url'] = config['endpoint_url']

            self.dynamodb = boto3.resource('dynamodb', **dynamodb_config)

            # Table names
            self.sessions_table_name = f"{self.table_prefix}_sessions"
            self.snapshots_table_name = f"{self.table_prefix}_snapshots"
            self.prompts_table_name = f"{self.table_prefix}_prompts"
            self.onboarding_table_name = f"{self.table_prefix}_onboarding"

            # Get table references
            self.sessions_table = self.dynamodb.Table(self.sessions_table_name)
            self.snapshots_table = self.dynamodb.Table(self.snapshots_table_name)
            self.prompts_table = self.dynamodb.Table(self.prompts_table_name)
            self.onboarding_table = self.dynamodb.Table(self.onboarding_table_name)

            # Test connection
            self.sessions_table.table_status
            self._connected = True
            print("✅ DynamoDB connected successfully")

        except Exception as e:
            print(f"⚠️  DynamoDB not available: {e}")
            print("   Session storage disabled. Reviews will not be saved.")
            self._connected = False

    @property
    def connected(self) -> bool:
        """Check if database is connected"""
        return self._connected

    def save_session(self, session_data: Dict) -> Optional[str]:
        """
        Save a review session to DynamoDB

        Args:
            session_data: Dictionary containing review results

        Returns:
            Session ID (str) or None if storage failed
        """
        if not self.connected:
            return None

        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())

            # Add metadata
            timestamp = datetime.utcnow()
            session_data['session_id'] = session_id
            session_data['timestamp'] = timestamp.isoformat()
            session_data['created_at'] = timestamp.isoformat()
            session_data['ttl'] = int((timestamp + timedelta(days=365)).timestamp())  # 1 year TTL

            # Convert floats to Decimal for DynamoDB
            item = convert_floats_to_decimal(session_data)

            # Insert into DynamoDB
            self.sessions_table.put_item(Item=item)

            print(f"✅ Session saved: {session_id}")
            return session_id

        except Exception as e:
            print(f"❌ Failed to save session: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a specific session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary or None
        """
        if not self.connected:
            return None

        try:
            response = self.sessions_table.get_item(
                Key={'session_id': session_id}
            )

            if 'Item' in response:
                item = response['Item']
                return convert_decimals_to_float(dict(item))
            return None

        except Exception as e:
            print(f"❌ Failed to retrieve session: {e}")
            return None

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent review sessions

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        if not self.connected:
            return []

        try:
            response = self.sessions_table.scan(
                Limit=1000  # Scan more to ensure we get enough recent ones
            )

            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Limit results
            sessions = items[:limit]

            return [convert_decimals_to_float(dict(s)) for s in sessions]

        except Exception as e:
            print(f"❌ Failed to retrieve recent sessions: {e}")
            return []

    def search_sessions(self, pr_url: str = None, repo_url: str = None) -> List[Dict]:
        """
        Search sessions by PR URL or repository URL

        Args:
            pr_url: Pull request URL to search for
            repo_url: Repository URL to search for

        Returns:
            List of matching session dictionaries
        """
        if not self.connected:
            return []

        try:
            filter_expression = None

            if pr_url:
                filter_expression = Attr('pr_url').eq(pr_url)
            if repo_url:
                if filter_expression:
                    filter_expression = filter_expression & Attr('repo_url').eq(repo_url)
                else:
                    filter_expression = Attr('repo_url').eq(repo_url)

            if filter_expression:
                response = self.sessions_table.scan(
                    FilterExpression=filter_expression
                )
            else:
                response = self.sessions_table.scan()

            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return [convert_decimals_to_float(dict(s)) for s in items]

        except Exception as e:
            print(f"❌ Failed to search sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.sessions_table.delete_item(
                Key={'session_id': session_id}
            )
            return True

        except Exception as e:
            print(f"❌ Failed to delete session: {e}")
            return False

    def get_statistics(self) -> Dict:
        """
        Get overall statistics

        Returns:
            Dictionary with statistics
        """
        if not self.connected:
            return {}

        try:
            response = self.sessions_table.scan()
            items = response.get('Items', [])

            if not items:
                return {
                    'total_sessions': 0,
                    'average_ddd_score': 0,
                    'top_repos': [],
                    'average_test_count': 0,
                    'average_files': 0
                }

            total_sessions = len(items)
            ddd_scores = [float(item.get('ddd_score', 0)) for item in items if item.get('ddd_score')]
            test_counts = [int(item.get('test_count', 0)) for item in items if item.get('test_count')]
            files_counts = [int(item.get('files_count', 0)) for item in items if item.get('files_count')]

            # Count repos
            repo_counts = {}
            for item in items:
                repo = item.get('repo_url', 'Unknown')
                repo_counts[repo] = repo_counts.get(repo, 0) + 1

            top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'total_sessions': total_sessions,
                'average_ddd_score': sum(ddd_scores) / len(ddd_scores) if ddd_scores else 0,
                'top_repos': [{'repo': repo, 'count': count} for repo, count in top_repos],
                'average_test_count': sum(test_counts) / len(test_counts) if test_counts else 0,
                'average_files': sum(files_counts) / len(files_counts) if files_counts else 0
            }

        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {}

    def get_all_repositories(self) -> List[str]:
        """
        Get list of all unique repository URLs

        Returns:
            List of repository URLs
        """
        if not self.connected:
            return []

        try:
            response = self.sessions_table.scan(
                ProjectionExpression='repo_url'
            )

            items = response.get('Items', [])
            repos = set(item.get('repo_url') for item in items if item.get('repo_url'))

            return sorted(list(repos))

        except Exception as e:
            print(f"❌ Failed to get repositories: {e}")
            return []

    def get_sessions_by_repositories(self, repo_urls: List[str]) -> List[Dict]:
        """
        Get sessions filtered by repository URLs

        Args:
            repo_urls: List of repository URLs

        Returns:
            List of session dictionaries
        """
        if not self.connected:
            return []

        try:
            # Build filter expression
            filter_expression = Attr('repo_url').is_in(repo_urls)

            response = self.sessions_table.scan(
                FilterExpression=filter_expression
            )

            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return [convert_decimals_to_float(dict(s)) for s in items]

        except Exception as e:
            print(f"❌ Failed to get sessions by repositories: {e}")
            return []

    def get_filtered_statistics(self, repo_urls: List[str] = None) -> Dict:
        """
        Get statistics filtered by repositories

        Args:
            repo_urls: List of repository URLs to filter by

        Returns:
            Dictionary with filtered statistics
        """
        if not self.connected:
            return {}

        try:
            if repo_urls:
                filter_expression = Attr('repo_url').is_in(repo_urls)
                response = self.sessions_table.scan(
                    FilterExpression=filter_expression
                )
            else:
                response = self.sessions_table.scan()

            items = response.get('Items', [])

            if not items:
                return {
                    'total_sessions': 0,
                    'average_ddd_score': 0,
                    'top_repos': [],
                    'average_test_count': 0,
                    'average_files': 0
                }

            total_sessions = len(items)
            ddd_scores = [float(item.get('ddd_score', 0)) for item in items if item.get('ddd_score')]
            test_counts = [int(item.get('test_count', 0)) for item in items if item.get('test_count')]
            files_counts = [int(item.get('files_count', 0)) for item in items if item.get('files_count')]

            # Count repos
            repo_counts = {}
            for item in items:
                repo = item.get('repo_url', 'Unknown')
                repo_counts[repo] = repo_counts.get(repo, 0) + 1

            top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'total_sessions': total_sessions,
                'average_ddd_score': sum(ddd_scores) / len(ddd_scores) if ddd_scores else 0,
                'top_repos': [{'repo': repo, 'count': count} for repo, count in top_repos],
                'average_test_count': sum(test_counts) / len(test_counts) if test_counts else 0,
                'average_files': sum(files_counts) / len(files_counts) if files_counts else 0
            }

        except Exception as e:
            print(f"❌ Failed to get filtered statistics: {e}")
            return {}

    def save_statistics_snapshot(self, snapshot_type: str = 'daily') -> Optional[str]:
        """
        Create and save a statistics snapshot

        Args:
            snapshot_type: Type of snapshot (daily/weekly/monthly)

        Returns:
            Snapshot ID or None if failed
        """
        if not self.connected:
            return None

        try:
            stats = self.get_statistics()

            snapshot_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            snapshot = {
                'snapshot_id': snapshot_id,
                'snapshot_type': snapshot_type,
                'timestamp': timestamp.isoformat(),
                'created_at': timestamp.isoformat(),
                'total_sessions': stats.get('total_sessions', 0),
                'average_ddd_score': stats.get('average_ddd_score', 0),
                'top_repos': stats.get('top_repos', []),
                'average_test_count': stats.get('average_test_count', 0),
                'average_files': stats.get('average_files', 0),
                'ttl': int((timestamp + timedelta(days=730)).timestamp())  # 2 year TTL
            }

            # Convert floats to Decimal
            item = convert_floats_to_decimal(snapshot)

            self.snapshots_table.put_item(Item=item)

            return snapshot_id

        except Exception as e:
            print(f"❌ Failed to save snapshot: {e}")
            return None

    def get_latest_snapshot(self, snapshot_type: str = 'daily') -> Optional[Dict]:
        """
        Get the most recent snapshot

        Args:
            snapshot_type: Type of snapshot

        Returns:
            Snapshot dictionary or None
        """
        if not self.connected:
            return None

        try:
            response = self.snapshots_table.scan(
                FilterExpression=Attr('snapshot_type').eq(snapshot_type)
            )

            items = response.get('Items', [])

            if not items:
                return None

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return convert_decimals_to_float(dict(items[0]))

        except Exception as e:
            print(f"❌ Failed to get latest snapshot: {e}")
            return None

    def get_snapshot_by_date_range(self, start_date: datetime, end_date: datetime,
                                   snapshot_type: str = 'daily') -> List[Dict]:
        """
        Get snapshots within a date range

        Args:
            start_date: Start date
            end_date: End date
            snapshot_type: Type of snapshot

        Returns:
            List of snapshot dictionaries
        """
        if not self.connected:
            return []

        try:
            filter_expression = (
                Attr('snapshot_type').eq(snapshot_type) &
                Attr('timestamp').gte(start_date.isoformat()) &
                Attr('timestamp').lte(end_date.isoformat())
            )

            response = self.snapshots_table.scan(
                FilterExpression=filter_expression
            )

            items = response.get('Items', [])

            # Sort by timestamp ascending
            items.sort(key=lambda x: x.get('timestamp', ''))

            return [convert_decimals_to_float(dict(s)) for s in items]

        except Exception as e:
            print(f"❌ Failed to get snapshots by date range: {e}")
            return []

    def calculate_trend(self, days: int = 7) -> Dict:
        """
        Calculate trend data over specified days

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend data
        """
        if not self.connected:
            return {}

        try:
            current_stats = self.get_statistics()

            past_date = datetime.utcnow() - timedelta(days=days)

            # Get snapshot from past
            past_snapshot = self.get_latest_snapshot('daily')

            if not past_snapshot:
                # No historical data
                return {
                    'current': current_stats,
                    'change': {
                        'total_sessions': 0,
                        'average_ddd_score': 0,
                        'average_test_count': 0,
                        'average_files': 0
                    }
                }

            change = {
                'total_sessions': current_stats.get('total_sessions', 0) - past_snapshot.get('total_sessions', 0),
                'average_ddd_score': current_stats.get('average_ddd_score', 0) - past_snapshot.get('average_ddd_score', 0),
                'average_test_count': current_stats.get('average_test_count', 0) - past_snapshot.get('average_test_count', 0),
                'average_files': current_stats.get('average_files', 0) - past_snapshot.get('average_files', 0)
            }

            return {
                'current': current_stats,
                'past': past_snapshot,
                'change': change
            }

        except Exception as e:
            print(f"❌ Failed to calculate trend: {e}")
            return {}

    def save_prompt_version(self, stage: str, version: str, prompt_content: str,
                          description: str = "", criteria: List[str] = None) -> Optional[str]:
        """
        Save a prompt version

        Args:
            stage: Review stage
            version: Version string
            prompt_content: Full prompt text
            description: Prompt description
            criteria: List of evaluation criteria

        Returns:
            Prompt version ID or None
        """
        if not self.connected:
            return None

        try:
            prompt_id = f"{stage}#{version}"
            timestamp = datetime.utcnow()

            prompt_data = {
                'prompt_id': prompt_id,
                'stage': stage,
                'version': version,
                'prompt_content': prompt_content,
                'description': description,
                'criteria': criteria or [],
                'active': True,
                'timestamp': timestamp.isoformat(),
                'created_at': timestamp.isoformat(),
                'ttl': int((timestamp + timedelta(days=730)).timestamp())  # 2 year TTL
            }

            self.prompts_table.put_item(Item=prompt_data)

            return prompt_id

        except Exception as e:
            print(f"❌ Failed to save prompt version: {e}")
            return None

    def get_prompt_version(self, stage: str, version: str = None) -> Optional[Dict]:
        """
        Get a specific prompt version

        Args:
            stage: Review stage
            version: Version string (None for latest active)

        Returns:
            Prompt version dictionary or None
        """
        if not self.connected:
            return None

        try:
            if version:
                prompt_id = f"{stage}#{version}"
                response = self.prompts_table.get_item(
                    Key={'prompt_id': prompt_id}
                )

                if 'Item' in response:
                    return dict(response['Item'])
                return None
            else:
                # Get latest active version
                response = self.prompts_table.scan(
                    FilterExpression=Attr('stage').eq(stage) & Attr('active').eq(True)
                )

                items = response.get('Items', [])

                if not items:
                    return None

                # Sort by timestamp descending
                items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

                return dict(items[0])

        except Exception as e:
            print(f"❌ Failed to get prompt version: {e}")
            return None

    def get_all_prompt_versions(self, stage: str = None) -> List[Dict]:
        """
        Get all prompt versions

        Args:
            stage: Filter by stage (None for all)

        Returns:
            List of prompt version dictionaries
        """
        if not self.connected:
            return []

        try:
            if stage:
                response = self.prompts_table.scan(
                    FilterExpression=Attr('stage').eq(stage)
                )
            else:
                response = self.prompts_table.scan()

            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return [dict(p) for p in items]

        except Exception as e:
            print(f"❌ Failed to get prompt versions: {e}")
            return []

    def deactivate_prompt_version(self, stage: str, version: str) -> bool:
        """
        Deactivate a prompt version

        Args:
            stage: Review stage
            version: Version string

        Returns:
            True if deactivated, False otherwise
        """
        if not self.connected:
            return False

        try:
            prompt_id = f"{stage}#{version}"

            self.prompts_table.update_item(
                Key={'prompt_id': prompt_id},
                UpdateExpression='SET active = :val',
                ExpressionAttributeValues={':val': False}
            )

            return True

        except Exception as e:
            print(f"❌ Failed to deactivate prompt version: {e}")
            return False

    def get_sessions_with_token_stats(self, limit: int = 10) -> List[Dict]:
        """
        Get sessions with token usage statistics

        Args:
            limit: Maximum number of sessions

        Returns:
            List of sessions with token stats
        """
        if not self.connected:
            return []

        try:
            sessions = self.get_recent_sessions(limit)

            # Add calculated token stats
            for session in sessions:
                token_usage = session.get('token_usage', {})
                session['total_tokens'] = (
                    token_usage.get('prompt_tokens', 0) +
                    token_usage.get('completion_tokens', 0)
                )

            return sessions

        except Exception as e:
            print(f"❌ Failed to get sessions with token stats: {e}")
            return []

    def save_onboarding(self, team_name: str, repositories: List[Dict]) -> Optional[str]:
        """
        Save onboarding information

        Args:
            team_name: Name of the team
            repositories: List of repository dictionaries

        Returns:
            Onboarding ID or None
        """
        if not self.connected:
            return None

        try:
            onboarding_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            onboarding_data = {
                'onboarding_id': onboarding_id,
                'team_name': team_name,
                'repositories': repositories,
                'timestamp': timestamp.isoformat(),
                'created_at': timestamp.isoformat(),
                'updated_at': timestamp.isoformat(),
                'ttl': int((timestamp + timedelta(days=730)).timestamp())  # 2 year TTL
            }

            self.onboarding_table.put_item(Item=onboarding_data)

            return onboarding_id

        except Exception as e:
            print(f"❌ Failed to save onboarding: {e}")
            return None

    def get_onboarding(self, onboarding_id: str = None) -> Optional[Dict]:
        """
        Get onboarding information

        Args:
            onboarding_id: Onboarding identifier (None for latest)

        Returns:
            Onboarding dictionary or None
        """
        if not self.connected:
            return None

        try:
            if onboarding_id:
                response = self.onboarding_table.get_item(
                    Key={'onboarding_id': onboarding_id}
                )

                if 'Item' in response:
                    return dict(response['Item'])
                return None
            else:
                # Get latest
                response = self.onboarding_table.scan()
                items = response.get('Items', [])

                if not items:
                    return None

                # Sort by timestamp descending
                items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

                return dict(items[0])

        except Exception as e:
            print(f"❌ Failed to get onboarding: {e}")
            return None

    def get_all_onboardings(self) -> List[Dict]:
        """
        Get all onboarding records

        Returns:
            List of onboarding dictionaries
        """
        if not self.connected:
            return []

        try:
            response = self.onboarding_table.scan()
            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return [dict(o) for o in items]

        except Exception as e:
            print(f"❌ Failed to get all onboardings: {e}")
            return []

    def update_onboarding(self, onboarding_id: str, team_name: str = None,
                         repositories: List[Dict] = None) -> bool:
        """
        Update onboarding information

        Args:
            onboarding_id: Onboarding identifier
            team_name: New team name
            repositories: New repositories list

        Returns:
            True if updated, False otherwise
        """
        if not self.connected:
            return False

        try:
            update_expr_parts = []
            expr_attr_values = {}

            if team_name is not None:
                update_expr_parts.append('team_name = :tn')
                expr_attr_values[':tn'] = team_name

            if repositories is not None:
                update_expr_parts.append('repositories = :repos')
                expr_attr_values[':repos'] = repositories

            # Always update timestamp
            update_expr_parts.append('updated_at = :ua')
            expr_attr_values[':ua'] = datetime.utcnow().isoformat()

            if not update_expr_parts:
                return False

            update_expression = 'SET ' + ', '.join(update_expr_parts)

            self.onboarding_table.update_item(
                Key={'onboarding_id': onboarding_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_attr_values
            )

            return True

        except Exception as e:
            print(f"❌ Failed to update onboarding: {e}")
            return False

    def delete_onboarding(self, onboarding_id: str) -> bool:
        """
        Delete onboarding record

        Args:
            onboarding_id: Onboarding identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.onboarding_table.delete_item(
                Key={'onboarding_id': onboarding_id}
            )

            return True

        except Exception as e:
            print(f"❌ Failed to delete onboarding: {e}")
            return False
