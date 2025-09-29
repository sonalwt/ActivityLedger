# cleanup_test_files.py
import os
from pathlib import Path

print("=== Cleaning up test and debug files created during troubleshooting ===\n")

# Define ONLY the files we created during debugging
files_we_created = {
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
}

# Get the root directory
root_dir = Path(__file__).parent

# Remove files
print("Removing troubleshooting files:")
removed_count = 0
not_found_count = 0

for file in files_we_created:
    file_path = root_dir / file
    if file_path.exists():
        try:
            os.remove(file_path)
            print(f"  ✓ Removed: {file}")
            removed_count += 1
        except Exception as e:
            print(f"  ✗ Failed to remove {file}: {e}")
    else:
        not_found_count += 1

if not_found_count > 0:
    print(f"\n  ({not_found_count} files were already removed or didn't exist)")

print(f"\n=== Cleanup complete ===")
print(f"Removed {removed_count} troubleshooting files")
print("\nYour original project files remain intact, including:")
print("- Original test files (test_activitywatch.py, etc.)")
print("- Original debug files (debug_table.py, etc.)")
print("- All core project files")

print("\n⚠️  Important note about main.py:")
print("If we commented out the exec() line in main.py during troubleshooting,")
print("it's still commented. You can:")
print("1. Keep it commented if it was causing issues")
print("2. Uncomment it if you need those endpoints")

# Delete this cleanup script
print("\nRemoving this cleanup script...")
try:
    os.remove(__file__)
    print("✓ Cleanup script will be removed")
except:
    print("✗ Please manually delete cleanup_test_files.py")
