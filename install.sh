#!/bin/bash

# Installation and Quick Test Script for OLX Apartment Scraper

echo "======================================"
echo "OLX Apartment Scraper - Installation"
echo "======================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python is installed"
echo ""

# Create virtual environment
echo "2. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "3. Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "4. Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Initialize configuration
echo "5. Initializing configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Configuration file created (.env)"
else
    echo "✓ Configuration file already exists"
fi
echo ""

# Create necessary directories
echo "6. Creating directories..."
mkdir -p cache data logs
echo "✓ Directories created"
echo ""

# Make scripts executable
echo "7. Setting permissions..."
chmod +x main.py cli.py
echo "✓ Scripts are now executable"
echo ""

echo "======================================"
echo "Installation Complete! ✓"
echo "======================================"
echo ""
echo "Quick Test:"
echo "  python main.py scrape -p 2"
echo ""
echo "View Statistics:"
echo "  python main.py stats"
echo ""
echo "Export Data:"
echo "  python main.py export"
echo ""
echo "For more information, see:"
echo "  - QUICKSTART.txt - Quick start guide"
echo "  - README_USAGE.md - Full documentation"
echo "  - EXAMPLES.py - Usage examples"
echo ""

# Ask if user wants to run a test
read -p "Do you want to run a quick test now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo ""
    echo "Running test scrape (first 2 pages)..."
    python main.py scrape -p 2
    
    echo ""
    echo "Showing statistics..."
    python main.py stats
fi

echo ""
echo "Setup complete! You can now use the scraper."
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
