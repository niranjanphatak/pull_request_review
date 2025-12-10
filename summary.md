# PR Review System - Data Transmission Summary

## Overview

This document details exactly what data is sent to your AI provider during the PR review process.

## Data Sent to AI Provider

### 1. System Prompts (Instructions)

Each review agent receives specialized system prompts from the `prompts/` directory:

- **Security Review** (`prompts/security_review.txt`): Instructions to analyze for SQL injection, XSS, authentication issues, hardcoded secrets, command injection, path traversal, CORS misconfigurations, etc.

- **Bug Detection** (`prompts/bug_detection.txt`): Instructions to find logic errors, null pointers, race conditions, memory leaks, off-by-one errors, resource leaks, edge case issues, etc.

- **Style & Optimization** (`prompts/style_optimization.txt`): Instructions to review code quality, naming conventions, performance optimization, algorithm efficiency, best practices, DRY violations, design patterns, etc.

- **Test Suggestions** (`prompts/test_suggestions.txt`): Instructions to suggest unit tests, edge cases, error handling tests, mock requirements, integration tests, and test coverage gaps.

### 2. PR Metadata (NOT Sent to AI)

The following PR information is fetched from GitHub but **NOT sent to AI** (stored only in MongoDB for display):

- PR title
- PR description
- Author username
- PR state (open/closed)
- Created/updated timestamps
- Base and head branch names
- Total additions/deletions count
- Number of commits
- Diff URL

### 3. Code Changes (Sent to AI)

For **each file changed** in the PR, the following data is sent:

```python
{
    'filename': 'path/to/file.js',
    'status': 'modified',  # or 'added', 'deleted', 'renamed'
    'additions': 45,
    'deletions': 12,
    'patch': '...'  # The actual git diff content
}
```

### 4. Formatted AI Request

The data is formatted as follows before sending to AI:

```
================================================================================
File: src/components/UserAuth.js
Status: modified
Changes: +45 -12
================================================================================

@@ -10,7 +10,10 @@ class UserAuth {
   async login(username, password) {
-    const query = `SELECT * FROM users WHERE username='${username}'`;
+    const query = 'SELECT * FROM users WHERE username=?';
+    const params = [username];
     // ... rest of the diff
   }
}

================================================================================
File: src/utils/api.js
Status: added
Changes: +32 -0
================================================================================

@@ -0,0 +1,32 @@
+export async function fetchData(endpoint) {
+  // ... new file content
+}
```

### 5. Complete AI Request Structure

Each AI request contains two messages:

**System Message:**
```
You are an expert security analyst reviewing code for vulnerabilities.

Your task is to perform a comprehensive security analysis of the provided code changes.

## Focus Areas:
- SQL injection vulnerabilities
- Cross-Site Scripting (XSS) risks
- Authentication/Authorization issues
[...full prompt from prompts/security_review.txt...]
```

**User Message:**
```
Review these code changes for security issues:

================================================================================
File: src/components/UserAuth.js
Status: modified
Changes: +45 -12
================================================================================
[...actual git diff patch...]

================================================================================
File: src/utils/api.js
Status: added
Changes: +32 -0
================================================================================
[...actual git diff patch...]
```

### 6. What is NOT Sent

The following information is **NOT** sent to the AI:

- ❌ Full file contents (only the diff/patch showing changes)
- ❌ PR description or comments
- ❌ Author information
- ❌ Repository names or URLs
- ❌ Timestamps
- ❌ Binary files (marked as "(Binary file or no patch available)")
- ❌ Any credentials or tokens
- ❌ Commit messages
- ❌ Review comments from other developers

### 7. API Configuration

The AI client is configured with:

```python
{
    "api_key": AI_API_KEY,           # From .env file
    "model": AI_MODEL,                # Default: "gemini-2.5-flash-lite"
    "temperature": AI_TEMPERATURE,    # Default: 0.1
    "base_url": AI_BASE_URL          # Default: Gemini API endpoint
}
```

## Summary Table

| Data Type | Sent to AI | Purpose |
|-----------|-----------|---------|
| System prompts | ✅ Yes | Instructions for review |
| File paths | ✅ Yes | Identify files being reviewed |
| File status (modified/added/deleted) | ✅ Yes | Context for changes |
| Line counts (+/-) | ✅ Yes | Scope of changes |
| Git diff patches | ✅ Yes | Actual code changes |
| Full file contents | ❌ No | Only diffs sent |
| PR title/description | ❌ No | Not needed for code review |
| Author information | ❌ No | Privacy |
| Repository URLs | ❌ No | Privacy |
| Binary files | ❌ No | Cannot be analyzed |
| Credentials/tokens | ❌ No | Security |

## Privacy & Security

- **Minimal Data**: Only code diffs are sent, not entire files
- **No Metadata**: PR descriptions, author names, and repo URLs are not sent
- **No Credentials**: All tokens and API keys are stripped
- **Binary Files Excluded**: Binary files are not transmitted
- **Context-Only**: Only changed lines + surrounding context (typically 3 lines)

## AI Provider Compatibility

The system works with any OpenAI-compatible AI provider:
- Google Gemini (default)
- OpenAI GPT models
- Anthropic Claude
- Azure OpenAI
- Custom AI endpoints

All providers receive the same formatted data structure.
