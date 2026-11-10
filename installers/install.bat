@echo off
REM PPT Generator Installation Script for Windows
REM This script installs the PPT Generator application

setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════╗
echo ║   PPT Generator Installation Script   ║
echo ║            Windows Version             ║
echo ╚═══════════════════════════════════════╝
echo.

REM Configuration
set "REPO_URL=https://github.com/bornebyte/ppt-generator.git"
set "INSTALL_DIR=%USERPROFILE%\.ppt-generator"
set "ERRORS=0"

REM Check prerequisites
echo [INFO] Checking prerequisites...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or higher from https://www.python.org/
    set /a ERRORS+=1
    goto :error
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python !PYTHON_VERSION! found
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10 or higher is required.
    set /a ERRORS+=1
    goto :error
)

REM Check Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/
    set /a ERRORS+=1
    goto :error
) else (
    echo [OK] Git found
)

REM Prefer uv, but keep pip as a supported fallback.
where uv >nul 2>&1
if errorlevel 1 (
    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Neither uv nor pip is available.
        echo Install uv from https://docs.astral.sh/uv/getting-started/installation/ or enable pip in Python.
        set /a ERRORS+=1
        goto :error
    )
    set "PACKAGE_MANAGER=pip"
    echo [WARNING] uv not found; using pip fallback
) else (
    set "PACKAGE_MANAGER=uv"
    echo [OK] uv found; using uv
)

REM Check if already installed
if exist "%INSTALL_DIR%" (
    echo [WARNING] PPT Generator is already installed at %INSTALL_DIR%
    set /p "REINSTALL=Do you want to reinstall? (y/N): "
    if /i not "!REINSTALL!"=="y" (
        echo Installation cancelled.
        exit /b 0
    )
    echo [INFO] Removing existing installation...
    rmdir /s /q "%INSTALL_DIR%"
)

REM Clone repository
echo [INFO] Cloning PPT Generator repository...
git clone "%REPO_URL%" "%INSTALL_DIR%" --quiet
if errorlevel 1 (
    echo [ERROR] Failed to clone repository.
    set /a ERRORS+=1
    goto :error
)
echo [OK] Repository cloned to %INSTALL_DIR%

REM Navigate to install directory
cd /d "%INSTALL_DIR%"

echo [INFO] Installing dependencies...

REM Try to install with retries
set "MAX_RETRIES=3"
set "RETRY_COUNT=0"

:install_loop
if !RETRY_COUNT! geq !MAX_RETRIES! (
    echo [ERROR] Failed to install dependencies after !MAX_RETRIES! attempts.
    echo This might be due to network issues. Please try:
    echo   cd %INSTALL_DIR%
    echo   uv sync --no-dev
    echo   or: .venv\Scripts\python.exe -m pip install -r requirements.txt
    set /a ERRORS+=1
    goto :error
)

if "%PACKAGE_MANAGER%"=="uv" (
    uv sync --project "%INSTALL_DIR%" --no-dev
) else (
    python -m venv "%INSTALL_DIR%\.venv"
    if not errorlevel 1 "%INSTALL_DIR%\.venv\Scripts\python.exe" -m pip install -r "%INSTALL_DIR%\requirements.txt"
)
if errorlevel 1 (
    set /a RETRY_COUNT+=1
    echo [WARNING] Installation failed. Retrying (!RETRY_COUNT!/!MAX_RETRIES!)...
    timeout /t 2 >nul
    goto :install_loop
)

echo [OK] Dependencies installed

REM Create launcher batch file in user directory
echo [INFO] Creating launcher script...
set "BIN_DIR=%USERPROFILE%\bin"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

(
echo @echo off
echo REM PPT Generator Launcher
echo.
echo set "INSTALL_DIR=%INSTALL_DIR%"
echo.
echo if not exist "%%INSTALL_DIR%%" ^(
echo     echo Error: PPT Generator is not installed.
echo     exit /b 1
echo ^)
echo.
echo cd /d "%%INSTALL_DIR%%"
echo.
echo if "%%1"=="-p" ^(
echo     if "%%2"=="" ^(
echo         set PORT=5000
echo     ^) else ^(
echo         set PORT=%%2
echo     ^)
echo     echo Starting PPT Generator in production mode on port %%PORT%%...
echo     "%%INSTALL_DIR%%\.venv\Scripts\python.exe" -m gunicorn -w 4 -b 0.0.0.0:%%PORT%% main:app
echo ^) else if "%%1"=="-h" ^(
echo     echo PPT Generator CLI
echo     echo.
echo     echo Usage: pptgen [OPTIONS]
echo     echo.
echo     echo Options:
echo     echo   -p [port]    Run in production mode with Gunicorn
echo     echo   -h           Show this help message
echo ^) else ^(
echo     echo Starting PPT Generator in development mode...
echo     set FLASK_APP=main.py
echo     set FLASK_ENV=development
echo     "%%INSTALL_DIR%%\.venv\Scripts\python.exe" main.py
echo ^)
) > "%BIN_DIR%\pptgen.bat"

echo [OK] Launcher created at %BIN_DIR%\pptgen.bat

REM Check if BIN_DIR is in PATH
echo %PATH% | findstr /i "%BIN_DIR%" >nul
if errorlevel 1 (
    echo [WARNING] %BIN_DIR% is not in your PATH
    echo.
    echo To add it permanently:
    echo 1. Open System Properties ^(Win + Pause^)
    echo 2. Click "Advanced system settings"
    echo 3. Click "Environment Variables"
    echo 4. Under "User variables", select "Path" and click "Edit"
    echo 5. Click "New" and add: %BIN_DIR%
    echo 6. Click OK and restart your terminal
    echo.
    echo Or run this command in PowerShell as Administrator:
    echo [Environment]::SetEnvironmentVariable^("Path", $env:Path + ";%BIN_DIR%", "User"^)
)

REM Installation complete
echo.
echo ╔═══════════════════════════════════════╗
echo ║    Installation completed! 🎉         ║
echo ╚═══════════════════════════════════════╝
echo.
echo [INFO] PPT Generator has been installed to: %INSTALL_DIR%
echo [INFO] Launcher available: %BIN_DIR%\pptgen.bat
echo.
echo [SUCCESS] Quick start:
echo   1. Add %BIN_DIR% to your PATH ^(see instructions above^)
echo   2. Open a new terminal
echo   3. Run: pptgen
echo   4. Open browser: http://localhost:5000
echo.
echo [INFO] Or run directly: %BIN_DIR%\pptgen.bat
echo.
goto :end

:error
echo.
echo ╔═══════════════════════════════════════╗
echo ║    Installation failed with errors    ║
echo ╚═══════════════════════════════════════╝
echo.
echo Please check the errors above and try again.
exit /b 1

:end
endlocal
exit /b 0
