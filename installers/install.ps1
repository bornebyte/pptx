# PPT Generator Installation Script for Windows PowerShell
# Run with: powershell -ExecutionPolicy Bypass -File installers/install.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   PPT Generator Installation Script   ║" -ForegroundColor Green
Write-Host "║        PowerShell Version             ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Configuration
$REPO_URL = "https://github.com/bornebyte/ppt-generator.git"
$INSTALL_DIR = "$env:USERPROFILE\.ppt-generator"
$BIN_DIR = "$env:USERPROFILE\bin"

function Write-Info {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Message {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

try {
    # Check prerequisites
    Write-Info "Checking prerequisites..."

    # Check Python
    try {
        $pythonVersion = (python --version 2>&1) -replace "Python ", ""
        Write-Success "Python $pythonVersion found"
    }
    catch {
        Write-Error-Message "Python is not installed or not in PATH."
        Write-Host "Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Yellow
        exit 1
    }
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Python 3.10 or higher is required."
        exit 1
    }

    # Check Git
    try {
        $null = git --version 2>&1
        Write-Success "Git found"
    }
    catch {
        Write-Error-Message "Git is not installed or not in PATH."
        Write-Host "Please install Git from https://git-scm.com/" -ForegroundColor Yellow
        exit 1
    }

    # Check pip
    try {
        $null = python -m pip --version 2>&1
        Write-Success "pip found"
    }
    catch {
        Write-Error-Message "pip is not installed."
        Write-Host "Please install pip or reinstall Python with pip included." -ForegroundColor Yellow
        exit 1
    }

    # Check if already installed
    if (Test-Path $INSTALL_DIR) {
        Write-Warning "PPT Generator is already installed at $INSTALL_DIR"
        $response = Read-Host "Do you want to reinstall? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Installation cancelled."
            exit 0
        }
        Write-Info "Removing existing installation..."
        Remove-Item -Path $INSTALL_DIR -Recurse -Force
    }

    # Clone repository
    Write-Info "Cloning PPT Generator repository..."
    git clone $REPO_URL $INSTALL_DIR --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clone repository"
    }
    Write-Success "Repository cloned to $INSTALL_DIR"

    # Navigate to install directory
    Set-Location $INSTALL_DIR

    # Create virtual environment
    Write-Info "Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
    Write-Success "Virtual environment created"

    # Activate virtual environment and install dependencies
    Write-Info "Installing dependencies..."
    & "$INSTALL_DIR\venv\Scripts\Activate.ps1"

    # Try to install with retries
    $MAX_RETRIES = 3
    $RETRY_COUNT = 0
    $installed = $false

    while ($RETRY_COUNT -lt $MAX_RETRIES -and -not $installed) {
        try {
            python -m pip install --upgrade pip --quiet --timeout 300 2>&1 | Out-Null
            python -m pip install -r requirements.txt --quiet --timeout 300 2>&1 | Out-Null
            $installed = $true
            Write-Success "Dependencies installed"
        }
        catch {
            $RETRY_COUNT++
            if ($RETRY_COUNT -lt $MAX_RETRIES) {
                Write-Warning "Installation failed. Retrying ($RETRY_COUNT/$MAX_RETRIES)..."
                Start-Sleep -Seconds 2
            }
            else {
                Write-Error-Message "Failed to install dependencies after $MAX_RETRIES attempts."
                Write-Host "This might be due to network issues. Please try:" -ForegroundColor Yellow
                Write-Host "  cd $INSTALL_DIR" -ForegroundColor Yellow
                Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
                Write-Host "  pip install -r requirements.txt --timeout 300" -ForegroundColor Yellow
                exit 1
            }
        }
    }

    # Create bin directory if it doesn't exist
    if (-not (Test-Path $BIN_DIR)) {
        New-Item -ItemType Directory -Path $BIN_DIR | Out-Null
        Write-Info "Created $BIN_DIR directory"
    }

    # Create launcher batch file
    Write-Info "Creating launcher scripts..."
    
    # Create .bat launcher
    $batContent = @"
@echo off
REM PPT Generator Launcher

set "INSTALL_DIR=$INSTALL_DIR"

if not exist "%INSTALL_DIR%" (
    echo Error: PPT Generator is not installed.
    exit /b 1
)

cd /d "%INSTALL_DIR%"
call venv\Scripts\activate.bat

if "%1"=="-p" (
    if "%2"=="" (
        set PORT=5000
    ) else (
        set PORT=%2
    )
    echo Starting PPT Generator in production mode on port %PORT%...
    gunicorn -w 4 -b 0.0.0.0:%PORT% main:app
) else if "%1"=="-h" (
    echo PPT Generator CLI
    echo.
    echo Usage: pptgen [OPTIONS]
    echo.
    echo Options:
    echo   -p [port]    Run in production mode with Gunicorn
    echo   -h           Show this help message
) else (
    echo Starting PPT Generator in development mode...
    set FLASK_APP=main.py
    set FLASK_ENV=development
    python main.py
)
"@
    
    $batContent | Out-File -FilePath "$BIN_DIR\pptgen.bat" -Encoding ASCII
    Write-Success "Launcher created at $BIN_DIR\pptgen.bat"

    # Check if BIN_DIR is in PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$BIN_DIR*") {
        Write-Warning "$BIN_DIR is not in your PATH"
        Write-Host ""
        Write-Host "Adding $BIN_DIR to your PATH..." -ForegroundColor Yellow
        
        try {
            $newPath = "$currentPath;$BIN_DIR"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Write-Success "PATH updated. Please restart your terminal."
        }
        catch {
            Write-Warning "Could not automatically add to PATH. Please add manually:"
            Write-Host "  [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$BIN_DIR', 'User')" -ForegroundColor Yellow
        }
    }

    # Installation complete
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║    Installation completed! 🎉         ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Info "PPT Generator has been installed to: $INSTALL_DIR"
    Write-Info "Launcher available: $BIN_DIR\pptgen.bat"
    Write-Host ""
    Write-Success "Quick start:"
    Write-Host "  1. Restart your terminal" -ForegroundColor Cyan
    Write-Host "  2. Run: pptgen" -ForegroundColor Cyan
    Write-Host "  3. Open browser: http://localhost:5000" -ForegroundColor Cyan
    Write-Host ""
    Write-Info "Or run directly: $BIN_DIR\pptgen.bat"
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║    Installation failed with errors    ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}
