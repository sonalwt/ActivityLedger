# debug_backend_simple.py
import socket
import subprocess
import sys
import os
import time
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def main():
    print("=== Simple Backend Debug ===\n")
    
    # 1. Check Python version
    print(f"Python version: {sys.version}\n")
    
    # 2. Check if we're in the right directory
    backend_dir = Path(__file__).parent / "backend"
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return
    
    os.chdir(backend_dir)
    print(f"Working directory: {os.getcwd()}\n")
    
    # 3. Check if port 8000 is in use
    print("Checking port 8000...")
    if check_port(8000):
        print("❌ Port 8000 is already in use!")
        print("Try: netstat -ano | findstr :8000")
        print("Then kill the process using: taskkill /PID <pid> /F")
    else:
        print("✅ Port 8000 is available\n")
    
    # 4. Test import
    print("Testing backend import...")
    try:
        sys.path.insert(0, os.getcwd())
        import main
        print("✅ Backend imports successfully\n")
        
        # Check if app exists
        if hasattr(main, 'app'):
            print("✅ FastAPI app found")
        else:
            print("❌ FastAPI app not found in main.py")
            
    except Exception as e:
        print(f"❌ Import error: {e}\n")
        import traceback
        traceback.print_exc()
    
    # 5. Try to start backend
    print("\n=== Attempting to start backend ===")
    print("Running: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run([
            sys.executable,
            "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--log-level", "debug"
        ])
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start: {e}")

if __name__ == "__main__":
    main()
