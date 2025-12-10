# JavaScript UI Setup Guide

This guide explains how to use the new JavaScript-based UI for the AI PR Code Review System.

## Overview

The JavaScript UI provides a modern, interactive web interface with:
- Real-time progress updates with horizontal scroll
- 8 interactive Plotly charts for visualization
- Rich CSS animations and effects
- Tab-based detailed reports
- Download functionality (Markdown & JSON)
- Professional gradient design

## Architecture

### Frontend (JavaScript)
- **HTML**: `static/index.html` - Main page structure
- **CSS**: `static/styles.css` - Rich styling with animations
- **JavaScript**: `static/app.js` - Application logic and chart rendering

### Backend (Flask)
- **Server**: `server.py` - Flask API server
- **API Endpoint**: `/api/review` - POST endpoint for PR reviews
- **Static Files**: Served from `/static/` directory

## Quick Start

### 1. Configure Your Credentials

Create `config.py` from the template:

```bash
cp config.py.template config.py
```

Edit `config.py` and set your credentials:

```python
class Config:
    # AI Configuration
    AI_API_KEY = 'your_actual_api_key_here'
    AI_BASE_URL = 'your_provider_base_url'
    AI_MODEL = 'your_model_name'
    AI_TEMPERATURE = 0.1

    # GitHub Configuration (optional - only for private repos)
    GITHUB_TOKEN = ''
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Install Dependencies

If you haven't already:

```bash
pip install -r requirements.txt
```

### 4. Start the Server

```bash
python server.py
```

You should see:

```
================================================================================
🚀 Starting AI PR Code Review Server
================================================================================
AI Model: your_model_name
AI Base URL: your_provider_base_url
GitHub Token: Not set (public repos only)

Server running at: http://localhost:5000
Open your browser and navigate to the URL above
================================================================================
```

### 5. Open the UI

Navigate to: **http://localhost:5000**

## Using the UI

### Step 1: Enter PR/MR Details (Any Git Platform)
- **Pull/Merge Request URL**:
  - GitHub: `https://github.com/owner/repo/pull/123`
  - GitLab: `https://gitlab.com/owner/repo/-/merge_requests/456`
  - Bitbucket: `https://bitbucket.org/owner/repo/pull-requests/789`
- **Source Repository URL**: The base URL of your Git repository

### Step 2: Start Review
Click the "🚀 Start Review" button

### Step 3: Watch Progress
The progress bar and step cards will update in real-time showing:
1. 📥 Fetch PR Details
2. 📦 Clone Repository
3. 🔍 Analyze Structure
4. 🔒 Security Review
5. 🐛 Bug Detection
6. ✨ Style Review
7. 🧪 Test Analysis
8. 🏗️ DDD Practices
9. 📊 Complexity Check
10. ✅ Finalize Report

### Step 4: View Results
After completion, you'll see:

#### Summary Dashboard
- **Metrics Cards**: Total files, test files, DDD score, directories
- **Summary Cards**: Quick overview of security, bugs, quality, and tests

#### Visual Analysis (8 Charts)
1. **Test Coverage Gauge** - Number of test files
2. **DDD Compliance Gauge** - Domain-Driven Design score
3. **File Distribution Pie** - Files by type/extension
4. **Code Changes Bar** - Additions vs deletions
5. **Test Ratio Donut** - Test files vs source files
6. **DDD Pattern Radar** - Coverage of entities, repos, services
7. **File Sizes Bar** - Top 10 files by changes
8. **Changes Timeline** - Line changes per file

#### Detailed Reports
Click tabs to view full reports:
- 🔒 **Security**: Security vulnerabilities and risks
- 🐛 **Bugs**: Potential bugs and issues
- ✨ **Quality**: Code style and quality suggestions
- 🧪 **Tests**: Test coverage recommendations

### Step 5: Download Reports
Click download buttons to save:
- 📄 **Markdown Format**: Human-readable report
- 📋 **JSON Format**: Machine-readable data

## API Reference

### POST /api/review

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "repo_url": "https://github.com/owner/repo"
}
```

**Response (Success):**
```json
{
  "success": true,
  "results": {
    "pr_details": {
      "title": "PR Title",
      "author": "username",
      "url": "https://github.com/owner/repo/pull/123"
    },
    "structure": {
      "total": 25,
      "dirs": 8
    },
    "test_analysis": {
      "count": 5,
      "status": "good"
    },
    "ddd": {
      "score": 75,
      "rating": "good",
      "indicators": {
        "entities": true,
        "repos": true,
        "services": true
      }
    },
    "files": [...],
    "security": "Security review text...",
    "bugs": "Bug review text...",
    "style": "Style review text...",
    "tests": "Test suggestions text..."
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message"
}
```

## Troubleshooting

### Server won't start
- Check if port 5000 is already in use
- Ensure virtual environment is activated
- Verify Flask is installed: `pip list | grep -i flask`

### "AI API key not configured" error
- Edit `config.py` and set `AI_API_KEY`
- Ensure it's not set to `'your_api_key_here'`

### No charts appearing
- Check browser console for JavaScript errors
- Ensure Plotly.js is loading from CDN
- Check internet connection (Plotly.js is loaded from CDN)

### 403 or 429 errors
- **403**: API key may be invalid or leaked
- **429**: Quota exceeded, wait or get new key

## Development

### File Structure
```
pr_review/
├── server.py              # Flask backend
├── static/
│   ├── index.html        # Main HTML page
│   ├── styles.css        # CSS styling
│   └── app.js            # JavaScript application
├── config.py             # Configuration (in .gitignore)
├── agents/               # AI review agents
├── workflow/             # LangGraph workflow
├── utils/                # Helper utilities
└── prompts/              # AI prompts
```

### Modifying the UI

**To change colors:**
Edit `static/styles.css` and update gradient values:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**To add new charts:**
1. Add chart container in `static/index.html`
2. Create render method in `static/app.js`
3. Call it from `renderCharts()` method

**To modify progress steps:**
Edit the step cards in `static/index.html`

## Alternative: Streamlit UI

If you prefer the Streamlit UI, you can still use it:

```bash
streamlit run app.py
```

Both UIs use the same backend workflow and agents.

## Support

For issues or questions:
- Check existing GitHub issues
- Review configuration in `config.py`
- Ensure all dependencies are installed
- Check server logs for errors
