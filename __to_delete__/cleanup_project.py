import os
import shutil

# Define the base directory
base_dir = r"E:\timesheet\timesheet_new"

# Files and directories to remove
to_remove = [
    # All .md files
    "deleted_AWS_DEPLOYMENT_GUIDE.md",
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
    "backend/test_activitywatch.py",
    "backend/test_activitywatch_daily.py",
    "backend/test_aw_connection.py",
    "backend/test_backend.py",
    "backend/test_backend_local.py",
    "backend/test_daily_hours.py",
    "backend/test_date_range.py",
    "backend/test_discovery.py",
    "backend/test_env.py",
    "backend/test_filtering.py",
    "backend/test_local.py",
    "backend/test_productivity.py",
    "backend/test_raw_aw_data.py",
    "backend/test_realistic_hours.py",
    "backend/test_sync.py",
    "backend/simple_test.py",
    
    # Debug files
    "backend/debug_activitywatch_time.py",
    "backend/debug_table.py",
    "backend/debug_total_time.py",
    "backend/debug_window_titles.py",
    "backend/debug_working_hours.py",
    
    # Check files
    "backend/check_any_date.py",
    "backend/check_available_dates.py",
    "backend/check_database.py",
    "backend/check_database_data.py",
    "backend/check_database_structure.py",
    "backend/check_projects.py",
    "backend/check_tables.py",
    "backend/check_user_id.py",
    
    # Fix files
    "backend/fix_developers_table.py",
    "backend/fix_foreign_keys.py",
    "backend/fix_users_table.py",
    "backend/fix_working_hours.py",
    "backend/fixed_data_puller.py",
    "backend/fixed_dynamic_developer_api.py",
    "backend/fixed_registration_final.py",
    "backend/fixed_top_window_titles.py",
    "backend/quick_fix_registration.py",
    
    # HTML files in backend
    "backend/activity_tracker.html",
    "backend/developers_list.html",
    "backend/developer_list.html",
    "backend/register-developer.html",
    "backend/simple_developer_registration.html",
    "backend/token-manager.html",
    
    # Text files
    "backend/correct_imports.txt",
    "backend/fix_duplicate_endpoint.txt",
    "backend/import_fix.txt",
    
    # Old/temp files
    "backend/.envold",
    
    # Directories to remove
    "__to_delete__",
    "backend/__pycache__",
    
    # One-off scripts that seem temporary
    "backend/add_sample_data.py",
    "backend/clean_duplicates.py",
    "backend/create_enhanced_tables.py",
    "backend/direct_aw_test.py",
    "backend/explain_dashboard_numbers.py",
    "backend/explain_productivity.py",
    "backend/inspect_database.py",
    "backend/migrate_detailed_info.py",
    "backend/query_database.py",
    "backend/sample_data.py",
    "backend/simple_token_creator.py",
    "backend/view_saved_data.py",
]

# Remove files and directories
removed_count = 0
for item in to_remove:
    full_path = os.path.join(base_dir, item)
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
            print(f"Removed file: {item}")
            removed_count += 1
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
            print(f"Removed directory: {item}")
            removed_count += 1
    except Exception as e:
        print(f"Could not remove {item}: {e}")

print(f"\nTotal items removed: {removed_count}")
print("\nCleanup complete!")
print("\nRemaining essential files:")
print("- Core backend files: main.py, config.py, database.py, models.py, schemas.py, crud.py, auth.py")
print("- Environment files: .env, .env.example")
print("- Requirements: requirements.txt")
print("- Batch scripts for running the app")
