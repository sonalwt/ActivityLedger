# quick_fix_backend.py
import os
import shutil
from pathlib import Path

def quick_fix():
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("=== Quick Fix for Backend ===\n")
    
    # Backup main.py
    if os.path.exists("main.py") and not os.path.exists("main.py.original"):
        shutil.copy("main.py", "main.py.original")
        print("✅ Backed up main.py to main.py.original")
    
    # Read main.py
    with open("main.py", "r") as f:
        content = f.read()
    
    # Comment out the problematic exec line
    if "exec(open('real_data_endpoints.py').read())" in content:
        content = content.replace(
            "exec(open('real_data_endpoints.py').read())",
            "# exec(open('real_data_endpoints.py').read())  # TEMPORARILY DISABLED - causing import errors"
        )
        
        with open("main.py", "w") as f:
            f.write(content)
        
        print("✅ Commented out the problematic exec() line")
    else:
        print("⚠️  exec() line not found or already commented")
    
    # Also check if .env exists
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("✅ Created .env from .env.example")
        else:
            # Create a basic .env
            with open(".env", "w") as f:
                f.write("""# Basic environment configuration
DATABASE_URL=sqlite:///./timesheet.db
SECRET_KEY=your-secret-key-change-this-in-production
ENVIRONMENT=local
LOCAL_DEVELOPER_NAME=local_dev
""")
            print("✅ Created basic .env file")
    
    print("\n=== Done! ===")
    print("Now try running: python ../run_backend.py")
    print("Or: python -m uvicorn main:app --reload")

if __name__ == "__main__":
    quick_fix()
