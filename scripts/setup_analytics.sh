#!/bin/bash
set -e

# Setup script for PPT Generator with Analytics

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Setting up PPT Generator with Analytics..."

# Prefer uv, while retaining a pip installation path.
if command -v uv >/dev/null 2>&1; then
    echo "Installing dependencies with uv..."
    uv sync --project "$PROJECT_ROOT" --no-dev
else
    echo "uv not found; installing dependencies with pip..."
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi
PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your admin credentials!"
fi

# Initialize database
echo "Initializing database..."
"$PYTHON" -c "
from main import app, db
with app.app_context():
    db.create_all()
    print('✓ Database initialized successfully')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and change ADMIN_USERNAME and ADMIN_PASSWORD"
echo "2. Run the application: .venv/bin/python main.py"
echo "3. Access admin dashboard at: http://localhost:5000/admin"
echo ""
echo "Default admin credentials (CHANGE THESE!):"
echo "  Username: admin"
echo "  Password: changeme123"
