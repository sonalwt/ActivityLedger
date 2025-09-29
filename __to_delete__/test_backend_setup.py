# test_backend_setup.py
import os
import sys
from pathlib import Path

print("=== Backend Setup Test ===\n")

# Check current directory
print(f"Current directory: {os.getcwd()}")

# Check if backend directory exists
backend_dir = Path(__file__).parent / "backend"
if backend_dir.exists():
    print(f"✅ Backend directory exists: {backend_dir}")
else:
    print(f"❌ Backend directory not found: {backend_dir}")
    sys.exit(1)

# Change to backend directory
os.chdir(backend_dir)

# Check for important files
important_files = ['main.py', '.env', 'database.py', 'models.py', 'config.py']
for file in important_files:
    if os.path.exists(file):
        print(f"✅ {file} exists")
    else:
        print(f"❌ {file} is missing!")

# Try to import FastAPI
print("\n=== Testing imports ===")
try:
    import fastapi
    print(f"✅ FastAPI version: {fastapi.__version__}")
except ImportError:
    print("❌ FastAPI not installed!")

try:
    import uvicorn
    print(f"✅ Uvicorn is installed")
except ImportError:
    print("❌ Uvicorn not installed!")

# Check database file
db_file = Path("timesheet.db")
if db_file.exists():
    print(f"\n✅ SQLite database exists: {db_file}")
    print(f"   Size: {db_file.stat().st_size / 1024:.2f} KB")
else:
    print("\n⚠️  SQLite database not found (will be created on first run)")

print("\n=== Next Steps ===")
print("1. Install missing packages: pip install -r requirements.txt")
print("2. Run the backend: python run_backend.py")
print("3. Check http://localhost:8000/docs")
