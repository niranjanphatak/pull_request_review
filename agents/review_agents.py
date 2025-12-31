from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional
import os


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
        """Load all prompt templates from files and track versions"""
        prompts = {}
        prompt_files = {
            'security': 'security_review.txt',
            'bugs': 'bug_detection.txt',
            'style': 'style_optimization.txt',
            'performance': 'performance_analysis.txt',
            'tests': 'test_suggestions.txt'
        }

        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    prompt_content = f.read().strip()
                    prompts[key] = prompt_content

                    # Try to get version info from MongoDB
                    try:
                        from utils.session_storage import SessionStorage
                        storage = SessionStorage()
                        if storage.connected:
                            prompt_version = storage.get_prompt_version(key)
                            if prompt_version:
                                self.prompt_versions[key] = {
                                    'version': prompt_version.get('version', '1.0.0'),
                                    'description': prompt_version.get('description', ''),
                                    'criteria': prompt_version.get('criteria', [])
                                }
                            else:
                                # No version in DB, use default
                                self.prompt_versions[key] = {
                                    'version': '1.0.0',
                                    'description': 'Code review analysis',
                                    'criteria': []
                                }
                            storage.close()
                    except Exception as e:
                        # If version lookup fails, use defaults
                        self.prompt_versions[key] = {
                            'version': '1.0.0',
                            'description': 'Code review analysis',
                            'criteria': []
                        }

            except FileNotFoundError:
                # Fallback to default prompts if file not found
                prompts[key] = self._get_default_prompt(key)
                self.prompt_versions[key] = {
                    'version': '1.0.0',
                    'description': 'Default prompt',
                    'criteria': []
                }

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

    def security_review(self, code_changes: List[Dict]) -> tuple[str, Dict]:
        """Agent for security vulnerability analysis

        Returns:
            tuple: (review_content, token_usage_dict)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['security']),
            ("user", "Review these code changes for security issues:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)", {}

            # Extract token usage from response metadata
            token_usage = self._extract_token_usage(result)
            return result.content, token_usage
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour API quota has been exhausted. Please:\n1. Wait for your quota to reset\n2. Check your API provider's usage dashboard\n3. Upgrade your API plan if needed\n4. Use a different API key\n\nError: {error_msg[:300]}", {}
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}", {}
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}", {}
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}", {}

    def bug_detection(self, code_changes: List[Dict]) -> tuple[str, Dict]:
        """Agent for potential bug detection

        Returns:
            tuple: (review_content, token_usage_dict)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['bugs']),
            ("user", "Review these code changes for potential bugs:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)", {}

            # Extract token usage from response metadata
            token_usage = self._extract_token_usage(result)
            return result.content, token_usage
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour API quota has been exhausted. Please:\n1. Wait for your quota to reset\n2. Check your API provider's usage dashboard\n3. Upgrade your API plan if needed\n4. Use a different API key\n\nError: {error_msg[:300]}", {}
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}", {}
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}", {}
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}", {}

    def style_and_optimization(self, code_changes: List[Dict]) -> tuple[str, Dict]:
        """Agent for code style and optimization suggestions

        Returns:
            tuple: (review_content, token_usage_dict)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['style']),
            ("user", "Review these code changes for style and optimization:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)", {}

            # Extract token usage from response metadata
            token_usage = self._extract_token_usage(result)
            return result.content, token_usage
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour API quota has been exhausted. Please:\n1. Wait for your quota to reset\n2. Check your API provider's usage dashboard\n3. Upgrade your API plan if needed\n4. Use a different API key\n\nError: {error_msg[:300]}", {}
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}", {}
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}", {}
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}", {}

    def performance_analysis(self, code_changes: List[Dict]) -> tuple[str, Dict]:
        """Agent for performance analysis and optimization

        Returns:
            tuple: (review_content, token_usage_dict)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['performance']),
            ("user", "Analyze these code changes for performance issues:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)", {}

            # Extract token usage from response metadata
            token_usage = self._extract_token_usage(result)
            return result.content, token_usage
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour API quota has been exhausted. Please:\n1. Wait for your quota to reset\n2. Check your API provider's usage dashboard\n3. Upgrade your API plan if needed\n4. Use a different API key\n\nError: {error_msg[:300]}", {}
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}", {}
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}", {}
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}", {}

    def unit_test_suggestions(self, code_changes: List[Dict]) -> tuple[str, Dict]:
        """Agent for unit test recommendations

        Returns:
            tuple: (review_content, token_usage_dict)
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['tests']),
            ("user", "Suggest unit tests for these code changes:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)", {}

            # Extract token usage from response metadata
            token_usage = self._extract_token_usage(result)
            return result.content, token_usage
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour API quota has been exhausted. Please:\n1. Wait for your quota to reset\n2. Check your API provider's usage dashboard\n3. Upgrade your API plan if needed\n4. Use a different API key\n\nError: {error_msg[:300]}", {}
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}", {}
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}", {}
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}", {}

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
