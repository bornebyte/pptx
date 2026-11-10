#!/bin/bash

# Setup Verification Script for PPT Generator
# Run this after installation to verify everything is working

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔍 Verifying PPT Generator Setup..."
echo ""

ERRORS=0

# Check if running from project directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run from project directory."
    exit 1
fi

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ Python 3 not found"
    ERRORS=$((ERRORS+1))
fi

# Check virtual environment
echo -n "Checking virtual environment... "
if [ -d ".venv" ]; then
    echo "✅ Found"
else
    echo "❌ Not found"
    ERRORS=$((ERRORS+1))
fi

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON=".venv/Scripts/python.exe"
fi

# Check dependencies
echo -n "Checking dependencies... "
if [ -f "requirements.txt" ]; then
    if [ -x "$PYTHON" ] && "$PYTHON" -c "import flask; import pptx; import gunicorn" 2>/dev/null; then
        echo "✅ All installed"
    else
        echo "❌ Missing dependencies"
        ERRORS=$((ERRORS+1))
    fi
else
    echo "❌ requirements.txt not found"
    ERRORS=$((ERRORS+1))
fi

# Check main.py syntax
echo -n "Checking main.py syntax... "
if python3 -m py_compile main.py src/main.py src/models.py 2>/dev/null; then
    echo "✅ No syntax errors"
else
    echo "❌ Syntax errors found"
    ERRORS=$((ERRORS+1))
fi

# Check templates
echo -n "Checking templates... "
if [ -f "src/templates/index.html" ] && [ -f "src/templates/base.html" ]; then
    echo "✅ Found"
else
    echo "❌ Missing templates"
    ERRORS=$((ERRORS+1))
fi

# Check executable permissions
echo -n "Checking pptgen executable... "
if [ -x "launchers/pptgen" ]; then
    echo "✅ Executable"
else
    echo "⚠️  Not executable (run: chmod +x launchers/pptgen)"
    ERRORS=$((ERRORS+1))
fi

# Check Linux/macOS installer
echo -n "Checking Linux/macOS installer... "
if [ -f "installers/install.sh" ] && [ -x "installers/install.sh" ]; then
    echo "✅ Found and executable"
else
    echo "⚠️  Not executable (run: chmod +x installers/install.sh)"
fi

# Check documentation
echo -n "Checking documentation... "
if [ -f "README.md" ]; then
    echo "✅ Found"
else
    echo "⚠️  README.md is missing"
fi

# Try to start Flask (just import test)
echo -n "Testing Flask import... "
if [ -x "$PYTHON" ] && "$PYTHON" -c "from main import app" 2>/dev/null; then
    echo "✅ Success"
else
    echo "❌ Import failed"
    ERRORS=$((ERRORS+1))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Setup is complete."
    echo ""
    echo "🚀 You can now run:"
    echo "   ./launchers/pptgen           # Development mode"
    echo "   ./launchers/pptgen -p        # Production mode"
    echo "   .venv/bin/python main.py     # Direct Python (Windows: .venv/Scripts/python.exe)"
    echo "   ./scripts/verify_setup.sh    # Run this setup check again"
    echo ""
    echo "📖 Visit http://localhost:5000 after starting"
else
    echo "❌ Found $ERRORS error(s). Please fix them before running."
    echo ""
    echo "💡 Common fixes:"
    echo "   - Preferred: uv sync; fallback: .venv/bin/python -m pip install -r requirements.txt"
    echo "   - Run: chmod +x launchers/pptgen installers/install.sh"
    echo "   - Make sure you're in the project directory"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit $ERRORS
