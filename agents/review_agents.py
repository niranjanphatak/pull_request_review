from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Union
import os
from agents.models import ReviewStageResult, ReviewFinding


class ReviewAgents:
    """Collection of specialized review agents with external prompt files"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        prompts_dir: str = "prompts"
    ):
        """
        Initialize review agents with flexible AI provider configuration

        Args:
            api_key: API key for the AI provider
            model: Model name (e.g., "claude-3-5-sonnet-20241022", "gpt-4o-mini", custom model names)
            base_url: Optional base URL for custom AI endpoints
            temperature: Temperature for LLM responses (0.0-1.0)
            prompts_dir: Directory containing prompt files
        """
        llm_kwargs = {
            "api_key": api_key,
            "model": model,
            "temperature": temperature
        }

        # Add base_url if provided for custom AI endpoints
        if base_url:
            llm_kwargs["base_url"] = base_url

        self.llm = ChatOpenAI(**llm_kwargs)
        self.prompts_dir = prompts_dir
        self.prompt_versions = {}  # Track which version was loaded for each stage (must be before _load_prompts)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load all prompt templates, prioritizing MongoDB over file system"""
        prompts = {}
        prompt_stages = ['security', 'bugs', 'style', 'performance', 'tests']
        
        prompt_files = {
            'security': 'security_review.txt',
            'bugs': 'bug_detection.txt',
            'style': 'style_optimization.txt',
            'performance': 'performance_analysis.txt',
            'tests': 'test_suggestions.txt'
        }

        for key in prompt_stages:
            prompt_content = None
            
            # 1. Try to get prompt from MongoDB
            try:
                from utils.session_storage import SessionStorage
                storage = SessionStorage()
                if storage.connected:
                    prompt_version = storage.get_prompt_version(key)
                    if prompt_version:
                        prompt_content = prompt_version.get('prompt_content')
                        self.prompt_versions[key] = {
                            'version': prompt_version.get('version', '1.0.0'),
                            'description': prompt_version.get('description', ''),
                            'criteria': prompt_version.get('criteria', []),
                            'timestamp': prompt_version.get('timestamp'),
                            'from_db': True
                        }
                storage.close()
            except Exception as e:
                print(f"Warning: Could not load prompt version from DB for {key}: {e}")

            # 2. If not in DB, try to load from file
            if not prompt_content:
                filename = prompt_files.get(key)
                if filename:
                    filepath = os.path.join(self.prompts_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            prompt_content = f.read().strip()
                            self.prompt_versions[key] = {
                                'version': '1.0.0',
                                'description': 'Loaded from file system',
                                'criteria': [],
                                'from_db': False
                            }
                    except FileNotFoundError:
                        pass

            # 3. Last fallback: default prompt
            if not prompt_content:
                prompt_content = self._get_default_prompt(key)
                self.prompt_versions[key] = {
                    'version': '1.0.0',
                    'description': 'Default internal prompt',
                    'criteria': [],
                    'from_db': False
                }
            
            prompts[key] = prompt_content

        return prompts

    def _get_default_prompt(self, prompt_type: str) -> str:
        """Fallback prompts if files are not found"""
        defaults = {
            'security': "You are an expert security analyst. Review the code for security vulnerabilities.",
            'bugs': "You are an expert at finding bugs. Review the code for potential bugs and logic errors.",
            'style': "You are an expert code reviewer. Review the code for style and optimization opportunities.",
            'performance': "You are an expert performance analyst. Identify performance bottlenecks and optimization opportunities.",
            'tests': "You are an expert in testing. Suggest comprehensive unit tests for the code."
        }
        return defaults.get(prompt_type, "Review the provided code changes.")

    def get_prompt_versions(self) -> Dict[str, Dict]:
        """
        Get version information for all loaded prompts

        Returns:
            Dictionary mapping stage names to version info
        """
        return self.prompt_versions

    def security_review(self, code_changes: List[Dict]) -> tuple[Union[str, Dict], Dict]:
        """Agent for security vulnerability analysis

        Returns:
            tuple: (review_stage_result_dict, token_usage_dict)
        """
        # Try structured output first
        try:
            structured_llm = self.llm.with_structured_output(ReviewStageResult)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['security'] + "\n\nYou MUST provide your response in the specified structured format."),
                ("user", "Review these code changes for security issues:\n\n{code_changes}")
            ])

            chain = prompt | structured_llm
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            
            # Extract token usage - unfortunately structured_output might not return metadata easily
            # We'll use a dummy usage for now or try to get it from the non-structured call if needed
            # For simplicity, let's try to get usage if possible
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            
            return result.model_dump(), token_usage
        except Exception as e:
            print(f"Structured security review failed: {e}. Falling back to text.")
            # Fallback to text output if structured fails
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['security']),
                ("user", "Review these code changes for security issues:\n\n{code_changes}")
            ])

            chain = prompt | self.llm
            try:
                result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
                if not result.content:
                    return {"stage": "security", "findings": [], "summary": "Empty response from AI", "status": "error", "error_message": "Empty response"}, {}

                token_usage = self._extract_token_usage(result)
                # Wrap text response in structured format
                return {
                    "stage": "security",
                    "findings": [],
                    "summary": result.content,
                    "status": "success"
                }, token_usage
            except Exception as e:
                return {"stage": "security", "findings": [], "summary": str(e), "status": "error", "error_message": str(e)}, {}

    def bug_detection(self, code_changes: List[Dict]) -> tuple[Union[str, Dict], Dict]:
        """Agent for potential bug detection

        Returns:
            tuple: (review_stage_result_dict, token_usage_dict)
        """
        try:
            structured_llm = self.llm.with_structured_output(ReviewStageResult)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['bugs'] + "\n\nYou MUST provide your response in the specified structured format."),
                ("user", "Review these code changes for potential bugs:\n\n{code_changes}")
            ])

            chain = prompt | structured_llm
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            return result.model_dump(), token_usage
        except Exception as e:
            print(f"Structured bug detection failed: {e}. Falling back to text.")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['bugs']),
                ("user", "Review these code changes for potential bugs:\n\n{code_changes}")
            ])

            chain = prompt | self.llm
            try:
                result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
                if not result.content:
                    return {"stage": "bugs", "findings": [], "summary": "Empty response from AI", "status": "error", "error_message": "Empty response"}, {}

                token_usage = self._extract_token_usage(result)
                return {
                    "stage": "bugs",
                    "findings": [],
                    "summary": result.content,
                    "status": "success"
                }, token_usage
            except Exception as e:
                return {"stage": "bugs", "findings": [], "summary": str(e), "status": "error", "error_message": str(e)}, {}

    def style_and_optimization(self, code_changes: List[Dict]) -> tuple[Union[str, Dict], Dict]:
        """Agent for code style and optimization suggestions

        Returns:
            tuple: (review_stage_result_dict, token_usage_dict)
        """
        try:
            structured_llm = self.llm.with_structured_output(ReviewStageResult)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['style'] + "\n\nYou MUST provide your response in the specified structured format."),
                ("user", "Review these code changes for style and optimization:\n\n{code_changes}")
            ])

            chain = prompt | structured_llm
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            return result.model_dump(), token_usage
        except Exception as e:
            print(f"Structured style review failed: {e}. Falling back to text.")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['style']),
                ("user", "Review these code changes for style and optimization:\n\n{code_changes}")
            ])

            chain = prompt | self.llm
            try:
                result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
                if not result.content:
                    return {"stage": "style", "findings": [], "summary": "Empty response from AI", "status": "error", "error_message": "Empty response"}, {}

                token_usage = self._extract_token_usage(result)
                return {
                    "stage": "style",
                    "findings": [],
                    "summary": result.content,
                    "status": "success"
                }, token_usage
            except Exception as e:
                return {"stage": "style", "findings": [], "summary": str(e), "status": "error", "error_message": str(e)}, {}

    def performance_analysis(self, code_changes: List[Dict]) -> tuple[Union[str, Dict], Dict]:
        """Agent for performance analysis and optimization

        Returns:
            tuple: (review_stage_result_dict, token_usage_dict)
        """
        try:
            structured_llm = self.llm.with_structured_output(ReviewStageResult)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['performance'] + "\n\nYou MUST provide your response in the specified structured format."),
                ("user", "Analyze these code changes for performance issues:\n\n{code_changes}")
            ])

            chain = prompt | structured_llm
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            return result.model_dump(), token_usage
        except Exception as e:
            print(f"Structured performance review failed: {e}. Falling back to text.")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['performance']),
                ("user", "Analyze these code changes for performance issues:\n\n{code_changes}")
            ])

            chain = prompt | self.llm
            try:
                result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
                if not result.content:
                    return {"stage": "performance", "findings": [], "summary": "Empty response from AI", "status": "error", "error_message": "Empty response"}, {}

                token_usage = self._extract_token_usage(result)
                return {
                    "stage": "performance",
                    "findings": [],
                    "summary": result.content,
                    "status": "success"
                }, token_usage
            except Exception as e:
                return {"stage": "performance", "findings": [], "summary": str(e), "status": "error", "error_message": str(e)}, {}

    def unit_test_suggestions(self, code_changes: List[Dict]) -> tuple[Union[str, Dict], Dict]:
        """Agent for unit test recommendations

        Returns:
            tuple: (review_stage_result_dict, token_usage_dict)
        """
        try:
            structured_llm = self.llm.with_structured_output(ReviewStageResult)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['tests'] + "\n\nYou MUST provide your response in the specified structured format."),
                ("user", "Suggest unit tests for these code changes:\n\n{code_changes}")
            ])

            chain = prompt | structured_llm
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            return result.model_dump(), token_usage
        except Exception as e:
            print(f"Structured test suggestions failed: {e}. Falling back to text.")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.prompts['tests']),
                ("user", "Suggest unit tests for these code changes:\n\n{code_changes}")
            ])

            chain = prompt | self.llm
            try:
                result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
                if not result.content:
                    return {"stage": "tests", "findings": [], "summary": "Empty response from AI", "status": "error", "error_message": "Empty response"}, {}

                token_usage = self._extract_token_usage(result)
                return {
                    "stage": "tests",
                    "findings": [],
                    "summary": result.content,
                    "status": "success"
                }, token_usage
            except Exception as e:
                return {"stage": "tests", "findings": [], "summary": str(e), "status": "error", "error_message": str(e)}, {}

    def _extract_token_usage(self, result) -> Dict:
        """Extract token usage from LLM response metadata

        Returns:
            Dict with keys: prompt_tokens, completion_tokens, total_tokens
        """
        token_usage = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }

        try:
            # Try to get usage info from response_metadata (OpenAI format)
            if hasattr(result, 'response_metadata'):
                usage = result.response_metadata.get('token_usage', {})
                token_usage['prompt_tokens'] = usage.get('prompt_tokens', 0)
                token_usage['completion_tokens'] = usage.get('completion_tokens', 0)
                token_usage['total_tokens'] = usage.get('total_tokens', 0)

            # Fallback: try usage_metadata (Anthropic format)
            elif hasattr(result, 'usage_metadata'):
                usage = result.usage_metadata
                token_usage['prompt_tokens'] = getattr(usage, 'input_tokens', 0)
                token_usage['completion_tokens'] = getattr(usage, 'output_tokens', 0)
                token_usage['total_tokens'] = token_usage['prompt_tokens'] + token_usage['completion_tokens']
        except Exception as e:
            print(f"Warning: Could not extract token usage: {e}")

        return token_usage

    def _format_code_changes(self, code_changes: List[Dict]) -> str:
        """
        Format code changes for LLM consumption in GitLab MR format

        Supports both GitLab and GitHub change formats and normalizes them
        for consistent LLM processing.
        """
        formatted = []

        for file_change in code_changes:
            # Header section with file information
            formatted.append(f"\n{'='*80}")
            formatted.append(f"📄 File: {file_change.get('filename', 'Unknown')}")

            # File status (GitLab: modified/added/removed, GitHub: modified/added/deleted)
            status = file_change.get('status', 'modified')
            status_icon = {
                'modified': '✏️ ',
                'added': '➕',
                'removed': '➖',
                'deleted': '➖',
                'renamed': '📝'
            }.get(status, '📝')
            formatted.append(f"Status: {status_icon} {status.upper()}")

            # Change statistics
            if 'additions' in file_change and 'deletions' in file_change:
                additions = file_change['additions']
                deletions = file_change['deletions']
                formatted.append(f"Changes: +{additions} lines added, -{deletions} lines removed")
            elif 'changes' in file_change:
                formatted.append(f"Changes: {file_change['changes']} total changes")

            # File type indicators (GitLab specific fields)
            flags = []
            if file_change.get('new_file'):
                flags.append('NEW FILE')
            if file_change.get('deleted_file'):
                flags.append('DELETED FILE')
            if file_change.get('renamed_file'):
                flags.append(f"RENAMED from {file_change.get('old_path', 'unknown')}")

            if flags:
                formatted.append(f"Flags: {', '.join(flags)}")

            formatted.append(f"{'='*80}\n")

            # Code diff section (prefer 'diff' field for GitLab, fall back to 'patch' for GitHub)
            diff_content = file_change.get('diff') or file_change.get('patch')

            if diff_content:
                formatted.append("📋 DIFF:")
                formatted.append(diff_content)
            else:
                # Handle binary files or files without diffs
                if file_change.get('binary'):
                    formatted.append("⚠️  Binary file - no diff available")
                else:
                    formatted.append("⚠️  No diff content available for this file")

            formatted.append("")  # Empty line between files

        # Add summary header
        summary_header = [
            "=" * 80,
            f"📊 MERGE REQUEST SUMMARY",
            f"Total files changed: {len(code_changes)}",
            "=" * 80,
            ""
        ]

        return "\n".join(summary_header + formatted)
