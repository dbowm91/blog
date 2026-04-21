#!/usr/bin/env bash
set -e

echo "=== Blog CMS Development Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 14 ]); then
    echo "Error: Python 3.14 or higher is required. Found: Python $PYTHON_VERSION"
    exit 1
fi

echo "Python version: $PYTHON_VERSION ✓"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Create config.toml from config.toml if it doesn't exist
if [ ! -f "config.toml" ]; then
    if [ -f "config.toml.example" ]; then
        echo "Creating config.toml from example..."
        cp config.toml.example config.toml
    else
        echo "Warning: No config.toml.example found. Skipping config setup."
    fi
else
    echo "config.toml already exists. Skipping."
fi

# Create required directories
mkdir -p instance logs app/static/uploads

# Run database migrations
echo "Running database migrations..."
flask db upgrade

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Required environment variables:"
echo "  SECRET_KEY    - Session secret (min 32 chars)"
echo "  ADMIN_PASSWORD - Admin login password"
echo ""
echo "Optional environment variables:"
echo "  ADMIN_USERNAME - Admin username (default: admin)"
echo "  SMTP_USER      - SMTP username for email"
echo "  SMTP_PASSWORD  - SMTP password for email"
echo ""
echo "To start the development server:"
echo "  source venv/bin/activate"
echo "  SECRET_KEY=<your-secret-key> ADMIN_PASSWORD=<your-password> flask run"
echo ""
echo "Or set environment variables in a .env file and use:"
echo "  source venv/bin/activate"
echo "  flask run"
