from typing import TypedDict, Annotated, Optional, Union
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from agents.review_agents import ReviewAgents
from utils.gitlab_helper import GitLabHelper
import os


class ReviewState(TypedDict):
    """State object for the review workflow"""
    pr_url: str
    repo_url: str
    pr_details: dict
    repo_path: str
    analyze_target_branch: bool
    target_branch_analysis: Optional[Union[str, dict]]
    security_review: Union[str, dict]
    bug_review: Union[str, dict]
    style_review: Union[str, dict]
    performance_review: Union[str, dict]
    test_suggestions: Union[str, dict]
    messages: Annotated[list, add_messages]
    status: str
    token_usage: dict  # Track AI token usage per stage


class PRReviewWorkflow:
    """LangGraph workflow for PR code review"""

    def __init__(
        self,
        ai_api_key: str,
        github_token: Optional[str] = None,
        ai_model: str = "claude-3-5-sonnet-20241022",
        ai_base_url: Optional[str] = None,
        ai_temperature: float = 0.1,
        progress_callback=None
    ):
        """
        Initialize PR review workflow

        Args:
            ai_api_key: API key for AI provider
            github_token: Optional access token for private repos (works with GitLab, GitHub, etc.)
            ai_model: Model name (default: claude-3-5-sonnet-20241022)
            ai_base_url: Optional base URL for custom AI endpoints
            ai_temperature: Temperature for LLM (default: 0.1)
            progress_callback: Optional callback function(step_name, progress_pct)
        """
        if not ai_api_key:
            raise ValueError("ai_api_key is required")

        self.gitlab_helper = GitLabHelper(github_token)
        self.review_agents = ReviewAgents(
            api_key=ai_api_key,
            model=ai_model,
            base_url=ai_base_url,
            temperature=ai_temperature
        )
        self.progress_callback = progress_callback
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(ReviewState)

        # Add nodes
        workflow.add_node("fetch_pr", self.fetch_pr_node)
        workflow.add_node("clone_repo", self.clone_repo_node)
        workflow.add_node("target_branch_check", self.target_branch_check_node)
        workflow.add_node("security_check", self.security_check_node)
        workflow.add_node("bug_check", self.bug_check_node)
        workflow.add_node("style_check", self.style_check_node)
        workflow.add_node("performance_check", self.performance_check_node)
        workflow.add_node("test_check", self.test_check_node)
        workflow.add_node("summarize", self.summarize_node)

        # Define workflow edges
        workflow.set_entry_point("fetch_pr")
        workflow.add_edge("fetch_pr", "clone_repo")
        workflow.add_edge("clone_repo", "target_branch_check")
        workflow.add_edge("target_branch_check", "security_check")
        workflow.add_edge("security_check", "bug_check")
        workflow.add_edge("bug_check", "style_check")
        workflow.add_edge("style_check", "performance_check")
        workflow.add_edge("performance_check", "test_check")
        workflow.add_edge("test_check", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    def fetch_pr_node(self, state: ReviewState) -> ReviewState:
        """Node to fetch PR/MR details"""
        try:
            print("=" * 80)
            print("📥 STAGE: Fetch PR/MR Details - START")
            print(f"   PR URL: {state.get('pr_url', 'N/A')}")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Fetching PR/MR details', 10)

            pr_details = self.gitlab_helper.get_mr_details(state['pr_url'])
            state['pr_details'] = pr_details
            state['status'] = 'PR details fetched successfully'
            state['messages'] = [{"role": "system", "content": f"Fetched PR: {pr_details['title']}"}]

            print("=" * 80)
            print("📥 STAGE: Fetch PR/MR Details - END")
            print(f"   Title: {pr_details.get('title', 'N/A')}")
            print(f"   Files Changed: {len(pr_details.get('files_changed', []))}")
            print("=" * 80)
        except Exception as e:
            state['status'] = f'Error fetching PR: {str(e)}'
            state['messages'] = [{"role": "system", "content": f"Error: {str(e)}"}]
            print("=" * 80)
            print(f"📥 STAGE: Fetch PR/MR Details - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def clone_repo_node(self, state: ReviewState) -> ReviewState:
        """Node to clone repository"""
        try:
            print("=" * 80)
            print("📦 STAGE: Clone Repository - START")
            print(f"   Repo URL: {state.get('repo_url', 'N/A')}")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Cloning repository (this may take a moment)', 20)

            repo_path = self.gitlab_helper.clone_repository(state['repo_url'])
            state['repo_path'] = repo_path
            state['status'] = 'Repository cloned successfully'
            state['messages'].append({"role": "system", "content": f"Cloned repository to {repo_path}"})

            print("=" * 80)
            print("📦 STAGE: Clone Repository - END")
            print(f"   Cloned to: {repo_path}")
            print("=" * 80)
        except Exception as e:
            # Mark repo_path as None to indicate failure
            state['repo_path'] = None
            state['status'] = f'Error cloning repository: {str(e)}'
            state['messages'].append({"role": "system", "content": f"Error cloning repository: {str(e)}"})

            # If target branch analysis is enabled, disable it since we can't proceed without repo
            if state.get('analyze_target_branch', False):
                state['target_branch_analysis'] = f'Skipped: Repository cloning failed - {str(e)}'

            print("=" * 80)
            print(f"📦 STAGE: Clone Repository - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def target_branch_check_node(self, state: ReviewState) -> ReviewState:
        """Node to analyze target branch code (optional)"""
        try:
            # Check if target branch analysis is enabled
            analyze_enabled = state.get('analyze_target_branch', False)

            print("=" * 80)
            print("🌳 STAGE: Target Branch Analysis - START")
            print(f"   Enabled: {analyze_enabled}")
            print("=" * 80)

            if not analyze_enabled:
                # Skip target branch analysis if not enabled
                state['target_branch_analysis'] = None
                if self.progress_callback:
                    self.progress_callback('Proceeding to code analysis', 30)
                print("=" * 80)
                print("🌳 STAGE: Target Branch Analysis - SKIPPED (Not Enabled)")
                print("=" * 80)
                return state

            # Check if already marked as skipped due to clone failure
            if state.get('target_branch_analysis') and 'Skipped:' in str(state.get('target_branch_analysis', '')):
                print("[Target Branch Check] Already skipped due to clone failure")
                if self.progress_callback:
                    self.progress_callback('Proceeding to code analysis', 30)
                return state

            # Get target branch from PR details
            pr_details = state.get('pr_details', {})
            # GitHub uses 'base_branch', GitLab uses 'target_branch'
            target_branch = pr_details.get('target_branch') or pr_details.get('base_branch') or 'main'
            repo_path = state.get('repo_path', '')

            print(f"[Target Branch Check] Enabled! repo_path='{repo_path}', target_branch='{target_branch}' (from PR details)")

            if not repo_path or repo_path is None:
                error_msg = f'Error: Repository path not available. Please ensure the repository was cloned successfully. State keys: {list(state.keys())}'
                state['target_branch_analysis'] = error_msg
                print(f"[Target Branch Check] ERROR: {error_msg}")
                if self.progress_callback:
                    self.progress_callback('Target branch analysis skipped (no repo path)', 30)
                return state

            if self.progress_callback:
                self.progress_callback('Analyzing target branch code (providing full context)', 30)

            # Read key files from the target branch to provide context
            import subprocess
            import json

            # Fetch the specific target branch
            print(f"[Target Branch] Fetching branch: {target_branch}")
            try:
                fetch_result = subprocess.run(
                    ['git', 'fetch', 'origin', target_branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                print(f"[Target Branch] Git fetch result: returncode={fetch_result.returncode}, stdout: {fetch_result.stdout}, stderr: {fetch_result.stderr}")

                if fetch_result.returncode != 0:
                    error_msg = fetch_result.stderr.strip() if fetch_result.stderr else 'Unknown error'
                    print(f"[Target Branch] Fetch failed for '{target_branch}': {error_msg}")

                    # Try to detect the actual default branch
                    print(f"[Target Branch] Attempting to detect default branch...")
                    try:
                        # Get the default branch from remote
                        remote_head_result = subprocess.run(
                            ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )

                        if remote_head_result.returncode == 0:
                            # Extract branch name from refs/remotes/origin/HEAD -> refs/remotes/origin/master
                            default_branch_ref = remote_head_result.stdout.strip()
                            target_branch = default_branch_ref.split('/')[-1]
                            print(f"[Target Branch] Detected default branch: {target_branch}")

                            # Try fetching the detected branch
                            fetch_result = subprocess.run(
                                ['git', 'fetch', 'origin', target_branch],
                                cwd=repo_path,
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            print(f"[Target Branch] Fetch detected branch result: returncode={fetch_result.returncode}")

                            if fetch_result.returncode != 0:
                                state['target_branch_analysis'] = f'Could not fetch target branch. Tried "{pr_details.get("target_branch") or pr_details.get("base_branch")}" and detected default "{target_branch}".'
                                return state
                        else:
                            # Fallback: try common default branch names
                            print(f"[Target Branch] Could not detect default branch, trying common names...")
                            common_branches = ['master', 'main', 'develop']
                            fetch_success = False

                            for branch_name in common_branches:
                                print(f"[Target Branch] Trying {branch_name}...")
                                fetch_result = subprocess.run(
                                    ['git', 'fetch', 'origin', branch_name],
                                    cwd=repo_path,
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )

                                if fetch_result.returncode == 0:
                                    target_branch = branch_name
                                    fetch_success = True
                                    print(f"[Target Branch] Successfully fetched {branch_name}")
                                    break

                            if not fetch_success:
                                state['target_branch_analysis'] = f'Could not find target branch. Tried: {pr_details.get("target_branch") or pr_details.get("base_branch")}, {", ".join(common_branches)}'
                                return state

                    except Exception as detect_error:
                        state['target_branch_analysis'] = f'Error detecting default branch: {str(detect_error)}'
                        print(f"[Target Branch] Branch detection exception: {detect_error}")
                        return state

            except Exception as fetch_error:
                state['target_branch_analysis'] = f'Error fetching target branch: {str(fetch_error)}'
                print(f"[Target Branch] Fetch exception: {fetch_error}")
                return state

            # Get list of all files in target branch - try multiple approaches
            files = []
            ls_tree_success = False

            # Approach 1: Try origin/{branch}
            print(f"[Target Branch] Approach 1: Trying origin/{target_branch}")
            try:
                result = subprocess.run(
                    ['git', 'ls-tree', '-r', '--name-only', f'origin/{target_branch}'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                print(f"[Target Branch] Approach 1 result: returncode={result.returncode}")

                if result.returncode == 0:
                    files = result.stdout.strip().split('\n')
                    ls_tree_success = True
                    print(f"[Target Branch] Approach 1 SUCCESS: {len(files)} files found")
                else:
                    print(f"[Target Branch] Approach 1 failed: {result.stderr}")
            except Exception as e:
                print(f"[Target Branch] Approach 1 exception: {e}")

            # Approach 2: If that failed, try FETCH_HEAD
            if not ls_tree_success:
                print(f"[Target Branch] Approach 2: Trying FETCH_HEAD")
                try:
                    result = subprocess.run(
                        ['git', 'ls-tree', '-r', '--name-only', 'FETCH_HEAD'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    print(f"[Target Branch] Approach 2 result: returncode={result.returncode}")

                    if result.returncode == 0:
                        files = result.stdout.strip().split('\n')
                        ls_tree_success = True
                        print(f"[Target Branch] Approach 2 SUCCESS: {len(files)} files found")
                    else:
                        print(f"[Target Branch] Approach 2 failed: {result.stderr}")
                except Exception as e:
                    print(f"[Target Branch] Approach 2 exception: {e}")

            # Approach 3: If that failed, try checking out the branch and using HEAD
            if not ls_tree_success:
                print(f"[Target Branch] Approach 3: Trying to checkout {target_branch}")
                try:
                    # Checkout the branch
                    checkout_result = subprocess.run(
                        ['git', 'checkout', target_branch],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    print(f"[Target Branch] Checkout result: returncode={checkout_result.returncode}")

                    if checkout_result.returncode == 0:
                        # Now try ls-tree with HEAD
                        result = subprocess.run(
                            ['git', 'ls-tree', '-r', '--name-only', 'HEAD'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        print(f"[Target Branch] Approach 3 result: returncode={result.returncode}")

                        if result.returncode == 0:
                            files = result.stdout.strip().split('\n')
                            ls_tree_success = True
                            print(f"[Target Branch] Approach 3 SUCCESS: {len(files)} files found")
                        else:
                            print(f"[Target Branch] Approach 3 failed: {result.stderr}")
                    else:
                        print(f"[Target Branch] Checkout failed: {checkout_result.stderr}")
                except Exception as e:
                    print(f"[Target Branch] Approach 3 exception: {e}")

            # If all approaches failed, return error
            if not ls_tree_success:
                error_msg = f'Could not read files from target branch "{target_branch}" using any method (origin/{target_branch}, FETCH_HEAD, or checkout).\n\nPlease verify the branch exists and is accessible.'
                state['target_branch_analysis'] = error_msg
                print(f"[Target Branch] ALL APPROACHES FAILED")
                return state

            # Continue with successful file list
            try:

                # Focus on important files (max 50 files for context)
                important_patterns = ['.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cpp', '.c', '.h']
                important_files = [f for f in files if any(f.endswith(p) for p in important_patterns)][:50]

                # Create summary of target branch structure
                analysis_summary = {
                    'target_branch': target_branch,
                    'total_files': len(files),
                    'analyzed_files': len(important_files),
                    'file_list': important_files
                }

                # Use AI to analyze target branch context
                context_prompt = f"""You are analyzing the target branch '{target_branch}' where PR changes will be merged.

Target Branch Files ({len(important_files)} files shown):
{chr(10).join(f'- {f}' for f in important_files[:30])}

Total files in target branch: {len(files)}

Provide a brief analysis of:
1. Overall codebase structure and organization
2. Key architectural patterns evident from file structure
3. Potential integration points for new changes
4. Any concerns about code organization or structure

Keep the analysis concise (3-5 bullet points)."""

                # Use the review agents to analyze
                target_analysis = self.review_agents.llm.invoke(context_prompt).content

                state['target_branch_analysis'] = target_analysis
                state['status'] = f'Target branch analysis completed for {target_branch}'
                state['messages'].append({
                    "role": "system",
                    "content": f"Analyzed target branch: {target_branch} ({len(files)} files)"
                })

                print("=" * 80)
                print("🌳 STAGE: Target Branch Analysis - END")
                print(f"   Branch: {target_branch}")
                print(f"   Files Analyzed: {len(important_files)}/{len(files)}")
                print("=" * 80)

            except subprocess.TimeoutExpired:
                state['target_branch_analysis'] = 'Timeout while reading target branch files'
                print("=" * 80)
                print("🌳 STAGE: Target Branch Analysis - ERROR: Timeout")
                print("=" * 80)
            except Exception as e:
                state['target_branch_analysis'] = f'Error analyzing target branch: {str(e)}'
                print("=" * 80)
                print(f"🌳 STAGE: Target Branch Analysis - ERROR: {str(e)}")
                print("=" * 80)

        except Exception as e:
            state['target_branch_analysis'] = f'Error in target branch analysis: {str(e)}'
            state['status'] = f'Error in target branch analysis: {str(e)}'
            print("=" * 80)
            print(f"🌳 STAGE: Target Branch Analysis - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def security_check_node(self, state: ReviewState) -> ReviewState:
        """Node for security review"""
        # Check if this stage is enabled
        if hasattr(self, 'enabled_stages') and not self.enabled_stages.get('security', True):
            print("=" * 80)
            print("🔒 STAGE: Security Review - SKIPPED (Disabled)")
            print("=" * 80)
            state['security_review'] = {
                "stage": "security",
                "findings": [],
                "summary": "Skipped: Stage disabled by user",
                "status": "skipped"
            }
            state['status'] = 'Security review skipped'
            return state

        try:
            print("=" * 80)
            print("🔒 STAGE: Security Review - START")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Running AI security analysis (analyzing vulnerabilities)', 40)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                security_review, token_usage = self.review_agents.security_review(files_changed)
                state['security_review'] = security_review
                state['token_usage']['security'] = token_usage
                state['status'] = 'Security review completed'
                state['messages'].append({"role": "system", "content": "Security review completed"})

            print("=" * 80)
            print("🔒 STAGE: Security Review - END")
            print("=" * 80)
        except Exception as e:
            state['security_review'] = {
                "stage": "security",
                "findings": [],
                "summary": f"Error during security review: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
            state['status'] = f'Error in security review: {str(e)}'
            print("=" * 80)
            print(f"🔒 STAGE: Security Review - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def bug_check_node(self, state: ReviewState) -> ReviewState:
        """Node for bug detection"""
        # Check if this stage is enabled
        if hasattr(self, 'enabled_stages') and not self.enabled_stages.get('bugs', True):
            print("=" * 80)
            print("🐛 STAGE: Bug Detection - SKIPPED (Disabled)")
            print("=" * 80)
            state['bug_review'] = {
                "stage": "bugs",
                "findings": [],
                "summary": "Skipped: Stage disabled by user",
                "status": "skipped"
            }
            state['status'] = 'Bug detection skipped'
            return state

        try:
            print("=" * 80)
            print("🐛 STAGE: Bug Detection - START")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Running AI bug detection (checking for logic errors)', 60)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                bug_review, token_usage = self.review_agents.bug_detection(files_changed)
                state['bug_review'] = bug_review
                state['token_usage']['bugs'] = token_usage
                state['status'] = 'Bug detection completed'
                state['messages'].append({"role": "system", "content": "Bug detection completed"})

            print("=" * 80)
            print("🐛 STAGE: Bug Detection - END")
            print("=" * 80)
        except Exception as e:
            state['bug_review'] = {
                "stage": "bugs",
                "findings": [],
                "summary": f"Error during bug detection: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
            state['status'] = f'Error in bug detection: {str(e)}'
            print("=" * 80)
            print(f"🐛 STAGE: Bug Detection - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def style_check_node(self, state: ReviewState) -> ReviewState:
        """Node for style and optimization review"""
        # Check if this stage is enabled
        if hasattr(self, 'enabled_stages') and not self.enabled_stages.get('style', True):
            print("=" * 80)
            print("✨ STAGE: Style & Optimization - SKIPPED (Disabled)")
            print("=" * 80)
            state['style_review'] = {
                "stage": "style",
                "findings": [],
                "summary": "Skipped: Stage disabled by user",
                "status": "skipped"
            }
            state['status'] = 'Style review skipped'
            return state

        try:
            print("=" * 80)
            print("✨ STAGE: Style & Optimization - START")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Running AI code quality analysis (checking style & optimization)', 75)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                style_review, token_usage = self.review_agents.style_and_optimization(files_changed)
                state['style_review'] = style_review
                state['token_usage']['style'] = token_usage
                state['status'] = 'Style and optimization review completed'
                state['messages'].append({"role": "system", "content": "Style review completed"})

            print("=" * 80)
            print("✨ STAGE: Style & Optimization - END")
            print("=" * 80)
        except Exception as e:
            state['style_review'] = {
                "stage": "style",
                "findings": [],
                "summary": f"Error during style review: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
            state['status'] = f'Error in style review: {str(e)}'
            print("=" * 80)
            print(f"✨ STAGE: Style & Optimization - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def performance_check_node(self, state: ReviewState) -> ReviewState:
        """Node for performance analysis"""
        # Check if this stage is enabled
        if hasattr(self, 'enabled_stages') and not self.enabled_stages.get('performance', True):
            print("=" * 80)
            print("⚡ STAGE: Performance Analysis - SKIPPED (Disabled)")
            print("=" * 80)
            state['performance_review'] = {
                "stage": "performance",
                "findings": [],
                "summary": "Skipped: Stage disabled by user",
                "status": "skipped"
            }
            state['status'] = 'Performance analysis skipped'
            return state

        try:
            print("=" * 80)
            print("⚡ STAGE: Performance Analysis - START")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Running AI performance analysis (identifying bottlenecks)', 82)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                performance_review, token_usage = self.review_agents.performance_analysis(files_changed)
                state['performance_review'] = performance_review
                state['token_usage']['performance'] = token_usage
                state['status'] = 'Performance analysis completed'
                state['messages'].append({"role": "system", "content": "Performance analysis completed"})

            print("=" * 80)
            print("⚡ STAGE: Performance Analysis - END")
            print("=" * 80)
        except Exception as e:
            state['performance_review'] = {
                "stage": "performance",
                "findings": [],
                "summary": f"Error during performance analysis: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
            state['status'] = f'Error in performance analysis: {str(e)}'
            print("=" * 80)
            print(f"⚡ STAGE: Performance Analysis - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def test_check_node(self, state: ReviewState) -> ReviewState:
        """Node for unit test suggestions"""
        # Check if this stage is enabled
        if hasattr(self, 'enabled_stages') and not self.enabled_stages.get('tests', True):
            print("=" * 80)
            print("🧪 STAGE: Test Suggestions - SKIPPED (Disabled)")
            print("=" * 80)
            state['test_suggestions'] = {
                "stage": "tests",
                "findings": [],
                "summary": "Skipped: Stage disabled by user",
                "status": "skipped"
            }
            state['status'] = 'Test suggestions skipped'
            return state

        try:
            print("=" * 80)
            print("🧪 STAGE: Test Suggestions - START")
            print("=" * 80)

            if self.progress_callback:
                self.progress_callback('Running AI test analysis (generating test suggestions)', 88)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                test_suggestions, token_usage = self.review_agents.unit_test_suggestions(files_changed)
                state['test_suggestions'] = test_suggestions
                state['token_usage']['tests'] = token_usage
                state['status'] = 'Unit test suggestions completed'
                state['messages'].append({"role": "system", "content": "Test suggestions completed"})

            print("=" * 80)
            print("🧪 STAGE: Test Suggestions - END")
            print("=" * 80)
        except Exception as e:
            state['test_suggestions'] = {
                "stage": "tests",
                "findings": [],
                "summary": f"Error during test suggestions: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
            state['status'] = f'Error in test suggestions: {str(e)}'
            print("=" * 80)
            print(f"🧪 STAGE: Test Suggestions - ERROR: {str(e)}")
            print("=" * 80)

        return state

    def summarize_node(self, state: ReviewState) -> ReviewState:
        """Node to create final summary"""
        print("=" * 80)
        print("📋 STAGE: Finalize Review - START")
        print("=" * 80)

        if self.progress_callback:
            self.progress_callback('Finalizing review report', 95)

        state['status'] = 'Review completed successfully'
        state['messages'].append({"role": "system", "content": "All reviews completed successfully"})

        # Calculate total tokens used
        token_usage_data = state.get('token_usage', {})
        total_tokens = 0
        for stage, usage in token_usage_data.items():
            if isinstance(usage, dict):
                total_tokens += usage.get('total_tokens', 0)
            elif isinstance(usage, int):
                total_tokens += usage

        print("=" * 80)
        print("📋 STAGE: Finalize Review - END")
        print(f"   Status: {state['status']}")
        print(f"   Total Tokens Used: {total_tokens:,}")
        print("=" * 80)
        print()
        print("✅ CODE REVIEW WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)

        return state

    def run(self, pr_url: str, repo_url: str, analyze_target_branch: bool = False, enabled_stages: dict = None) -> ReviewState:
        """Execute the review workflow

        Args:
            pr_url: Pull/Merge request URL
            repo_url: Repository URL
            analyze_target_branch: Whether to analyze target branch
            enabled_stages: Dict of enabled stages {'security': bool, 'bugs': bool, 'style': bool, 'tests': bool}
        """
        if enabled_stages is None:
            enabled_stages = {'security': True, 'bugs': True, 'style': True, 'tests': True}

        # Store enabled stages for use in node functions
        self.enabled_stages = enabled_stages

        initial_state = ReviewState(
            pr_url=pr_url,
            repo_url=repo_url,
            pr_details={},
            repo_path="",
            analyze_target_branch=analyze_target_branch,
            target_branch_analysis=None,
            security_review={"stage": "security", "findings": [], "summary": "", "status": "pending"},
            bug_review={"stage": "bugs", "findings": [], "summary": "", "status": "pending"},
            style_review={"stage": "style", "findings": [], "summary": "", "status": "pending"},
            performance_review={"stage": "performance", "findings": [], "summary": "", "status": "pending"},
            test_suggestions={"stage": "tests", "findings": [], "summary": "", "status": "pending"},
            messages=[],
            status="Starting review",
            token_usage={
                'security': {},
                'bugs': {},
                'style': {},
                'performance': {},
                'tests': {}
            }
        )

        result = self.workflow.invoke(initial_state)
        return result
