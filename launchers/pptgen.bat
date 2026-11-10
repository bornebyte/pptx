@echo off
REM PPT Generator CLI for Windows

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_DIR=%%~fI"
cd /d "%PROJECT_DIR%"

REM Prefer a project-local environment, then use the installer-managed environment.
set "VENV_DIR=%PROJECT_DIR%\venv"
if not exist "%VENV_DIR%" if exist "%USERPROFILE%\.ppt-generator\venv" set "VENV_DIR=%USERPROFILE%\.ppt-generator\venv"
if not exist "%VENV_DIR%" (
    echo Error: Virtual environment not found.
    echo Please run installers\install.bat first.
    exit /b 1
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Parse arguments
set "PRODUCTION=0"
set "PORT=5000"

if "%1"=="-p" (
    set "PRODUCTION=1"
    if not "%2"=="" (
        set "PORT=%2"
    )
)

if "%1"=="-h" goto :help
if "%1"=="--help" goto :help
if "%1"=="/?" goto :help

REM Start the server
if "%PRODUCTION%"=="1" (
    echo Starting PPT Generator in production mode on port %PORT%...
    echo Access the application at: http://localhost:%PORT%
    gunicorn -w 4 -b 0.0.0.0:%PORT% main:app
) else (
    echo Starting PPT Generator in development mode...
    echo Access the application at: http://localhost:5000
    set FLASK_APP=main.py
    set FLASK_ENV=development
    python main.py
)
exit /b 0

:help
echo PPT Generator CLI
echo.
echo Usage: launchers\pptgen.bat [OPTIONS]
echo.
echo Options:
echo   -p [port]    Run in production mode with Gunicorn (default port: 5000)
echo   -h           Show this help message
echo.
echo Examples:
echo   launchers\pptgen.bat              # Run development server
echo   launchers\pptgen.bat -p           # Run production server on port 5000
echo   launchers\pptgen.bat -p 8000      # Run production server on port 8000
exit /b 0
