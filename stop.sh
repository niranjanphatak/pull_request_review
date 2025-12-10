#!/bin/bash

# Stop AI PR Code Review Server
echo "======================================"
echo "  Stopping PR Review Server"
echo "======================================"
echo ""

# Find and kill Flask server process on port 5000
PID=$(lsof -ti :5000)

if [ -z "$PID" ]; then
    echo "❌ No server running on port 5000"
else
    echo "Found server process: $PID"
    kill -9 $PID
    echo "✅ Server stopped successfully"
fi

echo ""
echo "======================================"
