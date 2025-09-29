# safe_cleanup_test_files.py
import os
from pathlib import Path

print("=== Safe Cleanup of Debug/Test Files ===\n")

# Define ONLY the files we created during debugging
files_to_remove = [
    # Root directory files
    "debug_308_redirect.py",
    "test_backend_setup.py", 
    "debug_backend_simple.py",
    "test_minimal_fastapi.py",
    "test_main_imports.py",
    "run_backend_debug.py",
    "fix_main_exec.py",
    "quick_fix_backend.py",
    "start_backend_debug.py",
    "start_backend_fixed.py",
    "test_308_endpoints.py",
    "troubleshoot_backend.py",
    "cleanup_test_files.py",  # The previous cleanup script
    # Backend directory files
    "backend/activitywatch_sync.py",  # The stub file we created
    "backend/minimal_main.py",
    "backend/fix_and_check.py",
    "backend/fix_and_check_utf8.py",
    "backend/simple_fix.py",
    "backend/check_exec_line.py",
    "backend/create_fixed_main.py",
    "backend/debug_uvicorn_import.py",
    "backend/force_fix_and_start.py",
    "backend/start_direct.py",
    "backend/main_fixed.py",
    "backend/main.py.backup",
    "backend/main.py.original", 
    "backend/main.py.encoding_backup"
]

# Get the root directory
root_dir = Path(__file__).parent

# First, show what will be deleted
print("The following files will be removed:")
print("-" * 50)
files_found = []
for file in files_to_remove:
    file_path = root_dir / file
    if file_path.exists():
        size = file_path.stat().st_size
        files_found.append((file, size))
        print(f"  • {file} ({size:,} bytes)")

if not files_found:
    print("  No files found to remove - already cleaned up!")
    exit()

print("-" * 50)
print(f"Total files to remove: {len(files_found)}")
total_size = sum(size for _, size in files_found)
print(f"Total size: {total_size:,} bytes ({total_size/1024:.1f} KB)")

# Ask for confirmation
print("\n⚠️  This will permanently delete these files!")
response = input("Do you want to proceed? (yes/no): ")

if response.lower() in ['yes', 'y']:
    print("\nRemoving files...")
    removed_count = 0
    for file, _ in files_found:
        file_path = root_dir / file
        try:
            os.remove(file_path)
            print(f"  ✓ Removed: {file}")
            removed_count += 1
        except Exception as e:
            print(f"  ✗ Failed to remove {file}: {e}")
    
    print(f"\n✓ Successfully removed {removed_count} files")
    
    # Remove this script too
    print("\nRemoving this cleanup script...")
    try:
        os.remove(__file__)
        print("✓ Cleanup script removed")
    except:
        print("✗ Please manually delete safe_cleanup_test_files.py")
else:
    print("\nCleanup cancelled. No files were removed.")

print("\n📝 Note: Your original project files remain intact.")
print("If main.py was modified during debugging, you may want to check it.")
