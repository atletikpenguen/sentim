#!/bin/bash

# Sentimentalgo Scraper Run Script
# Scraper'ı çalıştırmak için basit script

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found!"
    echo "Please run setup.sh first."
    exit 1
fi

# Check for credentials
if [ ! -f "credentials.json" ]; then
    echo "ERROR: credentials.json not found!"
    echo "Please add your Google Service Account credentials."
    exit 1
fi

# Run the scraper
echo "Starting scraper..."
python3 scraper.py

# Deactivate virtual environment
deactivate
