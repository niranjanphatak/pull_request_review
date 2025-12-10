# 🚀 How to Start

## Quick Start

```bash
./start.sh
```

Then open: **http://localhost:5000**

---

## Manual Start

```bash
source venv/bin/activate
python server.py
```

Then open: **http://localhost:5000**

---

## First Time Setup

1. **Create config**:
   ```bash
   cp config.py.template config.py
   ```

2. **Add your API key** to `config.py`:
   ```python
   AI_API_KEY = 'your_actual_key_here'
   ```

3. **Start**:
   ```bash
   ./start.sh
   ```

---

## Usage

1. Open http://localhost:5000
2. Enter PR URL: `https://github.com/owner/repo/pull/123`
3. Enter Repo URL: `https://github.com/owner/repo`
4. Click "🚀 Start Review"
5. View results and download reports

---

## Get API Key

**Gemini (Free)**: https://aistudio.google.com/apikey

---

## Stop Server

### Method 1: Using Terminal
Press `CTRL+C` in the terminal where server is running

### Method 2: Using Stop Script
```bash
./stop.sh
```

### Method 3: Manual Kill
```bash
lsof -ti :5000 | xargs kill -9
```

---

See [README.md](README.md) for full documentation.
