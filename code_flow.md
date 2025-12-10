# PR Review System - Complete Code Flow

## Architecture Overview

```
User Input (PR URL)
        ↓
   Flask Server (app.py)
        ↓
   LangGraph Workflow (workflow/review_workflow.py)
        ↓
   ┌─────────────┬──────────────┬─────────────┬────────────┐
   │   Fetch PR  │  Clone Repo  │   Security  │    Bug     │
   │             │              │   Review    │  Detection │
   └─────────────┴──────────────┴─────────────┴────────────┘
        ↓
   Review Agents (agents/review_agents.py)
        ↓
   AI Provider (OpenAI, Anthropic, or custom)
        ↓
   MongoDB Storage
        ↓
   JavaScript UI (static/app.js)
```

## Detailed Flow

### 1. User Initiates Review

**File**: `static/app.js`

```javascript
// User enters PR URL and clicks "Start Review"
async startReview(prUrl, repoUrl = '') {
    // Send request to Flask backend
    const response = await fetch('/api/review', {
        method: 'POST',
        body: JSON.stringify({ pr_url: prUrl, repo_url: repoUrl })
    });

    // Get job_id for tracking
    const data = await response.json();
    this.currentJobId = data.job_id;

    // Start polling for progress
    this.pollReviewStatus();
}
```

### 2. Flask Server Receives Request

**File**: `app.py`

```python
@app.route('/api/review', methods=['POST'])
def review_pr():
    data = request.json
    pr_url = data.get('pr_url')
    repo_url = data.get('repo_url', '')

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    review_jobs[job_id] = {
        'status': 'starting',
        'progress': 0,
        'current_step': 'Initializing review...'
    }

    # Start review in background thread
    thread = threading.Thread(
        target=run_review_workflow,
        args=(job_id, pr_url, repo_url)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'started'})
```

### 3. Background Thread Starts Workflow

**File**: `app.py` → `run_review_workflow()`

```python
def run_review_workflow(job_id, pr_url, repo_url):
    try:
        # Load configuration from .env
        Config.validate()

        # Initialize workflow
        workflow = PRReviewWorkflow(
            ai_api_key=Config.get_ai_api_key(),
            github_token=Config.GITHUB_TOKEN,
            ai_model=Config.get_ai_model(),
            ai_base_url=Config.get_ai_base_url(),
            ai_temperature=Config.get_ai_temperature()
        )

        # Update progress callbacks
        def update_progress(status, progress, step):
            review_jobs[job_id]['status'] = status
            review_jobs[job_id]['progress'] = progress
            review_jobs[job_id]['current_step'] = step

        # Execute workflow
        result = workflow.review_pr(pr_url, repo_url, update_progress)

        # Store result in MongoDB
        save_to_database(job_id, result)

    except Exception as e:
        review_jobs[job_id]['status'] = 'error'
        review_jobs[job_id]['error'] = str(e)
```

### 4. LangGraph Workflow Execution

**File**: `workflow/review_workflow.py`

```python
class PRReviewWorkflow:
    def __init__(self, ai_api_key, github_token, ai_model, ai_base_url, ai_temperature):
        # Initialize GitLab helper (supports all Git platforms)
        self.gitlab_helper = GitLabHelper(github_token)

        # Initialize review agents with AI config
        self.review_agents = ReviewAgents(
            api_key=ai_api_key,
            model=ai_model,
            base_url=ai_base_url,
            temperature=ai_temperature
        )

        # Build workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build LangGraph state machine"""
        workflow = StateGraph(ReviewState)

        # Add nodes
        workflow.add_node("fetch_pr", self.fetch_pr_node)
        workflow.add_node("clone_repo", self.clone_repo_node)
        workflow.add_node("security_check", self.security_check_node)
        workflow.add_node("bug_check", self.bug_check_node)
        workflow.add_node("style_check", self.style_check_node)
        workflow.add_node("test_suggestions", self.test_suggestions_node)

        # Define edges (flow)
        workflow.set_entry_point("fetch_pr")
        workflow.add_edge("fetch_pr", "clone_repo")
        workflow.add_edge("clone_repo", "security_check")
        workflow.add_edge("security_check", "bug_check")
        workflow.add_edge("bug_check", "style_check")
        workflow.add_edge("style_check", "test_suggestions")
        workflow.add_edge("test_suggestions", END)

        return workflow.compile()
```

#### Node 1: Fetch PR Details

**File**: `workflow/review_workflow.py`

```python
def fetch_pr_node(self, state: ReviewState) -> ReviewState:
    """Fetch PR/MR details from any Git platform"""
    pr_details = self.gitlab_helper.get_mr_details(state['pr_url'])
    state['pr_details'] = pr_details
    state['status'] = 'PR/MR details fetched successfully'
    return state
```

**File**: `utils/gitlab_helper.py`

