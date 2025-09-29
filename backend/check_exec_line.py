# check_exec_line.py
import os

print("Checking for exec line in main.py...")

try:
    # Read file line by line to avoid encoding issues
    found_exec = False
    line_number = 0
    
    with open("main.py", "rb") as f:
        for line_num, line in enumerate(f, 1):
            try:
                line_str = line.decode('utf-8', errors='ignore')
                if "exec(open('real_data_endpoints.py').read())" in line_str:
                    found_exec = True
                    line_number = line_num
                    print(f"Found exec() at line {line_num}")
                    if line_str.strip().startswith('#'):
                        print("  ✅ Already commented out")
                    else:
                        print("  ❌ NOT commented - this needs to be fixed")
                    break
            except:
                pass
    
    if not found_exec:
        print("✅ No problematic exec() line found")
    
    print("\nTrying to start the server anyway...")
    print("If this fails, use: python minimal_main.py")
    
    import subprocess
    import sys
    
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app", "--host", "0.0.0.0", 
        "--port", "8000", "--reload"
    ])
    
except Exception as e:
    print(f"Error: {e}")
