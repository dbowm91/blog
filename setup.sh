#!/usr/bin/env bash
set -e

echo "=== DevLog Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]); then
    echo "Error: Python 3.12 or higher is required. Found: Python $PYTHON_VERSION"
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
pip install -r requirements-dev.txt

# Generate .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Generating .env file..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > .env << EOF
# Required
SECRET_KEY=$SECRET_KEY

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

# SMTP (optional — leave blank to disable email)
SMTP_USER=
SMTP_PASSWORD=
EOF
    echo ".env file created with random SECRET_KEY and ADMIN_PASSWORD."
    echo "Review .env and update SMTP settings if needed."
else
    echo ".env file already exists. Skipping."
fi

# Create required directories
mkdir -p instance logs static/uploads

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  python run.py"
echo ""
echo "Visit http://localhost:5000"
echo "Admin login at http://localhost:5000/admin/login"
