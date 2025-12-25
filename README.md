# 🛡️ CodeGuard - AI-Powered Code Review & Analysis

AI-powered code review and quality analysis system for GitLab, GitHub, and any Git repository.

## ✨ Features

- 🎨 **Modern JavaScript UI** - Professional dashboard with rich animations
- 📊 **12+ Interactive Charts** - Plotly visualizations for comprehensive insights
- 🔄 **Real-Time Progress** - Watch each step execute with smooth horizontal timeline
- 🤖 **AI-Powered Analysis** - Security, bugs, quality, and test recommendations
- 🏗️ **DDD Practices Check** - Domain-Driven Design compliance analysis
- 🧪 **Unit Test Coverage** - Test file detection and recommendations
- 📥 **Download Reports** - Export to Markdown or JSON format
- 🔒 **Multi-Provider Support** - Works with any OpenAI-compatible AI provider
- 🔗 **Multi-Platform Support** - Works with GitLab, GitHub, Bitbucket, and any Git repository
- 🪝 **Webhook Support** - GitLab & GitHub webhook integration for automatic reviews
- 📈 **Analytics Dashboard** - Aggregate metrics, trends, and insights
- 💾 **MongoDB Storage** - Persistent storage of all review results
- 🔍 **View Past Reviews** - Access complete history with one-click report viewing

## 🚀 Quick Start

### 1. Setup Configuration

```bash
# Copy template
cp config.py.template config.py

# Edit config.py with your API key
nano config.py
```

Add your credentials:
```python
class Config:
    AI_API_KEY = 'your_ai_api_key'
    AI_BASE_URL = 'your_provider_base_url'
    AI_MODEL = 'your_model_name'
    GITHUB_TOKEN = ''  # Optional, for private repos
```

### 2. Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the Server

**Option A: Using start script (recommended)**
```bash
./start.sh
```

**Option B: Direct command**
```bash
python server.py
```

### 4. Open in Browser

Navigate to: **http://localhost:5000**

## 📖 Usage

### Manual Review

1. **Enter URLs** (Works with any Git platform)
   - **GitLab MR**: `https://gitlab.com/owner/repo/-/merge_requests/123`
   - **GitHub PR**: `https://github.com/owner/repo/pull/456`
   - **Bitbucket PR**: `https://bitbucket.org/owner/repo/pull-requests/789`
   - **Repository URL**: The base URL of your Git repository from any platform

2. **Click "🚀 Start Review"**

3. **Watch Progress**
   - 10 steps with real-time horizontal timeline
   - Smooth progress animations
   - Real-time status updates

4. **View Results**
   - Summary dashboard with key metrics
   - 8+ interactive Plotly charts
   - Detailed reports in tabs
   - Download as Markdown or JSON

### Automatic Review via Webhooks

Set up webhooks for automatic reviews when PRs are created:

**Quick Setup:**
1. Configure webhook in GitHub/GitLab:
   - **GitHub:** `http://your-server:5000/api/webhook/github`
   - **GitLab:** `http://your-server:5000/api/webhook/gitlab`

2. Select events: Pull requests / Merge requests

3. PRs are automatically reviewed on:
   - `opened` - New PR created
   - `reopened` - PR reopened
   - `synchronize` / `update` - New commits pushed

**📚 Full webhook documentation:** [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md)

## 📊 Review Analysis

### Automated Checks

1. **Security Review** 🔒
   - SQL injection, XSS vulnerabilities
   - Authentication/authorization issues
   - Hardcoded secrets detection

2. **Bug Detection** 🐛
   - Logic errors and edge cases
   - Null pointer issues
   - Resource leaks

3. **Code Quality** ✨
   - Style compliance
   - Best practices
   - Performance opportunities

4. **Test Coverage** 🧪
   - Unit test detection
   - Coverage analysis
   - Test suggestions

5. **DDD Practices** 🏗️
   - Entity/model detection
   - Repository pattern usage
   - Service layer analysis

6. **Code Structure** 📁
   - File organization
   - Directory structure
   - Complexity analysis

## 🎨 UI Features

