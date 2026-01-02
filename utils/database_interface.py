"""
Database Interface - Abstract base class for database operations
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class DatabaseInterface(ABC):
    """Abstract interface for database operations"""

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize database connection"""
        pass

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Check if database is connected"""
        pass

    # Session Operations
    @abstractmethod
    def save_session(self, session_data: Dict) -> Optional[str]:
        """
        Save a review session

        Args:
            session_data: Dictionary containing review results

        Returns:
            Session ID (str) or None if storage failed
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a specific session by ID

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary or None
        """
        pass

    @abstractmethod
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent review sessions

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        pass

    @abstractmethod
    def search_sessions(self, pr_url: str = None, repo_url: str = None) -> List[Dict]:
        """
        Search sessions by PR URL or repository URL

        Args:
            pr_url: Pull request URL to search for
            repo_url: Repository URL to search for

        Returns:
            List of matching session dictionaries
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise
        """
        pass

    # Statistics Operations
    @abstractmethod
    def get_statistics(self) -> Dict:
        """
        Get overall statistics

        Returns:
            Dictionary with statistics
        """
        pass

    @abstractmethod
    def get_all_repositories(self) -> List[str]:
        """
        Get list of all unique repository URLs

        Returns:
            List of repository URLs
        """
        pass

    @abstractmethod
    def get_sessions_by_repositories(self, repo_urls: List[str]) -> List[Dict]:
        """
        Get sessions filtered by repository URLs

        Args:
            repo_urls: List of repository URLs

        Returns:
            List of session dictionaries
        """
        pass

    @abstractmethod
    def get_filtered_statistics(self, repo_urls: List[str] = None) -> Dict:
        """
        Get statistics filtered by repositories

        Args:
            repo_urls: List of repository URLs to filter by

        Returns:
            Dictionary with filtered statistics
        """
        pass

    # Snapshot Operations
    @abstractmethod
    def save_statistics_snapshot(self, snapshot_type: str = 'daily') -> Optional[str]:
        """
        Create and save a statistics snapshot

        Args:
            snapshot_type: Type of snapshot (daily/weekly/monthly)

        Returns:
            Snapshot ID or None if failed
        """
        pass

    @abstractmethod
    def get_latest_snapshot(self, snapshot_type: str = 'daily') -> Optional[Dict]:
        """
        Get the most recent snapshot

        Args:
            snapshot_type: Type of snapshot

        Returns:
            Snapshot dictionary or None
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def calculate_trend(self, days: int = 7) -> Dict:
        """
        Calculate trend data over specified days

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend data
        """
        pass

    # Prompt Version Operations
    @abstractmethod
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
        pass

    @abstractmethod
    def get_prompt_version(self, stage: str, version: str = None) -> Optional[Dict]:
        """
        Get a specific prompt version

        Args:
            stage: Review stage
            version: Version string (None for latest)

        Returns:
            Prompt version dictionary or None
        """
        pass

    @abstractmethod
    def get_all_prompt_versions(self, stage: str = None) -> List[Dict]:
        """
        Get all prompt versions

        Args:
            stage: Filter by stage (None for all)

        Returns:
            List of prompt version dictionaries
        """
        pass

    @abstractmethod
    def deactivate_prompt_version(self, stage: str, version: str) -> bool:
        """
        Deactivate a prompt version

        Args:
            stage: Review stage
            version: Version string

        Returns:
            True if deactivated, False otherwise
        """
        pass

    # Token Statistics Operations
    @abstractmethod
    def get_sessions_with_token_stats(self, limit: int = 10) -> List[Dict]:
        """
        Get sessions with token usage statistics

        Args:
            limit: Maximum number of sessions

        Returns:
            List of sessions with token stats
        """
        pass

    # Onboarding Operations
    @abstractmethod
    def save_onboarding(self, team_name: str, repositories: List[Dict]) -> Optional[str]:
        """
        Save onboarding information

        Args:
            team_name: Name of the team
            repositories: List of repository dictionaries

        Returns:
            Onboarding ID or None
        """
        pass

    @abstractmethod
    def get_onboarding(self, onboarding_id: str = None) -> Optional[Dict]:
        """
        Get onboarding information

        Args:
            onboarding_id: Onboarding identifier (None for latest)

        Returns:
            Onboarding dictionary or None
        """
        pass

    @abstractmethod
    def get_all_onboardings(self) -> List[Dict]:
        """
        Get all onboarding records

        Returns:
            List of onboarding dictionaries
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete_onboarding(self, onboarding_id: str) -> bool:
        """
        Delete onboarding record

        Args:
            onboarding_id: Onboarding identifier

        Returns:
            True if deleted, False otherwise
        """
        pass
