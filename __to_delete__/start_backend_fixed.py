#!/usr/bin/env python3
# start_backend_fixed.py
import os
import subprocess
import sys
from pathlib import Path

# Change to backend directory
backend_dir = Path(__file__).parent / "backend"
os.chdir(backend_dir)

print(f"Starting backend from: {os.getcwd()}")

# Comment out the problematic exec line in main.py
try:
    with open("main.py", "r") as f:
        content = f.read()
    
    if "exec(open('real_data_endpoints.py').read())" in content and not content.find("# exec(open('real_data_endpoints.py')"):
        print("Fixing main.py...")
        content = content.replace(
            "exec(open('real_data_endpoints.py').read())",
            "# exec(open('real_data_endpoints.py').read())  # Temporarily disabled"
        )
        with open("main.py", "w") as f:
            f.write(content)
        print("✅ Fixed main.py")
except Exception as e:
    print(f"Warning: Could not fix main.py: {e}")

# Start the server
print("\nStarting FastAPI server...")
subprocess.run([
    sys.executable,
    "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])
