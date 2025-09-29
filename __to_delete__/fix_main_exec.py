# fix_main_exec.py
import os
import shutil
from pathlib import Path

def fix_main_py():
    backend_dir = Path(__file__).parent / "backend"
    main_py = backend_dir / "main.py"
    main_backup = backend_dir / "main.py.backup"
    
    print("=== Fixing main.py ===\n")
    
    # Backup original
    if main_py.exists():
        shutil.copy(main_py, main_backup)
        print("✅ Backed up original main.py to main.py.backup")
    
    # Read the current main.py
    with open(main_py, 'r') as f:
        content = f.read()
    
    # Find and comment out the problematic exec line
    if "exec(open('real_data_endpoints.py').read())" in content:
        print("Found problematic exec() statement...")
        
        # Replace the exec with a proper import
        new_content = content.replace(
            "exec(open('real_data_endpoints.py').read())",
            "# exec(open('real_data_endpoints.py').read())  # FIXED: This was causing import errors\n# Import real_data_endpoints properly instead\ntry:\n    from real_data_endpoints import *  # or import specific functions\nexcept ImportError as e:\n    print(f'Warning: Could not import real_data_endpoints: {e}')"
        )
        
        # Write the fixed version
        with open(main_py, 'w') as f:
            f.write(new_content)
        
        print("✅ Fixed the exec() statement in main.py")
        print("The problematic line has been replaced with a proper import")
    else:
        print("❌ Could not find the exec() statement - it may have already been fixed")
    
    print("\n=== Next steps ===")
    print("1. Try running the backend again: python run_backend.py")
    print("2. If it still fails, run: python test_main_imports.py")
    print("3. To restore original: copy main.py.backup to main.py")

if __name__ == "__main__":
    fix_main_py()
