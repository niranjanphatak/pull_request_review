from typing import TypedDict, Annotated, Optional
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
    security_review: str
    bug_review: str
    style_review: str
    test_suggestions: str
    messages: Annotated[list, add_messages]
    status: str


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
        workflow.add_node("security_check", self.security_check_node)
        workflow.add_node("bug_check", self.bug_check_node)
        workflow.add_node("style_check", self.style_check_node)
        workflow.add_node("test_check", self.test_check_node)
        workflow.add_node("summarize", self.summarize_node)

        # Define workflow edges
        workflow.set_entry_point("fetch_pr")
        workflow.add_edge("fetch_pr", "clone_repo")
        workflow.add_edge("clone_repo", "security_check")
        workflow.add_edge("security_check", "bug_check")
        workflow.add_edge("bug_check", "style_check")
        workflow.add_edge("style_check", "test_check")
        workflow.add_edge("test_check", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    def fetch_pr_node(self, state: ReviewState) -> ReviewState:
        """Node to fetch PR/MR details"""
        try:
            if self.progress_callback:
                self.progress_callback('Fetching PR/MR details', 10)

            pr_details = self.gitlab_helper.get_mr_details(state['pr_url'])
            state['pr_details'] = pr_details
            state['status'] = 'PR details fetched successfully'
            state['messages'] = [{"role": "system", "content": f"Fetched PR: {pr_details['title']}"}]
        except Exception as e:
            state['status'] = f'Error fetching PR: {str(e)}'
            state['messages'] = [{"role": "system", "content": f"Error: {str(e)}"}]

        return state

    def clone_repo_node(self, state: ReviewState) -> ReviewState:
        """Node to clone repository"""
        try:
            if self.progress_callback:
                self.progress_callback('Cloning repository (this may take a moment)', 20)

            repo_path = self.gitlab_helper.clone_repository(state['repo_url'])
            state['repo_path'] = repo_path
            state['status'] = 'Repository cloned successfully'
            state['messages'].append({"role": "system", "content": f"Cloned repository to {repo_path}"})
        except Exception as e:
            state['status'] = f'Error cloning repository: {str(e)}'
            state['messages'].append({"role": "system", "content": f"Error: {str(e)}"})

        return state

    def security_check_node(self, state: ReviewState) -> ReviewState:
        """Node for security review"""
        try:
            if self.progress_callback:
                self.progress_callback('Running AI security analysis (analyzing vulnerabilities)', 35)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                security_review = self.review_agents.security_review(files_changed)
                state['security_review'] = security_review
                state['status'] = 'Security review completed'
                state['messages'].append({"role": "system", "content": "Security review completed"})
        except Exception as e:
            state['security_review'] = f'Error during security review: {str(e)}'
            state['status'] = f'Error in security review: {str(e)}'

        return state

    def bug_check_node(self, state: ReviewState) -> ReviewState:
        """Node for bug detection"""
        try:
            if self.progress_callback:
                self.progress_callback('Running AI bug detection (checking for logic errors)', 55)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                bug_review = self.review_agents.bug_detection(files_changed)
                state['bug_review'] = bug_review
                state['status'] = 'Bug detection completed'
                state['messages'].append({"role": "system", "content": "Bug detection completed"})
        except Exception as e:
            state['bug_review'] = f'Error during bug detection: {str(e)}'
            state['status'] = f'Error in bug detection: {str(e)}'

        return state

    def style_check_node(self, state: ReviewState) -> ReviewState:
        """Node for style and optimization review"""
        try:
            if self.progress_callback:
                self.progress_callback('Running AI code quality analysis (checking style & optimization)', 70)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                style_review = self.review_agents.style_and_optimization(files_changed)
                state['style_review'] = style_review
                state['status'] = 'Style and optimization review completed'
                state['messages'].append({"role": "system", "content": "Style review completed"})
        except Exception as e:
            state['style_review'] = f'Error during style review: {str(e)}'
            state['status'] = f'Error in style review: {str(e)}'

        return state

    def test_check_node(self, state: ReviewState) -> ReviewState:
        """Node for unit test suggestions"""
        try:
            if self.progress_callback:
                self.progress_callback('Running AI test analysis (generating test suggestions)', 85)

            if 'pr_details' in state and state['pr_details']:
                files_changed = state['pr_details']['files_changed']
                test_suggestions = self.review_agents.unit_test_suggestions(files_changed)
                state['test_suggestions'] = test_suggestions
                state['status'] = 'Unit test suggestions completed'
                state['messages'].append({"role": "system", "content": "Test suggestions completed"})
        except Exception as e:
            state['test_suggestions'] = f'Error during test suggestions: {str(e)}'
            state['status'] = f'Error in test suggestions: {str(e)}'

        return state

    def summarize_node(self, state: ReviewState) -> ReviewState:
        """Node to create final summary"""
        if self.progress_callback:
            self.progress_callback('Finalizing review report', 95)

        state['status'] = 'Review completed successfully'
        state['messages'].append({"role": "system", "content": "All reviews completed successfully"})
        return state

    def run(self, pr_url: str, repo_url: str) -> ReviewState:
        """Execute the review workflow"""
        initial_state = ReviewState(
            pr_url=pr_url,
            repo_url=repo_url,
            pr_details={},
            repo_path="",
            security_review="",
            bug_review="",
            style_review="",
            test_suggestions="",
            messages=[],
            status="Starting review"
        )

        result = self.workflow.invoke(initial_state)
        return result