```python
def get_mr_details(self, pr_url: str) -> Dict:
    """Fetch PR/MR details from GitLab, GitHub, or other platforms"""
    # Parse URL to get platform, owner/repo/mr_number
    mr_info = self.parse_pr_url(pr_url)

    # Platform-specific API calls
    if mr_info['platform'] == 'gitlab':
        return self._get_gitlab_mr_details(mr_info, pr_url)
    elif mr_info['platform'] == 'github':
        return self._get_github_pr_details(mr_info, pr_url)
    else:
        # Generic fallback for other platforms
        return {
            'title': f"MR #{mr_info['mr_number']}",
            'description': 'Details not available via API',
            'files_changed': []
        }
```

#### Node 2: Clone Repository

**File**: `workflow/review_workflow.py`

```python
def clone_repo_node(self, state: ReviewState) -> ReviewState:
    """Clone repository to local directory"""
    repo_path = self.gitlab_helper.clone_repository(state['repo_url'])
    state['repo_path'] = repo_path
    state['status'] = 'Repository cloned successfully'
    return state
```

#### Node 3: Security Review

**File**: `workflow/review_workflow.py`

```python
def security_check_node(self, state: ReviewState) -> ReviewState:
    """Run security analysis on code changes"""
    files_changed = state['pr_details']['files_changed']

    # Call security review agent
    security_review = self.review_agents.security_review(files_changed)

    state['security_review'] = security_review
    state['status'] = 'Security review completed'
    return state
```

**File**: `agents/review_agents.py`

```python
def security_review(self, code_changes: List[Dict]) -> str:
    """Agent for security vulnerability analysis"""

    # Create prompt with system instructions
    prompt = ChatPromptTemplate.from_messages([
        ("system", self.prompts['security']),  # From prompts/security_review.txt
        ("user", "Review these code changes for security issues:\n\n{code_changes}")
    ])

    # Format code changes
    formatted_code = self._format_code_changes(code_changes)

    # Create LangChain chain
    chain = prompt | self.llm

    # Invoke AI
    result = chain.invoke({"code_changes": formatted_code})

    return result.content
```

#### Node 4: Bug Detection

Similar to security review, but uses `prompts/bug_detection.txt`

#### Node 5: Style & Optimization

Similar to security review, but uses `prompts/style_optimization.txt`

#### Node 6: Test Suggestions

Similar to security review, but uses `prompts/test_suggestions.txt`

### 5. Code Formatting for AI

**File**: `agents/review_agents.py`

```python
def _format_code_changes(self, code_changes: List[Dict]) -> str:
    """Format code changes for AI consumption"""
    formatted = []

    for file_change in code_changes:
        # Add file header
        formatted.append(f"\n{'='*80}")
        formatted.append(f"File: {file_change.get('filename', 'Unknown')}")

        # Add metadata
        if 'status' in file_change:
            formatted.append(f"Status: {file_change['status']}")
        if 'additions' in file_change and 'deletions' in file_change:
            formatted.append(f"Changes: +{file_change['additions']} -{file_change['deletions']}")

        formatted.append(f"{'='*80}\n")

        # Add patch (git diff)
        if file_change.get('patch'):
            formatted.append(file_change['patch'])
        else:
            formatted.append("(Binary file or no patch available)")

    return "\n".join(formatted)
```

### 6. AI API Call

**File**: `agents/review_agents.py`

The `ChatOpenAI` class from LangChain handles the actual API call:

```python
# Configuration
llm_kwargs = {
    "api_key": ai_api_key,              # From .env: AI_API_KEY
    "model": model,                      # From .env: AI_MODEL
    "temperature": temperature,          # From .env: AI_TEMPERATURE
    "base_url": base_url                # From .env: AI_BASE_URL
}

self.llm = ChatOpenAI(**llm_kwargs)

# Actual API call (handled by LangChain)
result = chain.invoke({"code_changes": formatted_code})
```

**HTTP Request Structure** (simplified):

```http
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer [AI_API_KEY]
Content-Type: application/json

{
  "model": "claude-3-5-sonnet-20241022",
  "temperature": 0.1,
  "messages": [
    {
      "role": "system",
      "content": "You are an expert security analyst...[full prompt]"
    },
    {
      "role": "user",
      "content": "Review these code changes...\n\n================\nFile: src/auth.js\n...[formatted diffs]"
    }
  ]
}
```

### 7. Store Results in MongoDB

**File**: `app.py`

```python
def save_review_to_db(job_id, pr_url, result):
    """Save review results to MongoDB"""
    review_data = {
        'job_id': job_id,
        'pr_url': pr_url,
        'pr_details': {
            'title': result.get('pr_details', {}).get('title'),
            'author': result.get('pr_details', {}).get('author'),
            # ... more metadata
        },
        'reviews': {
            'security': result.get('security_review', ''),
            'bugs': result.get('bug_review', ''),
            'style': result.get('style_review', ''),
            'tests': result.get('test_suggestions', '')
        },
        'timestamp': datetime.utcnow(),
        'status': 'completed'
    }

    # Insert into MongoDB
    reviews_collection.insert_one(review_data)
```

