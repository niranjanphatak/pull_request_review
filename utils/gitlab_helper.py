import os
import re
from git import Repo
import shutil
import requests
from typing import Dict, Optional


def parse_diff_stats(diff_text: str) -> Dict[str, int]:
    """
    Parse a unified diff to calculate additions and deletions

    Args:
        diff_text: Unified diff text

    Returns:
        Dictionary with 'additions', 'deletions', and 'changes' counts
    """
    if not diff_text:
        return {'additions': 0, 'deletions': 0, 'changes': 0}

    additions = 0
    deletions = 0

    for line in diff_text.split('\n'):
        # Skip diff headers and metadata
        if line.startswith('+++') or line.startswith('---') or \
           line.startswith('@@') or line.startswith('diff ') or \
           line.startswith('index '):
            continue

        # Count additions (lines starting with +)
        if line.startswith('+'):
            additions += 1
        # Count deletions (lines starting with -)
        elif line.startswith('-'):
            deletions += 1

    return {
        'additions': additions,
        'deletions': deletions,
        'changes': additions + deletions
    }


class GitLabHelper:
    """
    Helper class for GitLab operations with multi-platform support
    Supports GitLab (Cloud & Self-hosted), GitHub, Bitbucket, and other Git platforms
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize helper with access token

        Args:
            access_token: Personal access token for private repositories
                         Works with GitLab, GitHub, Bitbucket tokens
        """
        self.access_token = access_token or os.getenv('GITLAB_TOKEN') or os.getenv('GITHUB_TOKEN')
        self.session = requests.Session()
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'PRIVATE-TOKEN': self.access_token  # GitLab specific
            })

    def detect_platform(self, url: str) -> str:
        """Detect Git platform from URL"""
        if 'gitlab' in url.lower():
            return 'gitlab'
        elif 'github' in url.lower():
            return 'github'
        elif 'bitbucket' in url.lower():
            return 'bitbucket'
        else:
            return 'generic'

    def parse_pr_url(self, pr_url: str) -> Dict[str, str]:
        """
        Parse Pull/Merge Request URL to extract owner, repo, and MR/PR number

        Supports:
        - GitLab: https://gitlab.com/owner/repo/-/merge_requests/123
        - GitHub: https://github.com/owner/repo/pull/456
        - Bitbucket: https://bitbucket.org/owner/repo/pull-requests/789
        - Self-hosted: https://git.company.com/owner/repo/-/merge_requests/123
        """
        platform = self.detect_platform(pr_url)

        # GitLab pattern (most flexible, works with self-hosted)
        gitlab_pattern = r'([^/]+)/([^/]+)/([^/]+)/-/merge_requests/(\d+)'
        # GitHub pattern
        github_pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
        # Bitbucket pattern
        bitbucket_pattern = r'bitbucket\.org/([^/]+)/([^/]+)/pull-requests/(\d+)'

        # Try GitLab pattern (works for most platforms)
        match = re.search(gitlab_pattern, pr_url)
        if match:
            return {
                'platform': 'gitlab',
                'host': match.group(1),
                'owner': match.group(2),
                'repo': match.group(3),
                'mr_number': int(match.group(4)),
                'type': 'merge_request'
            }

        # Try GitHub pattern
        match = re.search(github_pattern, pr_url)
        if match:
            return {
                'platform': 'github',
                'host': 'github.com',
                'owner': match.group(1),
                'repo': match.group(2),
                'mr_number': int(match.group(3)),
                'type': 'pull_request'
            }

        # Try Bitbucket pattern
        match = re.search(bitbucket_pattern, pr_url)
        if match:
            return {
                'platform': 'bitbucket',
                'host': 'bitbucket.org',
                'owner': match.group(1),
                'repo': match.group(2),
                'mr_number': int(match.group(3)),
                'type': 'pull_request'
            }

        raise ValueError(f"Unsupported PR/MR URL format: {pr_url}")

    def parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse repository URL

        Examples:
        - GitLab: https://gitlab.com/owner/repo
        - GitHub: https://github.com/owner/repo
        - Bitbucket: https://bitbucket.org/owner/repo
        - Self-hosted: https://git.company.com/owner/repo
        """
        platform = self.detect_platform(repo_url)

        # General pattern for most Git platforms
        pattern = r'([^:/]+(?:\.[^:/]+)+)/([^/]+)/([^/]+?)(?:\.git)?$'
        match = re.search(pattern, repo_url)

        if not match:
            raise ValueError(f"Invalid repository URL format: {repo_url}")

        return {
            'platform': platform,
            'host': match.group(1),
            'owner': match.group(2),
            'repo': match.group(3)
        }

    def get_mr_details(self, pr_url: str) -> Dict:
        """
        Fetch MR/PR details including diff, files changed, and metadata

        This is a generic implementation that works with Git platforms
        For production use, consider platform-specific API implementations
        """
        mr_info = self.parse_pr_url(pr_url)

        # Platform-specific API calls
        if mr_info['platform'] == 'gitlab':
            return self._get_gitlab_mr_details(mr_info, pr_url)
        elif mr_info['platform'] == 'github':
            return self._get_github_pr_details(mr_info, pr_url)
        else:
            # Generic fallback - basic info only
            return {
                'title': f"MR #{mr_info['mr_number']}",
                'description': 'Details not available via API',
                'platform': mr_info['platform'],
                'mr_number': mr_info['mr_number'],
                'files_changed': [],
                'note': 'Clone repository for full analysis'
            }

    def _get_gitlab_mr_details(self, mr_info: Dict, pr_url: str) -> Dict:
        """Fetch GitLab MR details using GitLab API"""
        try:
            # GitLab API endpoint
            host = mr_info['host']
            project_path = f"{mr_info['owner']}/{mr_info['repo']}"
            mr_number = mr_info['mr_number']

            # URL encode the project path
            encoded_project = project_path.replace('/', '%2F')

            # Determine API base URL
            if 'gitlab.com' in host:
                api_base = 'https://gitlab.com/api/v4'
            else:
                # Self-hosted GitLab
                api_base = f"https://{host}/api/v4"

            # Fetch MR details
            mr_url = f"{api_base}/projects/{encoded_project}/merge_requests/{mr_number}"

            headers = {}
            if self.access_token:
                headers['PRIVATE-TOKEN'] = self.access_token

            response = self.session.get(mr_url, headers=headers, timeout=30)
            response.raise_for_status()
            mr_data = response.json()

            # Fetch MR changes (files)
            changes_url = f"{mr_url}/changes"
            changes_response = self.session.get(changes_url, headers=headers, timeout=30)
            changes_response.raise_for_status()
            changes_data = changes_response.json()

            # Extract files changed and calculate total stats
            files_changed = []
            total_additions = 0
            total_deletions = 0

            for change in changes_data.get('changes', []):
                diff_text = change.get('diff', '')
                diff_stats = parse_diff_stats(diff_text)

                files_changed.append({
                    'filename': change.get('new_path', change.get('old_path')),
                    'status': 'modified' if change.get('new_path') == change.get('old_path') else 'renamed',
                    'new_file': change.get('new_file', False),
                    'deleted_file': change.get('deleted_file', False),
                    'renamed_file': change.get('renamed_file', False),
                    'old_path': change.get('old_path'),
                    'diff': diff_text,
                    'additions': diff_stats['additions'],
                    'deletions': diff_stats['deletions'],
                    'changes': diff_stats['changes']
                })

                total_additions += diff_stats['additions']
                total_deletions += diff_stats['deletions']

            return {
                'title': mr_data.get('title'),
                'description': mr_data.get('description'),
                'author': mr_data.get('author', {}).get('username'),
                'state': mr_data.get('state'),
                'created_at': mr_data.get('created_at'),
                'updated_at': mr_data.get('updated_at'),
                'source_branch': mr_data.get('source_branch'),
                'target_branch': mr_data.get('target_branch'),
                'files_changed': files_changed,
                'additions': total_additions,
                'deletions': total_deletions,
                'web_url': mr_data.get('web_url'),
                'platform': 'gitlab'
            }

        except Exception as e:
            print(f"Error fetching GitLab MR details: {str(e)}")
            return {
                'title': f"MR #{mr_info['mr_number']}",
                'description': f'Error fetching details: {str(e)}',
                'platform': 'gitlab',
                'error': str(e)
            }

    def _get_github_pr_details(self, mr_info: Dict, pr_url: str) -> Dict:
        """Fetch GitHub PR details using GitHub API"""
        try:
            # GitHub API endpoint
            owner = mr_info['owner']
            repo = mr_info['repo']
            pr_number = mr_info['mr_number']

            api_base = 'https://api.github.com'
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
                    'patch': file.get('patch')
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
                'files_changed': files_changed,
                'additions': pr_data.get('additions'),
                'deletions': pr_data.get('deletions'),
                'commits': pr_data.get('commits'),
                'platform': 'github'
            }

        except Exception as e:
            print(f"Error fetching GitHub PR details: {str(e)}")
            return {
                'title': f"PR #{mr_info['mr_number']}",
                'description': f'Error fetching details: {str(e)}',
                'platform': 'github',
                'error': str(e)
            }

    def clone_repository(self, repo_url: str, target_dir: str = 'temp_repos') -> str:
        """
        Clone repository to local directory

        Supports any Git repository (GitLab, GitHub, Bitbucket, self-hosted)
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
                clone_url = repo_url.replace('https://', f'https://oauth2:{self.access_token}@')
            elif repo_url.startswith('http://'):
                clone_url = repo_url.replace('http://', f'http://oauth2:{self.access_token}@')
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
