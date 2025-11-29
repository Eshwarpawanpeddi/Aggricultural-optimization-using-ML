#!/bin/bash

echo "================================"
echo "Precision Crop Management System"
echo "================================"
echo ""

echo "Step 1: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python $PYTHON_VERSION found"
echo ""

echo "Step 2: Installing dependencies..."
if pip3 install -r requirements.txt; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi
echo ""

echo "Step 3: Preparing templates directory..."
if [ ! -d "templates" ]; then
    mkdir templates
    echo "✓ Templates directory created"
else
    echo "✓ Templates directory exists"
fi
echo ""

echo "Step 4: Starting application..."
echo "Server will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
