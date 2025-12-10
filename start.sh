#!/bin/bash

# AI PR Code Review System Launcher
# Quick start script for both UI options

clear
echo "======================================"
echo "  AI PR Code Review System Launcher"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Check if config.py exists
if [ ! -f "config.py" ]; then
    echo "⚠️  config.py not found!"
    if [ -f "config.py.template" ]; then
        echo "Creating config.py from template..."
        cp config.py.template config.py
        echo "✅ config.py created"
        echo "⚠️  Please edit config.py and add your API keys before continuing"
        echo ""
        read -p "Press Enter to continue after editing config.py..."
    else
        echo "❌ config.py.template not found!"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

echo ""
echo "======================================"
echo "Starting JavaScript UI..."
echo "======================================"
echo ""
echo "Server will start at: http://localhost:5000"
echo "Press CTRL+C to stop the server"
echo ""
python server.py
