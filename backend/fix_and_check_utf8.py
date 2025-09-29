# fix_and_check_utf8.py
import os
import shutil

print("Checking main.py status...")

# Read current main.py with UTF-8 encoding
with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Check if exec line is causing issues
if "exec(open('real_data_endpoints.py').read())" in content:
    print("Found problematic exec() statement")
    
    # Backup
    if not os.path.exists("main.py.backup"):
        shutil.copy("main.py", "main.py.backup")
        print("Created backup: main.py.backup")
    
    # Fix by commenting out the line
    content = content.replace(
        "exec(open('real_data_endpoints.py').read())",
        "# exec(open('real_data_endpoints.py').read())  # DISABLED - causing import issues"
    )
    
    # Save fixed version with UTF-8 encoding
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Fixed main.py - commented out exec() line")
else:
    print("✅ main.py looks OK (exec line not found or already fixed)")

print("\nNow try running:")
print("  python -m uvicorn main:app --reload")
