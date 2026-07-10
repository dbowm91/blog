#!/usr/bin/env bash
set -e

# Parse arguments
DEV=false
for arg in "$@"; do
    case "$arg" in
        --dev) DEV=true ;;
        *) echo "Unknown option: $arg"; echo "Usage: $0 [--dev]"; exit 1 ;;
    esac
done

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
if [ "$DEV" = true ]; then
    echo "Installing dependencies (dev)..."
    pip install -r requirements-dev.txt
else
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

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
mkdir -p instance logs app/static/uploads

# Create config.toml from example if it doesn't exist
if [ ! -f "config.toml" ] && [ -f "config.toml.example" ]; then
    cp config.toml.example config.toml
    echo "Created config.toml from config.toml.example."
    echo "Review config.toml and adjust settings as needed."
fi

# Source .env so variables are available in the current shell
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "Environment variables loaded from .env."
fi

# Run database migrations
echo "Running database migrations..."
if ! ( cd "$(dirname "$0")" && venv/bin/python -m flask db upgrade ); then
    echo "Error: Database migrations failed."
    echo "Please fix the issue and run 'venv/bin/python -m flask db upgrade' manually before starting the app."
    exit 1
fi

# Build frontend assets
echo "Building frontend assets..."
if command -v npm &> /dev/null; then
    if ! ( cd "$(dirname "$0")" && npm ci && npm run build ); then
        echo "Warning: Frontend build failed. Admin UI may not work correctly."
        echo "Run 'npm ci && npm run build' manually to build frontend assets."
    fi
else
    echo "Warning: npm not found. Frontend assets not built."
    echo "Install Node.js and run 'npm ci && npm run build' to build frontend assets."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
if [ "$DEV" = true ]; then
    echo "Dev dependencies installed (includes pytest)."
else
    echo "Production dependencies installed. For dev, rerun with: ./setup.sh --dev"
fi
echo ""
echo "To start the application:"
echo "  venv/bin/python run.py"
echo ""
echo "Visit http://localhost:5000"
echo "Admin login at http://localhost:5000/admin/login"
