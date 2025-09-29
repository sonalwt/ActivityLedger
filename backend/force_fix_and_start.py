# force_fix_and_start.py
import os
import sys
import subprocess
import shutil

print("=== Force Fix and Start Backend ===\n")

# Ensure we're in backend directory
if not os.path.exists("main.py"):
    print("❌ Not in backend directory!")
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
        print(f"Changed to: {os.getcwd()}")
    else:
        print("Cannot find backend directory!")
        sys.exit(1)

# Backup main.py
if not os.path.exists("main.py.original"):
    shutil.copy("main.py", "main.py.original")
    print("✅ Backed up main.py to main.py.original")

# Read and fix main.py
print("\nFixing main.py...")
with open("main.py", "r") as f:
    content = f.read()

# Multiple fixes
fixes_applied = []

# 1. Fix exec() line
if "exec(open('real_data_endpoints.py').read())" in content:
    content = content.replace(
        "exec(open('real_data_endpoints.py').read())",
        "# exec(open('real_data_endpoints.py').read())  # DISABLED - causes import errors"
    )
    fixes_applied.append("Commented out exec() line")

# 2. Ensure app is created before any router includes
if "app = FastAPI" in content:
    # Make sure all router includes come after app creation
    lines = content.split('\n')
    new_lines = []
    app_created = False
    held_lines = []
    
    for line in lines:
        if "app = FastAPI" in line:
            new_lines.append(line)
            app_created = True
            # Add held router lines after app creation
            new_lines.extend(held_lines)
            held_lines = []
        elif not app_created and ("app.include_router" in line or "app.add_middleware" in line):
            # Hold these lines until after app is created
            held_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    if held_lines:
        fixes_applied.append("Reordered router includes after app creation")

# Save fixed main.py
with open("main.py", "w") as f:
    f.write(content)

if fixes_applied:
    print(f"✅ Applied fixes: {', '.join(fixes_applied)}")
else:
    print("✅ No fixes needed")

# Create .env if missing
if not os.path.exists(".env"):
    print("\nCreating .env file...")
    with open(".env", "w") as f:
        f.write("""# Environment configuration
ENVIRONMENT=local
DATABASE_URL=sqlite:///./timesheet.db
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOCAL_DEVELOPER_NAME=local_dev
ACTIVITYWATCH_HOST=http://localhost:5600
""")
    print("✅ Created .env file")

# Now try to import main
print("\nTesting import...")
try:
    if 'main' in sys.modules:
        del sys.modules['main']
    import main
    print("✅ Import successful!")
    
    # Start the server
    print("\n=== Starting Backend Server ===")
    print("URL: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop\n")
    
    subprocess.run([
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])
    
except Exception as e:
    print(f"❌ Import still failing: {e}")
    print("\nTrying minimal server instead...")
    
    # If main.py still won't work, use minimal version
    if os.path.exists("minimal_main.py"):
        subprocess.run([sys.executable, "minimal_main.py"])
    else:
        print("Run: python minimal_main.py")
