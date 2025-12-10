from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional
import os


class ReviewAgents:
    """Collection of specialized review agents with external prompt files"""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        prompts_dir: str = "prompts"
    ):
        """
        Initialize review agents with flexible AI provider configuration

        Args:
            api_key: API key for the AI provider
            model: Model name (e.g., "gemini-2.5-flash-lite", "gpt-4", custom model names)
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
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load all prompt templates from files"""
        prompts = {}
        prompt_files = {
            'security': 'security_review.txt',
            'bug': 'bug_detection.txt',
            'style': 'style_optimization.txt',
            'test': 'test_suggestions.txt'
        }

        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    prompts[key] = f.read().strip()
            except FileNotFoundError:
                # Fallback to default prompts if file not found
                prompts[key] = self._get_default_prompt(key)

        return prompts

    def _get_default_prompt(self, prompt_type: str) -> str:
        """Fallback prompts if files are not found"""
        defaults = {
            'security': "You are an expert security analyst. Review the code for security vulnerabilities.",
            'bug': "You are an expert at finding bugs. Review the code for potential bugs and logic errors.",
            'style': "You are an expert code reviewer. Review the code for style and optimization opportunities.",
            'test': "You are an expert in testing. Suggest comprehensive unit tests for the code."
        }
        return defaults.get(prompt_type, "Review the provided code changes.")

    def security_review(self, code_changes: List[Dict]) -> str:
        """Agent for security vulnerability analysis"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['security']),
            ("user", "Review these code changes for security issues:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)"
            return result.content
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour free tier quota is exhausted. Please:\n1. Wait for quota reset (check https://ai.dev/usage)\n2. Get a new API key from a different Google account\n3. Enable billing at https://aistudio.google.com/app/billing\n\nError: {error_msg[:300]}"
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}"
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}"
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}"

    def bug_detection(self, code_changes: List[Dict]) -> str:
        """Agent for potential bug detection"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['bug']),
            ("user", "Review these code changes for potential bugs:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)"
            return result.content
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour free tier quota is exhausted. Please:\n1. Wait for quota reset (check https://ai.dev/usage)\n2. Get a new API key from a different Google account\n3. Enable billing at https://aistudio.google.com/app/billing\n\nError: {error_msg[:300]}"
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}"
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}"
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}"

    def style_and_optimization(self, code_changes: List[Dict]) -> str:
        """Agent for code style and optimization suggestions"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['style']),
            ("user", "Review these code changes for style and optimization:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)"
            return result.content
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour free tier quota is exhausted. Please:\n1. Wait for quota reset (check https://ai.dev/usage)\n2. Get a new API key from a different Google account\n3. Enable billing at https://aistudio.google.com/app/billing\n\nError: {error_msg[:300]}"
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}"
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}"
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}"

    def unit_test_suggestions(self, code_changes: List[Dict]) -> str:
        """Agent for unit test recommendations"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts['test']),
            ("user", "Suggest unit tests for these code changes:\n\n{code_changes}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            if not result.content:
                return "⚠️ Warning: Received empty response from AI. This may indicate an API issue (quota exceeded, rate limit, etc.)"
            return result.content
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__

            # Get more details from the exception
            full_error = f"{error_type}: {error_msg}"

            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                return f"❌ API Quota Exceeded\n\nYour free tier quota is exhausted. Please:\n1. Wait for quota reset (check https://ai.dev/usage)\n2. Get a new API key from a different Google account\n3. Enable billing at https://aistudio.google.com/app/billing\n\nError: {error_msg[:300]}"
            elif "403" in error_msg or "permission" in error_msg.lower() or "PERMISSION_DENIED" in error_msg:
                return f"❌ API Permission Denied\n\nYour API key may be invalid, revoked, or reported as leaked.\n\nError: {error_msg[:300]}"
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return f"❌ Model Not Found\n\nThe model may not be available. Error: {error_msg[:300]}"
            else:
                return f"❌ API Error ({error_type})\n\nFull error:\n{full_error[:500]}"

    def _format_code_changes(self, code_changes: List[Dict]) -> str:
        """Format code changes for LLM consumption"""
        formatted = []

        for file_change in code_changes:
            formatted.append(f"\n{'='*80}")
            formatted.append(f"File: {file_change.get('filename', 'Unknown')}")

            # Optional fields
            if 'status' in file_change:
                formatted.append(f"Status: {file_change['status']}")
            if 'additions' in file_change and 'deletions' in file_change:
                formatted.append(f"Changes: +{file_change['additions']} -{file_change['deletions']}")

            formatted.append(f"{'='*80}\n")

            if file_change.get('patch'):
                formatted.append(file_change['patch'])
            else:
                formatted.append("(Binary file or no patch available)")

        return "\n".join(formatted)
