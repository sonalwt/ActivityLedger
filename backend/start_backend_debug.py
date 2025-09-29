# start_backend_debug.py
import os
import sys
import subprocess
from pathlib import Path

def start_backend():
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print(f"Current directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    # Check if main.py exists
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found in backend directory!")
        return
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found. Using .env.example if available...")
        if os.path.exists(".env.example"):
            print("Creating .env from .env.example...")
            import shutil
            shutil.copy(".env.example", ".env")
    
    # Try to run the backend with detailed output
    print("\n=== Starting Backend Server ===")
    try:
        # Run with python directly to see all errors
        subprocess.run([
            sys.executable, 
            "-m", 
            "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTrying alternative method...")
        
        # Try running main.py directly
        try:
            subprocess.run([sys.executable, "main.py"])
        except Exception as e2:
            print(f"❌ Alternative method also failed: {e2}")

if __name__ == "__main__":
    start_backend()