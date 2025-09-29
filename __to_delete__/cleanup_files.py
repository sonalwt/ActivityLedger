import os
import shutil

base_dir = r"E:\timesheet\timesheet_new"
deleted_count = 0
errors = []

# List of files to remove
files_to_remove = [
    # Markdown files
    "DEPLOYMENT_GUIDE.md",
    "DYNAMIC_CONFIG_SYSTEM.md", 
    "IMPLEMENTATION_STEPS.md",
    "MINIMAL_SETUP_GUIDE.md",
    "POSTGRESQL_SETUP.md",
    "PROJECT_OVERVIEW.md",
    "PROJECT_STRUCTURE.md", 
    "QUICK_START_GUIDE.md",
    "README.md",
    "STATELESS_APPROACH_GUIDE.md",
    "TIMESHEET_DOCUMENTATION.md",
    "ZERO_HARDCODE_GUIDE.md",
    
    # Test files
    "test_imports.py",
    
    # Generated files
    "generate_aw_configs.py",
    "generate_env_keys.sh",
    "generate_secure_password.sh",
    
    # Setup scripts (keeping only essential ones)
    "install_timesheet_tracker.sh",
    "integrate_activitywatch.py",
    "stateless_config_generator.py",
    "bulk_register_developers.py",
    "database_migration.py",
]

# Backend files to remove
backend_files = [
    # Test files
    "test_activitywatch.py",
    "test_activitywatch_daily.py", 
    "test_aw_connection.py",
    "test_backend.py",
    "test_backend_local.py",
    "test_daily_hours.py",
    "test_date_range.py",
    "test_discovery.py",
    "test_env.py",
    "test_filtering.py",
    "test_local.py",
    "test_productivity.py",
    "test_raw_aw_data.py",
    "test_realistic_hours.py",
    "test_sync.py",
    "simple_test.py",
    
    # Debug files
    "debug_activitywatch_time.py",
    "debug_table.py",
    "debug_total_time.py", 
    "debug_window_titles.py",
    "debug_working_hours.py",
    
    # Check files
    "check_any_date.py",
    "check_available_dates.py",
    "check_database.py",
    "check_database_data.py",
    "check_database_structure.py",
    "check_projects.py",
    "check_tables.py",
    "check_user_id.py",
    
    # Fix files
    "fix_developers_table.py",
    "fix_foreign_keys.py",
    "fix_users_table.py",
    "fix_working_hours.py",
    "fixed_data_puller.py",
    "fixed_dynamic_developer_api.py",
    "fixed_registration_final.py",
    "fixed_top_window_titles.py",
    "quick_fix_registration.py",
    
    # HTML files in backend (should be in frontend)
    "activity_tracker.html",
    "developers_list.html",
    "developer_list.html",
    "register-developer.html",
    "simple_developer_registration.html", 
    "token-manager.html",
    
    # Text files
    "correct_imports.txt",
    "fix_duplicate_endpoint.txt",
    "import_fix.txt",
    
    # Old/temp files
    ".envold",
    
    # One-off/duplicate scripts
    "add_sample_data.py",
    "clean_duplicates.py",
    "create_enhanced_tables.py",
    "direct_aw_test.py",
    "explain_dashboard_numbers.py",
    "explain_productivity.py",
    "inspect_database.py",
    "migrate_detailed_info.py",
    "query_database.py",
    "sample_data.py",
    "simple_token_creator.py",
    "view_saved_data.py",
    "alternative_registration.py",
    "correct_registration_endpoint.py",
    "developer_model_addition.py",
    "setup_multi_dev.py",
    "setup_multi_dev_clean.py",
    "update_database_schema.py",
    "update_existing_projects.py",
    "safe_activity_caching.py",
]

# Remove root level files
for filename in files_to_remove:
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"✓ Removed: {filename}")
            deleted_count += 1
        except Exception as e:
            errors.append(f"✗ Error removing {filename}: {str(e)}")
    else:
        print(f"- Skipped (not found): {filename}")

# Remove backend files
for filename in backend_files:
    filepath = os.path.join(base_dir, "backend", filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"✓ Removed: backend/{filename}")
            deleted_count += 1
        except Exception as e:
            errors.append(f"✗ Error removing backend/{filename}: {str(e)}")

# Remove directories
directories_to_remove = [
    "__to_delete__",
    os.path.join("backend", "__pycache__"),
]

for dir_path in directories_to_remove:
    full_path = os.path.join(base_dir, dir_path)
    if os.path.exists(full_path):
        try:
            shutil.rmtree(full_path)
            print(f"✓ Removed directory: {dir_path}")
            deleted_count += 1
        except Exception as e:
            errors.append(f"✗ Error removing directory {dir_path}: {str(e)}")

print(f"\n{'='*50}")
print(f"CLEANUP COMPLETE!")
print(f"{'='*50}")
print(f"✓ Total items removed: {deleted_count}")
print(f"✗ Errors encountered: {len(errors)}")

if errors:
    print(f"\nErrors:")
    for error in errors:
        print(f"  {error}")

print(f"\nYour project is now cleaner!")
print(f"Remaining key files:")
print("- Backend: main.py, config.py, database.py, models.py, schemas.py, crud.py, auth.py")
print("- Environment: .env files")
print("- Scripts: Essential batch files for running the app")
print("- Frontend: React application")
