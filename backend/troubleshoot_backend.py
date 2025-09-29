# troubleshoot_backend.py
import subprocess
import socket
import sys
import os
import time
import psutil
import requests
from pathlib import Path

def check_port(port):
    """Check if a port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def find_process_on_port(port):
    """Find which process is using a port"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    return proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def test_backend_import():
    """Test if backend can be imported"""
    backend_path = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_path))
    
    try:
        import main
        print("✅ Backend main.py can be imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import backend: {e}")
        return False

def check_database():
    """Check database connection"""
    backend_path = Path(__file__).parent / "backend"
    os.chdir(backend_path)
    
    try:
        from database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def start_backend_test():
    """Try to start the backend and test it"""
    print("\n=== Attempting to start backend ===")
    
    backend_path = Path(__file__).parent / "backend"
    os.chdir(backend_path)
    
    # Start backend process
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    print("Waiting for backend to start...")
    time.sleep(5)
    
    # Check if process is still running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"❌ Backend failed to start!")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    # Test if backend is responding
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and responding!")
            # Terminate the test process
            process.terminate()
            return True
        else:
            print(f"❌ Backend returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
    
    # Terminate the process
    process.terminate()
    return False

def check_environment():
    """Check environment setup"""
    print("\n=== Environment Check ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not running in virtual environment")
    
    # Check required packages
    required_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'psycopg2-binary']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")

def main():
    print("=== Backend Troubleshooting ===\n")
    
    # 1. Check if port 8000 is already in use
    print("1. Checking port 8000...")
    if check_port(8000):
        process = find_process_on_port(8000)
        if process:
            print(f"⚠️  Port 8000 is already in use by: {process['name']} (PID: {process['pid']})")
        else:
            print("⚠️  Port 8000 is in use but cannot identify the process")
    else:
        print("✅ Port 8000 is available")
    
    # 2. Check environment
    check_environment()
    
    # 3. Test backend import
    print("\n2. Testing backend imports...")
    test_backend_import()
    
    # 4. Check database
    print("\n3. Checking database connection...")
    check_database()
    
    # 5. Try to start backend
    start_backend_test()
    
    print("\n=== Troubleshooting Complete ===")
    print("\nRecommended actions based on the results:")
    print("1. If port is in use: Kill the process or use a different port")
    print("2. If packages are missing: Run 'pip install -r requirements.txt'")
    print("3. If database fails: Check your .env file and database server")
    print("4. If import fails: Check for syntax errors in your code")

if __name__ == "__main__":
    main()