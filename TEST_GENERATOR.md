# Test Generator Feature

## Overview
A new feature that analyzes code repositories and optionally generates missing test cases using AI.

## Access
- **Menu**: Click "Test Generator" in the left sidebar
- **Direct URL**: `http://localhost:5000/static/test-generator.html`

## Features

### 📋 Repository Input Form
- **Git Repository URL**: Enter the full Git repository URL (e.g., `https://github.com/username/repo.git`)
- **Branch Name**: Specify the branch to analyze (defaults to `main`)
- **Generate Missing Test Cases**: Toggle checkbox to enable/disable AI-powered test generation

### 📊 Code Analysis Report

Displays comprehensive analysis of the repository:

#### Summary Cards
- **Total Files**: Count of all files in the repository (excluding hidden and build directories)
- **Code Files**: Number of code files (Python, JavaScript, TypeScript, Java, Go, Ruby, PHP, C#, C++, etc.)
- **Test Files**: Number of test files detected
- **Test Coverage**: Estimated test coverage percentage

#### Before & After Comparison (when tests are generated)
When AI test generation is enabled, shows a detailed comparison:

**Visual Comparison Panel:**
- **BEFORE Analysis**: Original test count and coverage
- **AFTER Generation**: Updated test count and coverage
- **Tests Generated**: Number of new test files created
- **Files Now Covered**: How many files now have tests
- **Coverage Improvement**: Percentage points increase in coverage

**Example:**
```
📊 Before & After Comparison
┌─────────────────────────────────────────────────────────────────────┐
│ BEFORE: 8 tests (26.7% coverage)                                    │
│ AFTER:  13 tests (43.3% coverage)                                   │
│ Generated: +5 tests | Coverage: ↑ 16.6%                             │
└─────────────────────────────────────────────────────────────────────┘
```

#### Code Quality Issues
Table showing detected issues with:
- **Severity**: High, Medium, or Low
- **File/Location**: Where the issue was found
- **Issue Description**: What the problem is
- **Suggestion**: How to fix it

Common issues detected:
- Missing README file
- Missing .gitignore file
- Low test coverage (< 30%)
- Moderate test coverage (30-60%)

### 🧪 Generated Test Cases

When "Generate Missing Test Cases" is enabled:
- AI analyzes code files that lack tests
- Generates complete, runnable test files
- Shows test code with syntax highlighting
- Includes test description and purpose
- **Download Tests** button to save all generated tests

**Note**: Test generation is limited to 5 files for performance reasons.

### 📈 Progress Tracking

Real-time progress bar showing:
- Current step (Cloning, Analyzing, Generating tests)
- Progress percentage
- Status messages

## How It Works

### Backend API Endpoints

#### `POST /api/analyze-repo`
Starts code analysis and test generation.

**Request Body**:
```json
{
  "repo_url": "https://github.com/username/repo.git",
  "branch_name": "main",
  "generate_tests": true
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "Analysis started"
}
```

#### `GET /api/analyze-status/<task_id>`
Retrieves analysis progress and results.

**Response (In Progress)**:
```json
{
  "status": "in_progress",
  "progress": 50,
  "message": "Analyzing code structure..."
}
```

**Response (Completed)**:
```json
{
  "status": "completed",
  "progress": 100,
  "message": "Analysis complete!",
  "result": {
    "analysis_before": {
      "total_files": 45,
      "code_files": 30,
      "test_files": 8,
      "test_coverage": 26.7,
      "files_without_tests": 22,
      "issues": [...]
    },
    "analysis_after": {
      "total_files": 50,
      "code_files": 30,
      "test_files": 13,
      "test_coverage": 43.3,
      "tests_generated": 5
    },
    "comparison": {
      "tests_added": 5,
      "coverage_improvement": 16.6,
      "files_now_covered": 5
    },
    "test_cases": [...],
    "repo_path": "/path/to/temp_repos/analysis_abc123"
  }
}
```

### Analysis Process

1. **Clone Repository** (10% progress)
   - Creates directory under `temp_repos/analysis_<task_id>` in project root
   - Clones repository with `--depth 1` for speed
   - Checks out specified branch
   - Repository is preserved (not deleted) for inspection

2. **Analyze Code Structure** (30-50% progress)
   - Scans all files recursively
   - Identifies code files by extension
   - Detects test files using common patterns
   - Calculates test coverage estimate
   - Detects common code quality issues

3. **Generate Tests** (70-90% progress) - Optional
   - Finds code files without corresponding tests
   - Limits to 5 files for performance
   - Uses AI model to generate complete test files
   - **Writes test files directly into the cloned repository**
   - Test files are created in the same directory as source files
   - Includes imports and setup code
   - Handles errors gracefully

4. **Re-Analyze Repository** (95% progress) - After test generation
   - Re-scans repository to detect newly created test files
   - Calculates updated test coverage metrics
   - Compares before/after statistics
   - Generates comparison report

5. **Complete** (100% progress)
   - Returns before/after analysis results
   - Returns comparison metrics
   - Returns generated test cases with file locations
   - Repository remains in `temp_repos/` for review
   - Cleanup only occurs on error

## Technical Details

### Files
- **HTML**: `/static/test-generator.html`
- **JavaScript**: `/static/test-generator.js`
- **Backend**: `/server.py` (endpoints at lines 545-842)
- **CSS**: Shared `/static/styles.css`

### Dependencies
- Flask (backend web framework)
- LangChain with OpenAI (AI test generation)
- Git (repository cloning)
- Python standard library (tempfile, subprocess, pathlib)

### Code File Extensions Detected
`.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.go`, `.rb`, `.php`, `.cs`, `.cpp`, `.c`, `.h`, `.hpp`

### Test File Patterns
- `test_` prefix
- `_test.` suffix
- `test/` or `/tests/` directory
- `spec.`, `.spec.`, `.test.` patterns

### Excluded Directories
- Hidden directories (starting with `.`)
- `node_modules`
- `__pycache__`
- `venv`
- `dist`
- `build`

## Configuration

### AI Model Settings
Test generation uses the AI model configured in `config.py`:
- `AI_MODEL`: Model to use for test generation
- `AI_BASE_URL`: API endpoint
- `AI_API_KEY`: API key for authentication
- `AI_TEMPERATURE`: Temperature for generation

### Test Generation Prompt
The prompt used for test generation is stored in `/prompts/test_generation.txt`. The prompt is designed to:
- **Achieve ~95% code coverage** by generating comprehensive test suites
- Create **5-10+ test cases per function** covering all code paths
- Include positive, negative, edge case, and error handling tests
- Mock external dependencies for isolated unit testing
- Follow language-specific testing frameworks and conventions

**Coverage Strategy:**
The AI generates multiple test scenarios per function:
- Happy path tests (normal operation)
- Edge cases (empty, null, boundary values)
- Error scenarios (exceptions, invalid inputs)
- State-based tests (different object states)
- Mocked dependency tests (isolated from external services)

**Customization:**
You can customize the prompt to:
- Adjust coverage targets (default: 95%)
- Add language-specific testing patterns
- Modify test density (tests per function)
- Change mocking strategies
- Add project-specific requirements

If the prompt file cannot be loaded, the system falls back to a basic inline prompt.

If AI API is not configured or `generate_tests` is false, only code analysis is performed.

## Usage Examples

### Example 1: Analyze Repository Without Test Generation
1. Navigate to Test Generator page
2. Enter repository URL: `https://github.com/your-org/your-repo.git`
3. Enter branch name: `main`
4. **Uncheck** "Generate Missing Test Cases"
5. Click "Analyze Repository"
6. View code analysis results

### Example 2: Analyze and Generate Tests
1. Navigate to Test Generator page
2. Enter repository URL: `https://github.com/your-org/your-repo.git`
3. Enter branch name: `develop`
4. **Check** "Generate Missing Test Cases"
5. Click "Analyze Repository"
6. Wait for analysis to complete
7. View code analysis results
8. Review generated test cases
9. Click "Download Tests" to save

## Limitations

- Repository must be publicly accessible or credentials must be configured
- Test generation limited to 5 files per analysis
- Files larger than 10,000 characters are skipped for test generation
- Code content truncated to 5,000 characters for AI processing
- Test generation requires AI API key configuration
- Cloning timeout: 5 minutes
- Test coverage is estimated based on file count, not actual coverage metrics

## Error Handling

- **Git Clone Failure**: Shows error message with git stderr output
- **Invalid Repository URL**: Returns 400 error
- **Test Generation Failure**: Continues with analysis, shows error in issues list
- **Timeout**: Analysis will timeout after clone operation exceeds 5 minutes
- **Directory Cleanup**: Only on error - successful analyses preserve the repository in `temp_repos/`

## Performance Considerations

- Uses shallow clone (`--depth 1`) for faster cloning
- Limits test generation to 5 files
- Runs analysis in background thread to prevent blocking
- Progress polling every 2 seconds
- Maximum poll duration: 10 minutes (300 attempts)

## Repository Management

### Location
- **Directory**: `temp_repos/analysis_<task_id>/` in project root
- **Structure**: Each analysis gets a unique directory based on task ID
- **Persistence**: Repositories are kept after successful analysis for review

### Cleanup
Repositories can be manually cleaned up:
```bash
# Remove all analyzed repositories
rm -rf temp_repos/

# Remove specific analysis
rm -rf temp_repos/analysis_<task_id>/
```

### Test File Locations
Generated test files are written directly into the cloned repository:
- **Same directory as source**: Test files are created alongside their source files
- **Naming convention**: `test_<filename>` (e.g., `utils.py` → `test_utils.py`)
- **Example structure**:
  ```
  temp_repos/analysis_abc123/
  ├── src/
  │   ├── utils.py
  │   ├── test_utils.py        ← Generated
  │   ├── helpers.py
  │   └── test_helpers.py      ← Generated
  └── lib/
      ├── parser.js
      └── test_parser.js       ← Generated
  ```

## Future Enhancements

Potential improvements:
- Support for private repositories with authentication
- Configurable file limit for test generation
- Actual code coverage analysis using coverage tools
- Support for more programming languages
- Batch test generation
- Test execution and validation
- Integration with CI/CD pipelines
- Automatic git commit of generated tests
- Option to create tests in dedicated test directories
