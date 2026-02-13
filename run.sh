#!/bin/bash

echo "🚀 BridgeGen Application Launcher"
echo "=================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

echo "✅ pip found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Start the application
echo ""
echo "🌟 Starting BridgeGen Flask Application..."
echo ""
echo "📍 Access the application at:"
echo "   - http://127.0.0.1:5000"
echo "   - http://localhost:5000"
echo ""
echo "⚠️  Press CTRL+C to stop the server"
echo ""
echo "============================================"
echo ""

python3 app.py
