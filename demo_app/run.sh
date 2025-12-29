#!/bin/bash

echo "=========================================="
echo "🚀 SQLAdmin Demo Application Setup"
echo "=========================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -e ..
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting application..."
echo "   Admin interface: http://localhost:8000/admin"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the application
python main.py

