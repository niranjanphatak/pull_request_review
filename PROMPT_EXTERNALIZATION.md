# Code Analyzer Prompt Externalization

## Summary of Changes

Moved the Code Analyzer test generation prompt from hardcoded inline text in `server.py` to an external file in the `prompts/` directory, following the same pattern used for PR review prompts.

---

## Why This Change?

### Benefits

✅ **Consistency** - Follows same pattern as PR review prompts
✅ **Maintainability** - Easy to update prompt without touching Python code
✅ **Version Control** - Track prompt changes separately in git history
✅ **Customization** - Users can customize test generation behavior easily
✅ **Experimentation** - A/B test different prompts without code changes
✅ **Documentation** - Prompt is self-documenting in dedicated file

### Before

**Location**: Hardcoded in `server.py` lines 744-753

```python
prompt = f"""Generate a unit test file for the following code.
The test should use common testing frameworks for the language and cover the main functionality.

File: {file_path.name}
Code:
```
{code_content[:5000]}
```

Generate a complete test file that can be run immediately. Include imports and setup code."""
```

**Issues**:
- Mixed business logic with prompt content
- Hard to track prompt changes
- Requires Python knowledge to modify
- No prompt versioning

### After

**Location**: `prompts/test_generation.txt`

**Loading** (server.py lines 705-718):
```python
# Load test generation prompt from file
prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
test_gen_prompt_file = os.path.join(prompts_dir, 'test_generation.txt')

test_gen_prompt_template = ""
try:
    with open(test_gen_prompt_file, 'r', encoding='utf-8') as f:
        test_gen_prompt_template = f.read().strip()
except Exception as e:
    print(f"Warning: Could not load test generation prompt: {e}")
    # Fallback to inline prompt if file not found
    test_gen_prompt_template = """Generate a unit test file..."""
```

**Usage** (server.py lines 758-766):
```python
# Generate test using AI with loaded prompt template
prompt = f"""{test_gen_prompt_template}

File: {file_path.name}
Code:
```
{code_content[:5000]}
```
"""
```

---

## New Prompt File Structure

### Location
`prompts/test_generation.txt`

### Content Structure

**Key Features:**
- **95% Coverage Target**: Explicit goal to achieve comprehensive coverage
- **Multiple Test Scenarios**: 5-10+ tests per function
- **Test Type Diversity**: Happy path, edge cases, errors, state-based, mocked
- **Detailed Guidelines**: Specific requirements for each test category
- **Example Test Density**: Clear guidance on minimum tests per complexity level

**Prompt Sections:**

1. **CRITICAL COVERAGE REQUIREMENTS**
   - Target: 95% code coverage
   - All public/private functions
   - All branches and error paths
   - All edge cases and boundaries

2. **Coverage Strategy**
   - Happy path tests
   - Edge case tests (empty, null, boundary values)
   - Error tests (exceptions, invalid inputs)
   - State tests (different object states)
   - Integration tests

3. **Test Case Types**
   - Positive: Valid inputs, typical use cases
   - Negative: Invalid inputs, exceptions
   - Edge Cases: Min/max values, empty collections
   - State-Based: Different object states
   - Mock/Stub: External dependencies mocked

4. **Test Density Guidelines**
   - Simple function (10 lines): Minimum 5 tests
   - Medium function (20-30 lines): Minimum 10 tests
   - Complex function (50+ lines): Minimum 15-20 tests
   - Class with 5 methods: Minimum 25-30 tests

5. **Mocking Guidelines**
   - Database calls → Mock fixtures
   - API requests → Mock responses
   - File operations → In-memory mocks
   - Time/dates → Deterministic mocks
   - Random values → Seeded generators

---

## Implementation Details

### Changes Made

#### 1. Created Prompt File
**File**: `prompts/test_generation.txt`
- **Coverage-focused**: Targets ~95% code coverage
- **Comprehensive testing**: 5-10+ test cases per function
- **Multi-scenario testing**: Happy path, edge cases, errors, mocking
- **Language-agnostic guidelines**: Works for Python, JavaScript, Java, etc.
- **Best practices and requirements**: AAA pattern, mocking, isolation
- **Clear output format**: Detailed test structure specification

#### 2. Updated server.py
**Lines 705-718**: Load prompt from file with fallback
**Lines 758-766**: Use loaded prompt template

**Key Features**:
- Graceful error handling
- Fallback to inline prompt if file missing
- Warning message logged if file not found
- No breaking changes - works with or without file

#### 3. Updated Documentation
**TEST_GENERATOR.md**: Added "Test Generation Prompt" section
**BEFORE_AFTER_COMPARISON.md**: Added prompt file to configuration and files modified
**PROMPT_EXTERNALIZATION.md**: This document explaining the change

---

## Prompt Directory Structure

```
prompts/
├── best_practices.txt          # PR review - best practices
├── bug_detection.txt           # PR review - bug detection
├── documentation_review.txt    # PR review - documentation
├── security_review.txt         # PR review - security
├── style_optimization.txt      # PR review - style & optimization
├── test_suggestions.txt        # PR review - test suggestions
└── test_generation.txt         ← NEW: Code Analyzer test generation
```

All prompts now follow consistent pattern:
- Stored in `prompts/` directory
- Plain text `.txt` files
- Loaded at runtime
- Version controlled with code

---

## Usage

### For Developers

**Modify the prompt**:
```bash
# Edit the prompt file
nano prompts/test_generation.txt

# Changes take effect immediately on next analysis
# No server restart required (loaded per-request)
```

