from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Union
import os


class ReviewAgents:
    """Collection of specialized review agents returning text-based (markdown) results"""

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
        prompt_files = {
            'security': 'security_review.txt',
            'bugs': 'bug_detection.txt',
            'style': 'style_optimization.txt',
            'tests': 'test_suggestions.txt'
        }
        prompt_stages = list(prompt_files.keys())

        for key in prompt_stages:
            prompt_content = None
            
            # 1. Try to get prompt from Database (Factory)
            try:
                from utils.database_factory import create_database
                storage = create_database()
                if storage and storage.connected:
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
            'security': "You are an expert security analyst. Review the code for security vulnerabilities. Provide a clear, professional markdown report.",
            'bugs': "You are an expert at finding bugs. Review the code for potential bugs and logic errors. Provide a clear, professional markdown report.",
            'style': "You are an expert code reviewer. Review the code for style and optimization opportunities. Provide a clear, professional markdown report.",
            'tests': "You are an expert in testing. Suggest comprehensive unit tests for the code. Provide a clear, professional markdown report."
        }
        return defaults.get(prompt_type, "Review the provided code changes.")

    def get_prompt_versions(self) -> Dict[str, Dict]:
        """
        Get version information for all loaded prompts

        Returns:
            Dictionary mapping stage names to version info
        """
        return self.prompt_versions

    def _run_stage_review(self, stage: str, user_prompt: str, code_changes: List[Dict]) -> tuple[Dict, Dict]:
        """Generic method to run a review stage and return standardized text-based result"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts.get(stage, "Review the code changes.")),
            ("user", f"{user_prompt}:\n\n{{code_changes}}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"code_changes": self._format_code_changes(code_changes)})
            content = result.content if result.content else "No substantial findings for this stage."
            token_usage = self._extract_token_usage(result)
            
            return {
                "stage": stage,
                "summary": content,
                "status": "success"
            }, token_usage
        except Exception as e:
            return {
                "stage": stage,
                "summary": f"Failed to perform {stage} review: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }, {}

    def security_review(self, code_changes: List[Dict]) -> tuple[Dict, Dict]:
        return self._run_stage_review("security", "Review these code changes for security issues", code_changes)

    def bug_detection(self, code_changes: List[Dict]) -> tuple[Dict, Dict]:
        return self._run_stage_review("bugs", "Review these code changes for potential bugs", code_changes)

    def style_and_optimization(self, code_changes: List[Dict]) -> tuple[Dict, Dict]:
        return self._run_stage_review("style", "Review these code changes for style and optimization", code_changes)



    def unit_test_suggestions(self, code_changes: List[Dict]) -> tuple[Dict, Dict]:
        return self._run_stage_review("tests", "Suggest unit tests for these code changes", code_changes)

    def _extract_token_usage(self, result) -> Dict:
        """Extract token usage from LLM response metadata"""
        token_usage = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }

        try:
            if hasattr(result, 'response_metadata'):
                usage = result.response_metadata.get('token_usage', {})
                token_usage['prompt_tokens'] = usage.get('prompt_tokens', 0)
                token_usage['completion_tokens'] = usage.get('completion_tokens', 0)
                token_usage['total_tokens'] = usage.get('total_tokens', 0)

            elif hasattr(result, 'usage_metadata'):
                usage = result.usage_metadata
                token_usage['prompt_tokens'] = getattr(usage, 'input_tokens', 0)
                token_usage['completion_tokens'] = getattr(usage, 'output_tokens', 0)
                token_usage['total_tokens'] = token_usage['prompt_tokens'] + token_usage['completion_tokens']
        except Exception as e:
            print(f"Warning: Could not extract token usage: {e}")

        return token_usage

    def _format_code_changes(self, code_changes: List[Dict]) -> str:
        """Format code changes for LLM consumption"""
        formatted = []
        for file_change in code_changes:
            formatted.append(f"\n{'='*80}")
            formatted.append(f"📄 File: {file_change.get('filename', 'Unknown')}")
            status = file_change.get('status', 'modified')
            formatted.append(f"Status: {status.upper()}")
            
            diff_content = file_change.get('diff') or file_change.get('patch')
            if diff_content:
                formatted.append("📋 DIFF:")
                formatted.append(diff_content)
            else:
                formatted.append("⚠️  No diff content available")
            formatted.append("")

        return "\n".join(formatted)
