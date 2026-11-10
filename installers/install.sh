#!/bin/bash

# PPT Generator Installation Script
# This script installs the PPT Generator application and sets up the CLI
# Supports: Linux and macOS

set -e  # Exit on error

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

if [ "$MACHINE" = "UNKNOWN:${OS}" ]; then
    echo "Error: Unsupported operating system: ${OS}"
    echo "This script supports Linux and macOS only."
    echo "For Windows, please use installers/install.bat or installers/install.ps1"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/bornebyte/ppt-generator.git"
INSTALL_DIR="$HOME/.ppt-generator"
BIN_DIR="$HOME/.local/bin"

# Functions
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Start installation
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   PPT Generator Installation Script   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

if ! check_command python3; then
    print_error "Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    print_error "Python 3.10 or higher is required. Found $(python3 --version)."
    exit 1
fi

PYTHON_VERSION="$PYTHON_MAJOR.$PYTHON_MINOR"
print_success "Python $PYTHON_VERSION found"

if ! check_command git; then
    print_error "Git is not installed. Please install git."
    exit 1
fi
print_success "Git found"

if check_command uv; then
    PACKAGE_MANAGER=uv
    print_success "uv found ($(uv --version)); using uv"
elif python3 -m pip --version >/dev/null 2>&1; then
    PACKAGE_MANAGER=pip
    print_warning "uv not found; falling back to pip"
else
    print_error "Neither uv nor pip is available. Install uv from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    print_warning "PPT Generator is already installed at $INSTALL_DIR"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    else
        print_info "Installation cancelled."
        exit 0
    fi
fi

# Clone repository
print_info "Cloning PPT Generator repository..."
git clone "$REPO_URL" "$INSTALL_DIR" --quiet
print_success "Repository cloned to $INSTALL_DIR"

# Navigate to install directory
cd "$INSTALL_DIR"

# Create the uv-managed environment or use pip as a fallback
print_info "Installing dependencies with $PACKAGE_MANAGER..."

# Try to install with increased timeout and retries
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if [ "$PACKAGE_MANAGER" = "uv" ]; then
        if [ -f "$INSTALL_DIR/pyproject.toml" ]; then
            if uv sync --project "$INSTALL_DIR" --no-dev; then
                INSTALL_SUCCEEDED=1
            else
                INSTALL_SUCCEEDED=0
            fi
        elif [ -f "$INSTALL_DIR/requirements.txt" ]; then
            # Older repository revisions have requirements.txt but no
            # pyproject.toml, so install those dependencies into the same
            # .venv expected by the launchers.
            if uv venv "$INSTALL_DIR/.venv" && \
                uv pip install --python "$INSTALL_DIR/.venv/bin/python" -r "$INSTALL_DIR/requirements.txt"; then
                INSTALL_SUCCEEDED=1
            else
                INSTALL_SUCCEEDED=0
            fi
        else
            print_error "No pyproject.toml or requirements.txt found in $INSTALL_DIR."
            INSTALL_SUCCEEDED=0
        fi
    else
        if python3 -m venv "$INSTALL_DIR/.venv" && \
            "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"; then
            INSTALL_SUCCEEDED=1
        else
            INSTALL_SUCCEEDED=0
        fi
    fi
    if [ "$INSTALL_SUCCEEDED" -eq 1 ]; then
        print_success "Dependencies installed"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            print_warning "Installation failed. Retrying ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 2
        else
            print_error "Failed to install dependencies after $MAX_RETRIES attempts."
            print_info "Retry the dependency install with either package manager:"
            echo "  cd $INSTALL_DIR"
            echo "  uv sync --no-dev"
            echo "  # or: .venv/bin/python -m pip install -r requirements.txt"
            exit 1
        fi
    fi
done

# Create bin directory if it doesn't exist
if [ ! -d "$BIN_DIR" ]; then
    mkdir -p "$BIN_DIR"
    print_info "Created $BIN_DIR directory"
fi

# Create CLI script
print_info "Creating CLI command..."
cat > "$BIN_DIR/pptgen" << 'EOF'
#!/bin/bash
# PPT Generator CLI

INSTALL_DIR="$HOME/.ppt-generator"

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: PPT Generator is not installed."
    echo "Run: curl -sSL https://raw.githubusercontent.com/bornebyte/ppt-generator/main/installers/install.sh | bash"
    exit 1
fi

cd "$INSTALL_DIR"

# Parse arguments
PRODUCTION=0
PORT=5000

while getopts "p:h" opt; do
    case $opt in
        p)
            PRODUCTION=1
            if [ ! -z "$OPTARG" ] && [ "$OPTARG" != "-"* ]; then
                PORT=$OPTARG
            fi
            ;;
        h)
            echo "PPT Generator CLI"
            echo ""
            echo "Usage: pptgen [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -p [port]    Run in production mode with Gunicorn (default port: 5000)"
            echo "  -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  pptgen              # Run development server"
            echo "  pptgen -p           # Run production server on port 5000"
            echo "  pptgen -p 8000      # Run production server on port 8000"
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

# Start the server
if [ $PRODUCTION -eq 1 ]; then
    echo "Starting PPT Generator in production mode on port $PORT..."
    "$INSTALL_DIR/.venv/bin/python" -m gunicorn -w 4 -b 0.0.0.0:$PORT main:app
else
    echo "Starting PPT Generator in development mode..."
    export FLASK_APP=main.py
    export FLASK_ENV=development
    "$INSTALL_DIR/.venv/bin/python" main.py
fi
EOF

chmod +x "$BIN_DIR/pptgen"
print_success "CLI command created at $BIN_DIR/pptgen"

# Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    print_warning "$BIN_DIR is not in your PATH"
    
    # Detect shell
    SHELL_NAME=$(basename "$SHELL")
    if [ "$SHELL_NAME" = "bash" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ "$SHELL_NAME" = "zsh" ]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.profile"
    fi
    
    print_info "Adding $BIN_DIR to PATH in $SHELL_RC"
    echo "" >> "$SHELL_RC"
    echo "# PPT Generator CLI" >> "$SHELL_RC"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
    print_success "PATH updated in $SHELL_RC"
    print_warning "Please restart your terminal or run: source $SHELL_RC"
fi

# Installation complete
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Installation completed! 🎉         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
print_info "PPT Generator has been installed to: $INSTALL_DIR"
print_info "CLI command available: pptgen"
echo ""
print_success "Quick start:"
echo "  1. Restart your terminal or run: source $SHELL_RC"
echo "  2. Run: pptgen"
echo "  3. Open browser: http://localhost:5000"
echo ""
print_info "For production mode: pptgen -p"
print_info "For help: pptgen -h"
echo ""