**Track prompt changes**:
```bash
# View prompt history
git log prompts/test_generation.txt

# Compare versions
git diff HEAD~1 prompts/test_generation.txt
```

### For Users

**Customize test generation**:
1. Open `prompts/test_generation.txt`
2. Modify requirements, output format, or best practices
3. Save the file
4. Run Code Analyzer - new prompt is used automatically

**Example customization**:
```diff
## Requirements:
- Use common testing frameworks for the language
+ - Prefer pytest over unittest for Python
+ - Use describe/it blocks for JavaScript
- Cover the main functionality and important use cases
+ - Aim for 80%+ code coverage
+ - Include edge cases and error scenarios
```

---

## Backward Compatibility

✅ **Fully backward compatible**

- If `prompts/test_generation.txt` exists → Use it
- If file missing or unreadable → Fallback to inline prompt
- No breaking changes to API or behavior
- Existing code continues to work

**Fallback Behavior**:
```python
except Exception as e:
    print(f"Warning: Could not load test generation prompt: {e}")
    # Fallback to inline prompt
    test_gen_prompt_template = """Generate a unit test file for the following code.
The test should use common testing frameworks for the language and cover the main functionality.
Generate a complete test file that can be run immediately. Include imports and setup code."""
```

---

## Testing

### Verify Prompt Loading

**Test 1: File exists**
```python
# Expected: Loads from prompts/test_generation.txt
# Check server logs: No warning message
```

**Test 2: File missing**
```bash
mv prompts/test_generation.txt prompts/test_generation.txt.bak
# Expected: Falls back to inline prompt
# Check server logs: "Warning: Could not load test generation prompt"
```

**Test 3: File corrupted**
```bash
echo "invalid" > prompts/test_generation.txt
# Expected: Uses corrupted content (loads successfully)
# May affect test quality but won't crash
```

### Verify Test Generation

Run Code Analyzer with different prompts:

**Default prompt**:
- Tests use standard frameworks
- Basic coverage of main functionality

**Custom prompt** (add specific requirements):
- Tests follow custom requirements
- Additional test cases generated

---

## Future Enhancements

Potential improvements:

### Prompt Versioning
Store prompt version in MongoDB like PR review prompts:
```python
prompt_version = {
    'version': '1.0.0',
    'description': 'Initial test generation prompt',
    'created_at': datetime.now()
}
```

### Language-Specific Prompts
Different prompts for different languages:
```
prompts/
├── test_generation_python.txt
├── test_generation_javascript.txt
├── test_generation_java.txt
└── test_generation.txt  # Fallback
```

### Prompt Templates
Use Jinja2 or similar for advanced templating:
```python
from jinja2 import Template

template = Template(test_gen_prompt_template)
prompt = template.render(
    language=language,
    framework=framework,
    coverage_target=80
)
```

### A/B Testing
Track which prompts produce better tests:
```python
prompt_metrics = {
    'version': '1.0.0',
    'tests_generated': 150,
    'tests_passing': 142,
    'avg_coverage': 85.3
}
```

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| **prompts/test_generation.txt** | New prompt file | 1-35 (NEW) |
| **server.py** | Load prompt from file | 705-718, 758-766 |
| **TEST_GENERATOR.md** | Added prompt documentation | 225-234 |
| **BEFORE_AFTER_COMPARISON.md** | Updated configuration | 356-360, 376 |
| **PROMPT_EXTERNALIZATION.md** | This documentation | 1-300+ (NEW) |

---

## Configuration

No configuration required. Works automatically:

- ✅ Prompt loaded from `prompts/test_generation.txt`
- ✅ Fallback to inline prompt if file missing
- ✅ Changes take effect immediately
- ✅ No server restart needed

---

## Comparison with PR Review Prompts

### PR Review Prompts (existing pattern)
**File**: `agents/review_agents.py`
```python
def _load_prompts(self) -> Dict[str, str]:
    prompt_files = {
        'security': 'security_review.txt',
        'bugs': 'bug_detection.txt',
        'style': 'style_optimization.txt',
        'tests': 'test_suggestions.txt'
    }

    for key, filename in prompt_files.items():
        filepath = os.path.join(self.prompts_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            prompts[key] = f.read().strip()
```

### Code Analyzer Prompt (new pattern)
**File**: `server.py`
```python
# Load test generation prompt from file
prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
test_gen_prompt_file = os.path.join(prompts_dir, 'test_generation.txt')

try:
    with open(test_gen_prompt_file, 'r', encoding='utf-8') as f:
        test_gen_prompt_template = f.read().strip()
except Exception as e:
    print(f"Warning: Could not load test generation prompt: {e}")
    test_gen_prompt_template = """..."""  # Fallback
```

**Differences**:
- PR review: No fallback (raises error if file missing)
- Code Analyzer: Graceful fallback to inline prompt
- PR review: Loaded once during initialization
- Code Analyzer: Loaded per-request (in background thread)

**Similarity**:
- Both load from `prompts/` directory
- Both use `.txt` files
- Both strip whitespace
- Both use UTF-8 encoding

---

## Notes

- ✅ Prompt file is version controlled
- ✅ Compatible with existing `.gitignore`
- ✅ No environment variables needed
- ✅ Works in all deployment scenarios
- ✅ Safe to modify while server running
- ✅ Clear separation of concerns (code vs prompts)

---

## References

- **Prompt File**: [prompts/test_generation.txt](prompts/test_generation.txt)
- **Backend Code**: [server.py:705-766](server.py#L705-L766)
- **Documentation**: [TEST_GENERATOR.md:225-234](TEST_GENERATOR.md#L225-L234)
- **Related Prompts**: [prompts/](prompts/)
