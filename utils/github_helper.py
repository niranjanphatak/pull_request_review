import os
import re
from github import Github
from git import Repo
import shutil
from typing import Dict, Optional


class GitHubHelper:
    """Helper class for GitHub operations"""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.github = Github(self.github_token) if self.github_token else Github()

    def parse_pr_url(self, pr_url: str) -> Dict[str, str]:
        """
        Parse PR URL to extract owner, repo, and PR number
        Example: https://github.com/owner/repo/pull/123
        """
        pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        match = re.search(pattern, pr_url)

        if not match:
            raise ValueError("Invalid GitHub PR URL format")

        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': int(match.group(3))
        }

    def parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse repository URL
        Example: https://github.com/owner/repo
        """
        pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$'
        match = re.search(pattern, repo_url)

        if not match:
            raise ValueError("Invalid GitHub repository URL format")

        return {
            'owner': match.group(1),
            'repo': match.group(2)
        }

    def get_pr_details(self, pr_url: str) -> Dict:
        """Fetch PR details including diff, files changed, and metadata"""
        pr_info = self.parse_pr_url(pr_url)
        repo = self.github.get_repo(f"{pr_info['owner']}/{pr_info['repo']}")
        pr = repo.get_pull(pr_info['pr_number'])

        # Get files changed
        files_changed = []
        for file in pr.get_files():
            files_changed.append({
                'filename': file.filename,
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if hasattr(file, 'patch') else None
            })

        return {
            'title': pr.title,
            'description': pr.body,
            'author': pr.user.login,
            'state': pr.state,
            'created_at': pr.created_at.isoformat(),
            'updated_at': pr.updated_at.isoformat(),
            'base_branch': pr.base.ref,
            'head_branch': pr.head.ref,
            'files_changed': files_changed,
            'additions': pr.additions,
            'deletions': pr.deletions,
            'commits': pr.commits,
            'diff_url': pr.diff_url
        }

    def clone_repository(self, repo_url: str, target_dir: str = 'temp_repos') -> str:
        """Clone repository to local directory"""
        repo_info = self.parse_repo_url(repo_url)
        repo_name = repo_info['repo']

        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        repo_path = os.path.join(target_dir, repo_name)

        # Remove existing clone if exists
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

        # Clone repository
        if self.github_token:
            clone_url = f"https://{self.github_token}@github.com/{repo_info['owner']}/{repo_name}.git"
        else:
            clone_url = repo_url

        Repo.clone_from(clone_url, repo_path)
        return repo_path

    def get_file_content(self, repo_path: str, file_path: str) -> str:
        """Read file content from cloned repository"""
        full_path = os.path.join(repo_path, file_path)

        if not os.path.exists(full_path):
            return None

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
