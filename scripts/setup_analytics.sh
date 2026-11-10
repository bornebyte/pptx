#!/bin/bash

# Setup script for PPT Generator with Analytics

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Setting up PPT Generator with Analytics..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
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

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your admin credentials!"
fi

# Initialize database
echo "Initializing database..."
python3 -c "
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
echo "2. Run the application: python3 main.py"
echo "3. Access admin dashboard at: http://localhost:5000/admin"
echo ""
echo "Default admin credentials (CHANGE THESE!):"
echo "  Username: admin"
echo "  Password: changeme123"
