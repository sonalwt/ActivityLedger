# create_fixed_main.py
import shutil
import re

print("Creating a fixed version of main.py...\n")

try:
    # Read the file in binary mode and decode with error handling
    with open("main.py", "rb") as f:
        content_bytes = f.read()
    
    # Try different encodings
    content = None
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            content = content_bytes.decode(encoding)
            print(f"✅ Successfully decoded with {encoding}")
            break
        except:
            continue
    
    if content is None:
        print("❌ Could not decode main.py")
        print("Falling back to minimal server")
        import subprocess
        subprocess.run([sys.executable, "minimal_main.py"])
        exit()
    
    # Make a backup
    shutil.copy("main.py", "main.py.encoding_backup")
    print("✅ Created backup: main.py.encoding_backup")
    
    # Fix the exec line
    if "exec(open('real_data_endpoints.py').read())" in content:
        print("Found and fixing exec() line...")
        content = content.replace(
            "exec(open('real_data_endpoints.py').read())",
            "# exec(open('real_data_endpoints.py').read())  # DISABLED"
        )
    
    # Save with UTF-8 encoding
    with open("main_fixed.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Created main_fixed.py")
    
    # Copy the fixed version to main.py
    shutil.copy("main_fixed.py", "main.py")
    print("✅ Replaced main.py with fixed version")
    
    print("\n=== Starting server ===")
    import subprocess
    import sys
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app", "--host", "0.0.0.0",
        "--port", "8000", "--reload"
    ])
    
except Exception as e:
    print(f"Error: {e}")
    print("\nFalling back to minimal server...")
    import subprocess
    import sys
    subprocess.run([sys.executable, "minimal_main.py"])
