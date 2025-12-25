# Code Analyzer Updates - Test File Generation

## Summary of Changes

Updated the Code Analyzer feature to write generated test files directly into the cloned repository instead of just returning them as downloadable content.

---

## Key Changes

### 1. **Repository Cloning Location**
**Before:**
- Cloned to system temp directory (`/tmp/code_analysis_XXXXX`)
- Directory deleted after analysis

**After:**
- Clones to `temp_repos/analysis_<task_id>/` in project root
- Repository **preserved** after successful analysis
- Only cleaned up on error
- Each analysis gets unique directory based on task ID

**Code Location:** [server.py:590-597](server.py#L590-L597)

```python
# Create temp_repos directory in project root
project_root = Path(__file__).parent
temp_repos_dir = project_root / 'temp_repos'
temp_repos_dir.mkdir(exist_ok=True)

# Create unique directory for this analysis
temp_dir = temp_repos_dir / f'analysis_{task_id}'
temp_dir.mkdir(exist_ok=True)
```

---

### 2. **Test File Writing**
**Before:**
- Test files only returned in API response
- User had to download and manually place them

**After:**
- Test files **written directly** into cloned repository
- Created in same directory as source file
- Naming convention: `test_<original_filename>`
- Full file path tracked and returned

**Code Location:** [server.py:756-775](server.py#L756-L775)

```python
# Determine test filename and location
test_filename = f"test_{file_path.name}"
test_file_path = file_path.parent / test_filename

# Write test file to repository
with open(test_file_path, 'w', encoding='utf-8') as f:
    f.write(test_code)

# Get relative path from repo root for display
relative_test_path = test_file_path.relative_to(repo_path)

test_cases.append({
    'filename': str(relative_test_path),
    'code': test_code,
    'description': f'Unit tests for {file_path.name}',
    'written_to': str(test_file_path)
})
```

---

### 3. **API Response Updates**
Added `repo_path` and `written_to` fields to response:

**Response Structure:**
```json
{
  "status": "completed",
  "result": {
    "analysis": { ... },
    "test_cases": [
      {
        "filename": "src/test_utils.py",
        "code": "...",
        "description": "Unit tests for utils.py",
        "written_to": "/path/to/temp_repos/analysis_abc123/src/test_utils.py"
      }
    ],
    "repo_path": "/path/to/temp_repos/analysis_abc123"
  }
}
```

**Code Location:** [server.py:794-797](server.py#L794-L797)

---

### 4. **Frontend Display Updates**
Enhanced UI to show repository location and test file paths:

**New Features:**
- Info banner showing repository location
- Individual test file paths displayed
- Visual indication that files are written to disk

**Code Location:** [test-generator.js:197-234](static/test-generator.js#L197-L234)

**UI Example:**
```
┌─────────────────────────────────────────────────────────────┐
│ 📁 Repository Location: temp_repos/analysis_abc123          │
│ Test files have been written directly into the cloned       │
│ repository in their respective directories.                 │
└─────────────────────────────────────────────────────────────┘

Test File: src/test_utils.py
Location: /full/path/to/temp_repos/analysis_abc123/src/test_utils.py
[Test code displayed here]
```

---

### 5. **Cleanup Behavior**
**Before:**
- Always deleted temp directory in `finally` block

**After:**
- Successful analysis: Repository **preserved**
- Failed analysis: Repository **cleaned up**
- Console logging for transparency

**Code Location:** [server.py:800-820](server.py#L800-L820)

```python
# Print summary
if temp_dir:
    print(f"📁 Repository cloned to: {temp_dir}")
    if test_cases:
        print(f"✅ Generated {len(test_cases)} test files in the repository")

# ... (error handling)

# Cleanup on error only
if temp_dir and os.path.exists(temp_dir):
    try:
        shutil.rmtree(temp_dir)
        print(f"🗑️ Cleaned up temp directory due to error: {temp_dir}")
    except Exception as cleanup_error:
        print(f"Error cleaning up temp directory: {cleanup_error}")
```

---

## File Structure Example

After running Code Analyzer on a repository:

```
pull_request_review/
├── temp_repos/                    ← New directory
│   ├── analysis_abc-123/          ← First analysis
│   │   ├── .git/
│   │   ├── src/
│   │   │   ├── utils.py
│   │   │   ├── test_utils.py      ← Generated ✅
│   │   │   ├── helpers.py
│   │   │   └── test_helpers.py    ← Generated ✅
│   │   └── README.md
│   ├── analysis_def-456/          ← Second analysis
│   │   └── ...
│   └── analysis_ghi-789/          ← Third analysis
│       └── ...
├── static/
├── server.py                      ← Updated
├── TEST_GENERATOR.md              ← Updated
└── .gitignore                     ← Already excludes temp_repos/
```

---

## Benefits

### For Users
✅ **Immediate usability** - Tests written directly to repository
✅ **Correct file structure** - Tests in same directory as source
✅ **Easy inspection** - Can browse full repository with tests
✅ **Ready to commit** - Can review and commit tests via git

### For Development
✅ **Persistence** - Repository available for debugging
✅ **Traceability** - Each analysis has unique directory
✅ **Transparency** - Full file paths logged and displayed

---

## Repository Management

### Viewing Analyzed Repositories
```bash
# List all analyzed repositories
ls -la temp_repos/

# Navigate to specific analysis
cd temp_repos/analysis_abc123/

# View generated test files
find . -name "test_*.py"
```

### Cleanup
```bash
# Remove all analyzed repositories
rm -rf temp_repos/

# Remove specific analysis
rm -rf temp_repos/analysis_abc123/
```

### Git Integration
Generated tests can be committed:
```bash
cd temp_repos/analysis_abc123/
git status                          # See generated tests
git add src/test_*.py              # Stage test files
git commit -m "Add generated tests"
```

---

## Updated Files

| File | Changes | Lines |
|------|---------|-------|
| [server.py](server.py) | Clone location, test writing, cleanup logic | 590-820 |
| [test-generator.js](static/test-generator.js) | Display repo path, show file locations | 131-234 |
| [TEST_GENERATOR.md](TEST_GENERATOR.md) | Updated documentation | Multiple |
| [.gitignore](.gitignore) | Already excludes `temp_repos/` | Line 25 |

---

## Backward Compatibility

✅ **API**: Fully backward compatible - added new fields only
✅ **Frontend**: Gracefully handles missing `repo_path` field
✅ **Download**: Download button still works as before

---

## Testing Checklist

- [ ] Clone repository to `temp_repos/`
- [ ] Generate test files in repository
- [ ] Verify test files written to correct locations
- [ ] Check repository path displayed in UI
- [ ] Confirm repository preserved after success
- [ ] Verify cleanup on error
- [ ] Test download button still works
- [ ] Check console logs for file paths

---

## Console Output Example

When running Code Analyzer:

```
Cloning repository...
Analyzing code structure...
Detecting code quality issues...
Generating test cases...
Generating tests (1/5)...
✅ Generated test file: src/test_utils.py
Generating tests (2/5)...
✅ Generated test file: lib/test_parser.js
...
📁 Repository cloned to: /path/to/temp_repos/analysis_abc123
✅ Generated 5 test files in the repository
Analysis complete!
```

---

## Configuration

No configuration required. Feature works automatically with existing settings:
- Uses `AI_MODEL` from config.py
- Uses `AI_API_KEY` from config.py
- Respects `generate_tests` toggle in UI

---

## Notes

- `.gitignore` already excludes `temp_repos/` directory
- Each analysis creates unique directory with task ID
- Maximum 5 test files generated per analysis (existing limit)
- Test files use language-appropriate naming conventions
- Repository preserved for manual review and git operations
