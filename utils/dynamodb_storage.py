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
            self.prompt_candidates_table_name = f"{self.table_prefix}_prompt_candidates"
            self.analysis_reports_table_name = f"{self.table_prefix}_analysis_reports"

            # Get table references
            self.sessions_table = self.dynamodb.Table(self.sessions_table_name)
            self.snapshots_table = self.dynamodb.Table(self.snapshots_table_name)
            self.prompts_table = self.dynamodb.Table(self.prompts_table_name)
            self.onboarding_table = self.dynamodb.Table(self.onboarding_table_name)
            self.prompt_candidates_table = self.dynamodb.Table(self.prompt_candidates_table_name)
            self.analysis_reports_table = self.dynamodb.Table(self.analysis_reports_table_name)

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
                item = convert_decimals_to_float(dict(response['Item']))
                if 'session_id' in item:
                    item['_id'] = item['session_id']
                return item
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
            sessions = [convert_decimals_to_float(dict(s)) for s in items[:limit]]

            # Add _id alias for frontend compatibility
            for s in sessions:
                if 'session_id' in s:
                    s['_id'] = s['session_id']

            return sessions

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

            sessions = [convert_decimals_to_float(dict(s)) for s in items]
            for s in sessions:
                if 'session_id' in s:
                    s['_id'] = s['session_id']
            return sessions

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
            return {
                'total_sessions': 0,
                'connected': False
            }

        try:
            response = self.sessions_table.scan()
            items = response.get('Items', [])

            if not items:
                return {
                    'total_sessions': 0,
                    'connected': True,
                    'average_ddd_score': 0,
                    'top_repos': [],
                    'average_test_count': 0,
                    'average_files': 0,
                    'total_tokens_used': 0,
                    'avg_tokens_per_review': 0
                }

            total_sessions = len(items)
            ddd_scores = [float(item.get('ddd_score', 0)) for item in items if item.get('ddd_score')]
            test_counts = [int(item.get('test_count', 0)) for item in items if item.get('test_count')]
            files_counts = [int(item.get('files_count', 0)) for item in items if item.get('files_count')]

            # Calculate total tokens
            total_tokens_used = 0
            for item in items:
                token_usage = item.get('token_usage', {})
                if isinstance(token_usage, dict):
                    # Sum up tokens from all stages (architecture, security, bugs, style, tests)
                    for stage in ['architecture', 'security', 'bugs', 'style', 'performance', 'tests']:
                        stage_usage = token_usage.get(stage, {})
                        if isinstance(stage_usage, dict):
                            total_tokens_used += int(stage_usage.get('total_tokens', 0))

            # Count repos
            repo_counts = {}
            for item in items:
                repo = item.get('repo_url', 'Unknown')
                repo_counts[repo] = repo_counts.get(repo, 0) + 1

            top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'total_sessions': total_sessions,
                'connected': True,
                'average_ddd_score': sum(ddd_scores) / len(ddd_scores) if ddd_scores else 0,
                'top_repos': [{'_id': repo, 'count': count} for repo, count in top_repos],
                'average_test_count': sum(test_counts) / len(test_counts) if test_counts else 0,
                'average_files': sum(files_counts) / len(files_counts) if files_counts else 0,
                'total_tokens_used': total_tokens_used,
                'avg_tokens_per_review': int(total_tokens_used / total_sessions) if total_sessions > 0 else 0
            }

        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {
                'total_sessions': 0,
                'connected': False,
                'error': str(e)
            }

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

            sessions = [convert_decimals_to_float(dict(s)) for s in items]
            for s in sessions:
                if 'session_id' in s:
                    s['_id'] = s['session_id']
            return sessions

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
            return {
                'total_sessions': 0,
                'connected': False
            }

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
                    'connected': True,
                    'average_ddd_score': 0,
                    'top_repos': [],
                    'average_test_count': 0,
                    'average_files': 0,
                    'recent_sessions': 0
                }

            total_sessions = len(items)
            ddd_scores = [float(item.get('ddd_score', 0)) for item in items if item.get('ddd_score')]
            test_counts = [int(item.get('test_count', 0)) for item in items if item.get('test_count')]
            files_counts = [int(item.get('files_count', 0)) for item in items if item.get('files_count')]

            # Calculate recent reviews (last 24 hours)
            yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
            recent_count = sum(1 for item in items if item.get('timestamp', '') >= yesterday)

            # Count repos
            repo_counts = {}
            for item in items:
                repo = item.get('repo_url', 'Unknown')
                repo_counts[repo] = repo_counts.get(repo, 0) + 1

            top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'total_sessions': total_sessions,
                'recent_sessions': recent_count,
                'connected': True,
                'average_ddd_score': sum(ddd_scores) / len(ddd_scores) if ddd_scores else 0,
                'top_repos': [{'_id': repo, 'count': count} for repo, count in top_repos],
                'average_test_count': sum(test_counts) / len(test_counts) if test_counts else 0,
                'average_files': sum(files_counts) / len(files_counts) if files_counts else 0,
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

    def calculate_trend(self, metric_name: str, days_back: int = 7) -> Dict:
        """
        Calculate trend for a specific metric

        Args:
            metric_name: Name of metric to track (e.g., 'total_sessions', 'average_ddd_score')
            days_back: Number of days to look back (currently using latest snapshot as proxy)

        Returns:
            Dictionary with trend data
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
            current_stats = self.get_statistics()
            current_value = current_stats.get(metric_name, 0)

            # Get snapshot from past
            past_snapshot = self.get_latest_snapshot('daily')

            if not past_snapshot:
                # No historical data
                return {
                    'current': current_value,
                    'previous': 0,
                    'change': 0,
                    'percentage_change': 0,
                    'trend': 'neutral',
                    'message': 'No historical data available'
                }

            previous_value = past_snapshot.get(metric_name, 0)
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
                    item = dict(response['Item'])
                    if 'prompt_id' in item:
                        item['_id'] = item['prompt_id']
                    return item
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

                item = dict(items[0])
                if 'prompt_id' in item:
                    item['_id'] = item['prompt_id']
                return item

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

            versions = [dict(p) for p in items]
            # Add _id alias for consistency
            for v in versions:
                if 'prompt_id' in v:
                    v['_id'] = v['prompt_id']
            
            return versions

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
                total_tokens = 0
                if isinstance(token_usage, dict):
                    # Sum up tokens from all stages (architecture, security, bugs, style, tests)
                    for stage in ['architecture', 'security', 'bugs', 'style', 'performance', 'tests']:
                        stage_usage = token_usage.get(stage, {})
                        if isinstance(stage_usage, dict):
                            total_tokens += int(stage_usage.get('total_tokens', 0))
                session['total_tokens'] = total_tokens

            return sessions

        except Exception as e:
            print(f"❌ Failed to get sessions with token stats: {e}")
            return []

    def save_onboarding(self, onboarding_data: Dict) -> Optional[str]:
        """
        Save onboarding information to DynamoDB

        Args:
            onboarding_data: Dictionary containing onboarding details

        Returns:
            Onboarding ID or None
        """
        if not self.connected:
            return None

        try:
            onboarding_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            onboarding_data['onboarding_id'] = onboarding_id
            onboarding_data['timestamp'] = timestamp.isoformat()
            onboarding_data['created_at'] = timestamp.isoformat()
            onboarding_data['updated_at'] = timestamp.isoformat()
            onboarding_data['ttl'] = int((timestamp + timedelta(days=730)).timestamp())  # 2 year TTL

            item = convert_floats_to_decimal(onboarding_data)
            self.onboarding_table.put_item(Item=item)

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
                    item = convert_decimals_to_float(dict(response['Item']))
                    if 'onboarding_id' in item:
                        item['_id'] = item['onboarding_id']
                    return item
                return None
            else:
                # Get latest
                response = self.onboarding_table.scan()
                items = response.get('Items', [])

                if not items:
                    return None

                # Sort by timestamp descending
                items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

                item = convert_decimals_to_float(dict(items[0]))
                if 'onboarding_id' in item:
                    item['_id'] = item['onboarding_id']
                return item

        except Exception as e:
            print(f"❌ Failed to get onboarding: {e}")
            return None

    def get_all_onboardings(self, limit: int = 50) -> List[Dict]:
        """
        Get all onboarding records from DynamoDB

        Args:
            limit: Maximum number of records

        Returns:
            List of onboarding dictionaries
        """
        if not self.connected:
            return []

        try:
            response = self.onboarding_table.scan(Limit=limit)
            items = response.get('Items', [])

            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Limit results
            results = [convert_decimals_to_float(dict(o)) for o in items]
            
            # Add _id alias for frontend compatibility
            for r in results:
                if 'onboarding_id' in r:
                    r['_id'] = r['onboarding_id']
                    
            return results

        except Exception as e:
            print(f"❌ Failed to get all onboardings: {e}")
            return []

    def update_onboarding(self, onboarding_id: str, updates: Dict) -> bool:
        """
        Update onboarding information in DynamoDB

        Args:
            onboarding_id: Onboarding identifier
            updates: Dictionary with fields to update

        Returns:
            True if updated, False otherwise
        """
        if not self.connected:
            return False

        try:
            update_expr_parts = []
            expr_attr_values = {}

            for key, value in updates.items():
                if key != 'onboarding_id':
                    update_expr_parts.append(f"{key} = :{key}")
                    expr_attr_values[f":{key}"] = value

            # Always update timestamp
            update_expr_parts.append('updated_at = :ua')
            expr_attr_values[':ua'] = datetime.utcnow().isoformat()

            if not update_expr_parts:
                return False

            update_expression = 'SET ' + ', '.join(update_expr_parts)
            
            # Convert values to Decimal
            expr_attr_values = convert_floats_to_decimal(expr_attr_values)

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

    # Prompt Candidate Operations (Optimization)
    def save_prompt_candidate(self, candidate_data: Dict) -> Optional[str]:
        """
        Save a generated prompt candidate to DynamoDB

        Args:
            candidate_data: Dictionary containing candidate details

        Returns:
            Candidate ID or None
        """
        if not self.connected:
            return None

        try:
            candidate_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            candidate_data['candidate_id'] = candidate_id
            candidate_data['timestamp'] = timestamp.isoformat()
            candidate_data['created_at'] = timestamp.isoformat()
            candidate_data['accepted'] = False
            candidate_data['ttl'] = int((timestamp + timedelta(days=90)).timestamp())  # 90 day TTL

            item = convert_floats_to_decimal(candidate_data)
            self.prompt_candidates_table.put_item(Item=item)

            return candidate_id

        except Exception as e:
            print(f"❌ Failed to save prompt candidate: {e}")
            return None

    def get_prompt_candidates(self, accepted: bool = False, limit: int = 50) -> List[Dict]:
        """
        Get prompt candidates from DynamoDB

        Args:
            accepted: Filter by acceptance status
            limit: Maximum number of entries to return

        Returns:
            List of candidate dictionaries
        """
        if not self.connected:
            return []

        try:
            response = self.prompt_candidates_table.scan(
                FilterExpression=Attr('accepted').eq(accepted),
                Limit=limit
            )

            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            candidates = [convert_decimals_to_float(dict(i)) for i in items]
            # Add _id alias for compatibility with app.js
            for c in candidates:
                if 'candidate_id' in c:
                    c['_id'] = c['candidate_id']
            return candidates

        except Exception as e:
            print(f"❌ Failed to get prompt candidates: {e}")
            return []

    def get_prompt_candidate(self, candidate_id: str) -> Optional[Dict]:
        """
        Get a specific prompt candidate by ID

        Args:
            candidate_id: Candidate identifier

        Returns:
            Candidate dictionary or None
        """
        if not self.connected:
            return None

        try:
            response = self.prompt_candidates_table.get_item(
                Key={'candidate_id': candidate_id}
            )

            if 'Item' in response:
                item = convert_decimals_to_float(dict(response['Item']))
                if 'candidate_id' in item:
                    item['_id'] = item['candidate_id']
                return item
            return None

        except Exception as e:
            print(f"❌ Failed to get prompt candidate: {e}")
            return None

    def accept_prompt_candidate(self, candidate_id: str) -> bool:
        """
        Mark a prompt candidate as accepted

        Args:
            candidate_id: Candidate identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.prompt_candidates_table.update_item(
                Key={'candidate_id': candidate_id},
                UpdateExpression='SET accepted = :true',
                ExpressionAttributeValues={':true': True}
            )
            return True

        except Exception as e:
            print(f"❌ Failed to accept prompt candidate: {e}")
            return False

    def delete_prompt_candidate(self, candidate_id: str) -> bool:
        """
        Delete a prompt candidate from DynamoDB

        Args:
            candidate_id: Candidate identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.prompt_candidates_table.delete_item(
                Key={'candidate_id': candidate_id}
            )
            return True

        except Exception as e:
            print(f"❌ Failed to delete prompt candidate: {e}")
            return False



    def save_repo_analysis(self, analysis_data: Dict) -> Optional[str]:
        """Save a repository analysis report to DynamoDB"""
        if not self._connected:
            return None

        try:
            # Generate ID if not present
            if 'report_id' not in analysis_data:
                analysis_data['report_id'] = str(uuid.uuid4())
            
            # Add timestamp if not present
            if 'timestamp' not in analysis_data:
                analysis_data['timestamp'] = datetime.utcnow().isoformat()
            
            report_id = analysis_data['report_id']
            
            # Convert floats to decimals for DynamoDB
            db_item = convert_floats_to_decimal(analysis_data)
            
            # Put item
            self.analysis_reports_table.put_item(Item=db_item)
            return report_id

        except Exception as e:
            print(f"❌ Failed to save repo analysis: {e}")
            return None

    def get_repo_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Retrieve a repository analysis by ID from DynamoDB"""
        if not self._connected:
            return None

        try:
            response = self.analysis_reports_table.get_item(
                Key={'report_id': analysis_id}
            )

            if 'Item' in response:
                return convert_decimals_to_float(dict(response['Item']))
            return None

        except Exception as e:
            print(f"❌ Failed to get repo analysis: {e}")
            return None

    def get_recent_repo_analyses(self, limit: int = 10) -> List[Dict]:
        """Get recent repository analyses from DynamoDB"""
        if not self._connected:
            return []

        try:
            # Scan table (fine for small number of analysis reports)
            response = self.analysis_reports_table.scan(Limit=limit)
            items = response.get('Items', [])
            
            # Sort manually if needed (Scan doesn't guarantee order)
            sorted_items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return [convert_decimals_to_float(item) for item in sorted_items]

        except Exception as e:
            print(f"❌ Failed to get recent repo analyses: {e}")
            return []

    def close(self):
        """Close connection (dummy for DynamoDB)"""
        pass
