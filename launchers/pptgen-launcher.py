#!/usr/bin/env python3
"""
PPT Generator Universal Launcher
Cross-platform Python launcher for PPT Generator
Works on Windows, macOS, and Linux
"""

import os
import sys
import subprocess
from pathlib import Path

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).resolve().parent.parent

def get_python_executable():
    """Find the project's virtualenv interpreter (created by uv or pip)."""
    script_dir = get_script_dir()
    venv_dir = script_dir / ".venv"
    if not venv_dir.exists():
        installed_venv = Path.home() / ".ppt-generator" / ".venv"
        if installed_venv.exists():
            venv_dir = installed_venv
    if not venv_dir.exists():
        print("❌ Virtual environment not found. Run the platform installer, `uv sync`, or create .venv and install requirements.txt with pip.")
        sys.exit(1)
    executable = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.exists():
        print(f"❌ Python interpreter not found in {venv_dir}.")
        sys.exit(1)
    return executable

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
    
    python_executable = get_python_executable()
    env = os.environ.copy()
    
    try:
        if production:
            print(f"🚀 Starting PPT Generator in production mode on port {port}...")
            print(f"📖 Access at: http://localhost:{port}")
            
            # Run with gunicorn
            subprocess.run([
                str(python_executable), "-m", "gunicorn",
                "-w", "4",
                "-b", f"0.0.0.0:{port}",
                "main:app"
            ], env=env, check=True)
        else:
            print("🚀 Starting PPT Generator in development mode...")
            print("📖 Access at: http://localhost:5000")
            
            env = os.environ.copy()
            env["FLASK_APP"] = "main.py"
            env["FLASK_ENV"] = "development"
            
            subprocess.run([str(python_executable), "main.py"], env=env, check=True)
    
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
