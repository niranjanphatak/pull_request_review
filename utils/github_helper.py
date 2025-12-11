import os
import re
from git import Repo
import shutil
import requests
from typing import Dict, Optional


class GitHubHelper:
    """
    Helper class for GitHub operations
    Supports GitHub (Cloud & Enterprise)
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize helper with access token

        Args:
            access_token: Personal access token for private repositories
        """
        self.access_token = access_token or os.getenv('GITHUB_TOKEN')
        self.session = requests.Session()
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'token {self.access_token}',
                'Accept': 'application/vnd.github.v3+json'
            })

    def parse_pr_url(self, pr_url: str) -> Dict[str, str]:
        """
        Parse Pull Request URL to extract owner, repo, and PR number

        Supports:
        - GitHub: https://github.com/owner/repo/pull/456
        - GitHub Enterprise: https://github.company.com/owner/repo/pull/456
        """
        # GitHub pattern
        github_pattern = r'github[^/]*/([^/]+)/([^/]+)/pull/(\d+)'

        match = re.search(github_pattern, pr_url)
        if match:
            # Extract host from URL
            host_match = re.search(r'https?://([^/]+)', pr_url)
            host = host_match.group(1) if host_match else 'github.com'

            return {
                'platform': 'github',
                'host': host,
                'owner': match.group(1),
                'repo': match.group(2),
                'pr_number': int(match.group(3)),
                'type': 'pull_request'
            }

        raise ValueError(f"Unsupported GitHub PR URL format: {pr_url}")

    def parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse repository URL

        Examples:
        - GitHub: https://github.com/owner/repo
        - GitHub Enterprise: https://github.company.com/owner/repo
        """
        # General pattern for GitHub repositories
        pattern = r'([^:/]+(?:\.[^:/]+)*)/([^/]+)/([^/]+?)(?:\.git)?$'
        match = re.search(pattern, repo_url)

        if not match:
            raise ValueError(f"Invalid repository URL format: {repo_url}")

        return {
            'platform': 'github',
            'host': match.group(1),
            'owner': match.group(2),
            'repo': match.group(3)
        }

    def get_pr_details(self, pr_url: str) -> Dict:
        """
        Fetch PR details including diff, files changed, and metadata
        """
        pr_info = self.parse_pr_url(pr_url)
        return self._get_github_pr_details(pr_info, pr_url)

    def _get_github_pr_details(self, pr_info: Dict, pr_url: str) -> Dict:
        """Fetch GitHub PR details using GitHub API"""
        try:
            # GitHub API endpoint
            owner = pr_info['owner']
            repo = pr_info['repo']
            pr_number = pr_info['pr_number']
            host = pr_info['host']

            # Determine API base URL
            if host == 'github.com':
                api_base = 'https://api.github.com'
            else:
                # GitHub Enterprise
                api_base = f"https://{host}/api/v3"

            pr_api_url = f"{api_base}/repos/{owner}/{repo}/pulls/{pr_number}"

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if self.access_token:
                headers['Authorization'] = f'token {self.access_token}'

            response = self.session.get(pr_api_url, headers=headers, timeout=30)
            response.raise_for_status()
            pr_data = response.json()

            # Fetch files
            files_url = f"{pr_api_url}/files"
            files_response = self.session.get(files_url, headers=headers, timeout=30)
            files_response.raise_for_status()
            files_data = files_response.json()

            # Extract files changed
            files_changed = []
            for file in files_data:
                files_changed.append({
                    'filename': file.get('filename'),
                    'status': file.get('status'),
                    'additions': file.get('additions'),
                    'deletions': file.get('deletions'),
                    'changes': file.get('changes'),
                    'patch': file.get('patch'),
                    'new_file': file.get('status') == 'added',
                    'deleted_file': file.get('status') == 'removed',
                    'diff': file.get('patch', '')
                })

            return {
                'title': pr_data.get('title'),
                'description': pr_data.get('body'),
                'author': pr_data.get('user', {}).get('login'),
                'state': pr_data.get('state'),
                'created_at': pr_data.get('created_at'),
                'updated_at': pr_data.get('updated_at'),
                'base_branch': pr_data.get('base', {}).get('ref'),
                'head_branch': pr_data.get('head', {}).get('ref'),
                'source_branch': pr_data.get('head', {}).get('ref'),
                'target_branch': pr_data.get('base', {}).get('ref'),
                'files_changed': files_changed,
                'additions': pr_data.get('additions'),
                'deletions': pr_data.get('deletions'),
                'commits': pr_data.get('commits'),
                'web_url': pr_data.get('html_url'),
                'platform': 'github'
            }

        except Exception as e:
            print(f"Error fetching GitHub PR details: {str(e)}")
            return {
                'title': f"PR #{pr_info['pr_number']}",
                'description': f'Error fetching details: {str(e)}',
                'platform': 'github',
                'error': str(e)
            }

    def clone_repository(self, repo_url: str, target_dir: str = 'temp_repos') -> str:
        """
        Clone repository to local directory

        Supports any GitHub repository (github.com, GitHub Enterprise)
        """
        repo_info = self.parse_repo_url(repo_url)
        repo_name = repo_info['repo']

        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        repo_path = os.path.join(target_dir, repo_name)

        # Remove existing clone if exists
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

        # Construct clone URL with authentication if token provided
        if self.access_token:
            # Extract protocol and host
            if repo_url.startswith('https://'):
                clone_url = repo_url.replace('https://', f'https://{self.access_token}@')
            elif repo_url.startswith('http://'):
                clone_url = repo_url.replace('http://', f'http://{self.access_token}@')
            else:
                clone_url = repo_url
        else:
            clone_url = repo_url

        # Ensure URL ends with .git
        if not clone_url.endswith('.git'):
            clone_url += '.git'

        # Clone repository
        try:
            Repo.clone_from(clone_url, repo_path, depth=1)  # Shallow clone for speed
            print(f"Successfully cloned repository to {repo_path}")
        except Exception as e:
            print(f"Error cloning repository: {str(e)}")
            # Try without authentication if it fails
            if self.access_token:
                try:
                    clone_url = repo_url if repo_url.endswith('.git') else f"{repo_url}.git"
                    Repo.clone_from(clone_url, repo_path, depth=1)
                    print(f"Successfully cloned repository (public access) to {repo_path}")
                except Exception as e2:
                    raise Exception(f"Failed to clone repository: {str(e2)}")
            else:
                raise

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

    def cleanup_repository(self, repo_path: str):
        """Remove cloned repository"""
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path)
                print(f"Cleaned up repository at {repo_path}")
            except Exception as e:
                print(f"Error cleaning up repository: {str(e)}")
