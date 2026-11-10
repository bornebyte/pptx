# PPT Generator CLI for Windows PowerShell

param(
    [switch]$Production,
    [switch]$Help,
    [int]$Port = 5000
)

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = (Resolve-Path (Join-Path $SCRIPT_DIR "..")).Path
Set-Location $PROJECT_DIR

$VENV_DIR = Join-Path $PROJECT_DIR ".venv"
if (-not (Test-Path $VENV_DIR) -and (Test-Path "$env:USERPROFILE\.ppt-generator\.venv")) {
    $VENV_DIR = "$env:USERPROFILE\.ppt-generator\.venv"
}

if (-not (Test-Path $VENV_DIR)) {
    Write-Host "Error: Virtual environment not found." -ForegroundColor Red
    Write-Host "Please run installers\install.ps1 first." -ForegroundColor Yellow
    exit 1
}


# Show help
if ($Help) {
    Write-Host "PPT Generator CLI" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\launchers\pptgen.ps1 [OPTIONS]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -Production    Run in production mode with Gunicorn"
    Write-Host "  -Port [num]    Specify port (default: 5000)"
    Write-Host "  -Help          Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\launchers\pptgen.ps1                    # Run development server"
    Write-Host "  .\launchers\pptgen.ps1 -Production        # Run production server"
    Write-Host "  .\launchers\pptgen.ps1 -Production -Port 8000  # Custom port"
    exit 0
}

# Start the server
if ($Production) {
    Write-Host "Starting PPT Generator in production mode on port $Port..." -ForegroundColor Green
    Write-Host "Access the application at: http://localhost:$Port" -ForegroundColor Cyan
    & "$VENV_DIR\Scripts\python.exe" -m gunicorn -w 4 -b "0.0.0.0:$Port" main:app
}
else {
    Write-Host "Starting PPT Generator in development mode..." -ForegroundColor Green
    Write-Host "Access the application at: http://localhost:5000" -ForegroundColor Cyan
    $env:FLASK_APP = "main.py"
    $env:FLASK_ENV = "development"
    & "$VENV_DIR\Scripts\python.exe" main.py
}