### Summary Dashboard
- 📁 Total Files
- 🧪 Test Files Count
- 🏗️ DDD Compliance Score
- 📂 Directory Count

### Interactive Charts
1. Test Coverage Gauge
2. DDD Compliance Gauge
3. File Distribution Pie Chart
4. Code Changes Bar Chart
5. Test Ratio Donut Chart
6. DDD Pattern Radar Chart
7. Top 10 Files by Changes
8. Changes Timeline

### Detailed Reports
- Tab-based interface
- Syntax-highlighted code blocks
- Expandable sections
- Clean formatting

## ⚙️ Configuration

### AI Provider Configuration

The system supports any AI provider compatible with the OpenAI SDK format. Configure using AI_API_KEY, AI_BASE_URL, and AI_MODEL.

**Example Configuration:**
```python
AI_API_KEY = 'your-api-key'
AI_BASE_URL = 'your-provider-base-url'
AI_MODEL = 'your-model-name'
```

The system is compatible with providers such as OpenAI, Anthropic Claude, and other OpenAI-compatible APIs.

### Git Platform Support

This system works with **any Git repository platform**:
- ✅ **GitLab** (Public, Private & Self-hosted)
- ✅ **GitHub** (Public & Private)
- ✅ **Bitbucket** (Cloud & Server)
- ✅ **Azure DevOps**
- ✅ **Gitea, Gogs**
- ✅ **Self-hosted Git servers**
- ✅ Any platform with Git-based pull/merge requests

**Note**: For private repositories, you may need to configure authentication tokens in your environment.

### Customize Prompts

Edit files in `prompts/` directory:
- `security_review.txt`
- `bug_detection.txt`
- `style_optimization.txt`
- `test_suggestions.txt`

Changes take effect immediately on restart.

## 🗂️ Project Structure

```
pr_review/
├── server.py              # Flask backend
├── static/
│   ├── index.html        # HTML structure
│   ├── styles.css        # CSS styling
│   └── app.js            # JavaScript app
├── agents/
│   └── review_agents.py  # AI review agents
├── workflow/
│   └── review_workflow.py # LangGraph workflow
├── utils/
│   └── gitlab_helper.py  # Multi-platform Git API
├── prompts/              # AI prompts
├── config.py             # Configuration (gitignored)
├── config.py.template    # Template
└── requirements.txt      # Dependencies
```

## 🛠️ Troubleshooting

### "config.py not found"
```bash
cp config.py.template config.py
# Then edit with your API key
```

### "AI API key not configured"
Edit `config.py` and replace `'your_api_key_here'` with actual key

### "Port 5000 already in use"
```bash
lsof -i :5000
kill -9 <PID>
```

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Review fails or times out
- Check internet connection
- Verify API quota not exceeded
- Try smaller PR for testing
- Check GitHub token for private repos

## 🔐 Security

- ✅ `config.py` is in `.gitignore`
- ✅ Never commit API keys
- ✅ Rotate keys regularly
- ✅ Use separate keys for dev/prod

## 📚 Documentation

- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **JavaScript UI Guide**: [JAVASCRIPT_UI.md](JAVASCRIPT_UI.md)
- **Complete Setup**: [START_APP.md](START_APP.md)

## 🎯 API Endpoints

### POST /api/review
Review a pull request

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "repo_url": "https://github.com/owner/repo"
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "pr_details": {...},
    "structure": {...},
    "test_analysis": {...},
    "ddd": {...},
    "files": [...],
    "security": "...",
    "bugs": "...",
    "style": "...",
    "tests": "..."
  }
}
```

### GET /health
Health check endpoint

## 🚀 Quick Commands

```bash
# Start server
./start.sh

# Or direct
python server.py

# Stop server (3 options)
# Option 1: Press CTRL+C in terminal
# Option 2: Run stop script
./stop.sh
# Option 3: Kill process manually
lsof -ti :5000 | xargs kill -9
```

## 📦 Requirements

- Python 3.9+
- Virtual environment
- AI API key (any provider)
- GitHub token (optional, for private repos)
- Internet connection

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License

---

**Ready to review?** Run `./start.sh` and open http://localhost:5000 🚀
