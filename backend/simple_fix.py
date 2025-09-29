# simple_fix.py
import subprocess
import sys
import os

print("Simple fix for main.py encoding issues...\n")

# Use sed-like replacement with PowerShell (works on Windows)
try:
    # First, let's check if the backend runs with the current main.py
    print("Testing if we can start uvicorn directly...")
    
    # Try to start uvicorn, ignoring the exec error
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    subprocess.run([
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ], env=env)
    
except KeyboardInterrupt:
    print("\nServer stopped.")
except Exception as e:
    print(f"Error: {e}")
    print("\nTry running the minimal server instead:")
    print("  python minimal_main.py")
