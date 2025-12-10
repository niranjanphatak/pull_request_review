# 📋 Quick Commands Reference

## 🚀 Start Server

### Easiest Way
```bash
./start.sh
```

### Direct Command
```bash
source venv/bin/activate
python server.py
```

### Then Open
```
http://localhost:5000
```

---

## 🛑 Stop Server

### Option 1: Terminal (Recommended)
Press `CTRL+C` in the terminal where server is running

### Option 2: Stop Script
```bash
./stop.sh
```

### Option 3: Manual Kill
```bash
lsof -ti :5000 | xargs kill -9
```

---

## ⚙️ Configuration

### First Time Setup
```bash
# 1. Create config
cp config.py.template config.py

# 2. Edit with your API key
nano config.py

# 3. Start server
./start.sh
```

### Check Server Status
```bash
lsof -i :5000
```

### View Server Logs
Server logs appear in the terminal where you started it

---

## 🔧 Troubleshooting

### Port Already in Use
```bash
lsof -ti :5000 | xargs kill -9
```

### Reinstall Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Reset Virtual Environment
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Check Config
```bash
cat config.py
```

---

## 📝 Project Structure

```bash
# View all Python files
find . -name "*.py" -not -path "./venv/*"

# View all JavaScript files
find static -name "*.js"

# View all documentation
ls *.md
```

---

## 🗂️ File Locations

| What | Location |
|------|----------|
| Main Server | `server.py` |
| HTML | `static/index.html` |
| CSS | `static/styles.css` |
| JavaScript | `static/app.js` |
| Config | `config.py` |
| AI Prompts | `prompts/*.txt` |
| Start Script | `start.sh` |
| Stop Script | `stop.sh` |

---

## 🎯 Common Tasks

### Update AI Prompts
```bash
# Edit any prompt file
nano prompts/security_review.txt
nano prompts/bug_detection.txt
nano prompts/style_optimization.txt
nano prompts/test_suggestions.txt

# Restart server to apply changes
./stop.sh
./start.sh
```

### Change AI Model
```bash
# Edit config.py
nano config.py

# Change AI_MODEL value:
AI_MODEL = 'gemini-2.5-flash-lite'  # Fast
AI_MODEL = 'gemini-1.5-pro'         # More accurate
AI_MODEL = 'gpt-4o-mini'            # Alternative provider

# Restart server
./stop.sh
./start.sh
```

### View Temp Repositories
```bash
ls -la temp_repos/
```

### Clean Temp Files
```bash
rm -rf temp_repos/*
```

---

## 🌐 Access URLs

| URL | Purpose |
|-----|---------|
| http://localhost:5000 | Main UI |
| http://localhost:5000/health | Health Check |
| http://localhost:5000/api/review | API Endpoint (POST) |

---

## 📊 Testing

### Test with Sample PR
```
PR URL: https://github.com/python/cpython/pull/100000
Repo URL: https://github.com/python/cpython
```

### Small Test PR
```
PR URL: https://github.com/octocat/Hello-World/pull/1
Repo URL: https://github.com/octocat/Hello-World
```

---

## 🔐 Security

### Never Commit
- ❌ `config.py` (contains API keys)
- ❌ `.env` files
- ❌ `temp_repos/` directory

### Safe to Commit
- ✅ `config.py.template`
- ✅ All code files
- ✅ Documentation
- ✅ Shell scripts

---

## 🆘 Get Help

1. Check logs in terminal
2. Read [README.md](README.md)
3. Read [HOW_TO_START.md](HOW_TO_START.md)
4. Check [JAVASCRIPT_UI.md](JAVASCRIPT_UI.md)

---

**Quick Start**: `./start.sh` → Open http://localhost:5000 🚀