### 8. Frontend Polling

**File**: `static/app.js`

```javascript
async pollReviewStatus() {
    // Poll every 2 seconds
    this.pollInterval = setInterval(async () => {
        const response = await fetch(`/api/status/${this.currentJobId}`);
        const data = await response.json();

        // Update progress bar
        this.updateProgress(data.progress, data.current_step);

        // Check if complete
        if (data.status === 'completed') {
            clearInterval(this.pollInterval);
            this.loadReviewResults(this.currentJobId);
        }
    }, 2000);
}
```

### 9. Display Results

**File**: `static/app.js`

```javascript
async loadReviewResults(jobId) {
    // Fetch results from backend
    const response = await fetch(`/api/results/${jobId}`);
    const data = await response.json();

    // Show summary section with charts
    this.showSummarySection();

    // Render security review
    document.getElementById('securityReview').innerHTML =
        marked.parse(data.reviews.security);

    // Render bug detection
    document.getElementById('bugReview').innerHTML =
        marked.parse(data.reviews.bugs);

    // Render style suggestions
    document.getElementById('styleReview').innerHTML =
        marked.parse(data.reviews.style);

    // Render test suggestions
    document.getElementById('testReview').innerHTML =
        marked.parse(data.reviews.tests);

    // Generate charts
    this.generateCharts(data);
}
```

## Data Flow Summary

```
1. User Input (PR URL)
   ↓
2. Flask API (/api/review)
   ↓
3. Background Thread (run_review_workflow)
   ↓
4. LangGraph Workflow Initialization
   ↓
5. Node: Fetch PR/MR Details
   - GitLab/GitHub API call via GitLabHelper
   - Extract: files_changed[] with patches
   ↓
6. Node: Clone Repository (optional)
   - Git clone via GitPython
   ↓
7. Node: Security Review
   - Load prompt: prompts/security_review.txt
   - Format code changes
   - AI API call via LangChain
   ↓
8. Node: Bug Detection
   - Load prompt: prompts/bug_detection.txt
   - Format code changes
   - AI API call via LangChain
   ↓
9. Node: Style Review
   - Load prompt: prompts/style_optimization.txt
   - Format code changes
   - AI API call via LangChain
   ↓
10. Node: Test Suggestions
    - Load prompt: prompts/test_suggestions.txt
    - Format code changes
    - AI API call via LangChain
    ↓
11. Save to MongoDB
    - Store all reviews
    - Store metadata
    ↓
12. Frontend Polling
    - Poll /api/status/{job_id} every 2s
    - Update progress bar
    ↓
13. Display Results
    - Fetch /api/results/{job_id}
    - Render markdown reviews
    - Generate charts
    - Show summary section
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Flask server, API endpoints, job management |
| `static/app.js` | Frontend JavaScript, UI interactions |
| `static/index.html` | HTML structure, sections, forms |
| `workflow/review_workflow.py` | LangGraph workflow orchestration |
| `agents/review_agents.py` | AI review agents, prompt management |
| `utils/gitlab_helper.py` | Multi-platform Git API integration (GitLab, GitHub, etc.) |
| `config.py` | Configuration management, env variables |
| `prompts/security_review.txt` | Security analysis instructions |
| `prompts/bug_detection.txt` | Bug detection instructions |
| `prompts/style_optimization.txt` | Style review instructions |
| `prompts/test_suggestions.txt` | Test suggestions instructions |

## Configuration Flow

```
.env file
  ↓
Config.validate() (config.py)
  ↓
PRReviewWorkflow.__init__() (workflow/review_workflow.py)
  ↓
ReviewAgents.__init__() (agents/review_agents.py)
  ↓
ChatOpenAI() (LangChain wrapper)
  ↓
AI Provider API
```

## Error Handling Flow

```
AI API Error
  ↓
Exception in review_agents.py
  ↓
Check error type:
  - 429/RESOURCE_EXHAUSTED → Quota exceeded message
  - 403/PERMISSION_DENIED → Permission denied message
  - 404/NOT_FOUND → Model not found message
  - Other → Generic error message
  ↓
Return error string instead of review
  ↓
Store in MongoDB with error flag
  ↓
Display in UI with error styling
```

## Session Management

```
User starts review
  ↓
Generate UUID job_id
  ↓
Store in review_jobs[job_id] (in-memory)
  ↓
Frontend polls with job_id
  ↓
On completion, save to MongoDB
  ↓
History page loads from MongoDB
  ↓
Statistics aggregates from MongoDB
```
