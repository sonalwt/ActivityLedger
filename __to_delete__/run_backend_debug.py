# run_backend_debug.py
import os
import sys
import subprocess
from pathlib import Path

def run_backend_with_debug():
    # Get the backend directory
    backend_dir = Path(__file__).parent / "backend"
    
    # Change to backend directory
    os.chdir(backend_dir)
    print(f"Changed to directory: {os.getcwd()}")
    
    # First, try to import main directly to see the error
    print("\n=== Testing direct import of main.py ===")
    try:
        import main
        print("✅ main.py imported successfully!")
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        print("\n=== Attempting to fix common issues ===")
        
        # Check if .env exists
        if not os.path.exists('.env'):
            print("Creating .env file from .env.example...")
            if os.path.exists('.env.example'):
                import shutil
                shutil.copy('.env.example', '.env')
                print("✅ .env file created")
            else:
                print("❌ No .env.example found!")
        
        # Try importing again
        print("\nTrying import again after fixes...")
        try:
            # Clear the module cache
            if 'main' in sys.modules:
                del sys.modules['main']
            import main
            print("✅ main.py now imports successfully!")
        except Exception as e2:
            print(f"❌ Still failing: {e2}")
            return
    
    # If we got here, try running with uvicorn
    print("\n=== Starting backend with uvicorn ===")
    try:
        subprocess.run([
            sys.executable,
            "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\nBackend stopped by user.")
    except Exception as e:
        print(f"Error running uvicorn: {e}")

if __name__ == "__main__":
    run_backend_with_debug()
