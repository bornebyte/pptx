#!/usr/bin/env python3
"""
PPT Generator Universal Launcher
Cross-platform Python launcher for PPT Generator
Works on Windows, macOS, and Linux
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).resolve().parent.parent

def check_venv():
    """Check if virtual environment exists"""
    script_dir = get_script_dir()
    venv_dir = script_dir / "venv"
    if not venv_dir.exists():
        installed_venv = Path.home() / ".ppt-generator" / "venv"
        if installed_venv.exists():
            venv_dir = installed_venv
    
    if not venv_dir.exists():
        print("❌ Error: Virtual environment not found.")
        print("Please run the installation script first:")
        if platform.system() == "Windows":
            print("  installers\\install.bat  (or)  powershell -File installers\\install.ps1")
        else:
            print("  ./installers/install.sh")
        sys.exit(1)
    
    return venv_dir

def get_python_executable(venv_dir):
    """Get the Python executable path from venv"""
    system = platform.system()
    
    if system == "Windows":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
    
    if not python_exe.exists():
        print(f"❌ Error: Python executable not found at {python_exe}")
        sys.exit(1)
    
    return str(python_exe)

def show_help():
    """Show help message"""
    print("PPT Generator CLI")
    print()
    print("Usage: python launchers/pptgen-launcher.py [OPTIONS]")
    print()
    print("Options:")
    print("  -p, --production [port]    Run in production mode (default port: 5000)")
    print("  -h, --help                 Show this help message")
    print()
    print("Examples:")
    print("  python launchers/pptgen-launcher.py              # Development mode")
    print("  python launchers/pptgen-launcher.py -p           # Production mode")
    print("  python launchers/pptgen-launcher.py -p 8000      # Production on port 8000")
    print()

def main():
    """Main launcher function"""
    script_dir = get_script_dir()
    os.chdir(script_dir)
    
    # Parse arguments
    args = sys.argv[1:]
    production = False
    port = 5000
    
    if '-h' in args or '--help' in args:
        show_help()
        return 0
    
    if '-p' in args or '--production' in args:
        production = True
        # Try to get port from next argument
        try:
            idx = args.index('-p') if '-p' in args else args.index('--production')
            if idx + 1 < len(args) and args[idx + 1].isdigit():
                port = int(args[idx + 1])
        except (ValueError, IndexError):
            pass
    
    # Check virtual environment
    venv_dir = check_venv()
    python_exe = get_python_executable(venv_dir)
    
    try:
        if production:
            print(f"🚀 Starting PPT Generator in production mode on port {port}...")
            print(f"📖 Access at: http://localhost:{port}")
            
            # Check if gunicorn is available
            result = subprocess.run(
                [python_exe, "-m", "pip", "show", "gunicorn"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("❌ Error: Gunicorn not found. Installing...")
                subprocess.run([python_exe, "-m", "pip", "install", "gunicorn"], check=True)
            
            # Run with gunicorn
            subprocess.run([
                python_exe, "-m", "gunicorn",
                "-w", "4",
                "-b", f"0.0.0.0:{port}",
                "main:app"
            ], check=True)
        else:
            print("🚀 Starting PPT Generator in development mode...")
            print("📖 Access at: http://localhost:5000")
            
            env = os.environ.copy()
            env["FLASK_APP"] = "main.py"
            env["FLASK_ENV"] = "development"
            
            subprocess.run([python_exe, "main.py"], env=env, check=True)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running server: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
