# debug_uvicorn_import.py
import sys
import os

print("=== Debugging Uvicorn Import Issue ===\n")

# Show current directory and Python path
print(f"Current directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python path (first 3): {sys.path[:3]}\n")

# Try importing main directly
print("1. Testing direct import of main:")
try:
    import main
    print("✅ Direct import successful")
    print(f"   App object exists: {hasattr(main, 'app')}")
except Exception as e:
    print(f"❌ Direct import failed: {e}")
    import traceback
    traceback.print_exc()

# Try what uvicorn does
print("\n2. Testing uvicorn-style import:")
try:
    import importlib
    module = importlib.import_module("main")
    app = getattr(module, "app")
    print("✅ Uvicorn-style import successful")
    print(f"   App type: {type(app)}")
except Exception as e:
    print(f"❌ Uvicorn-style import failed: {e}")
    import traceback
    traceback.print_exc()

# Check for the exec line
print("\n3. Checking main.py for exec():")
try:
    with open("main.py", "r") as f:
        content = f.read()
    if "exec(open('real_data_endpoints.py').read())" in content:
        if content.find("# exec(open('real_data_endpoints.py')") == -1:
            print("❌ Found uncommented exec() line - THIS IS THE PROBLEM!")
            print("   Run: python fix_and_check.py to fix it")
        else:
            print("✅ exec() line is commented out")
    else:
        print("✅ No exec() line found")
except Exception as e:
    print(f"❌ Could not read main.py: {e}")

print("\n=== Debug Complete ===")
