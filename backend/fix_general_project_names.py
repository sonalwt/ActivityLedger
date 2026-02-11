"""
Fix project names for records currently marked as 'general'
Extract actual project names from window_title field for VS Code activities
"""
from sqlalchemy import create_engine, text
import os
import re

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:asdf1234@localhost:5432/timesheet")
engine = create_engine(DATABASE_URL)

def extract_project_from_vscode_title(window_title):
    """
    Extract project name from VS Code window titles like:
    - "branding.js - mahindraManulifeDistributor"
    - "FundRelatedContentController.php - mahindraCMS"
    - "ImportController.php - mahindraCMS (Workspace)"
    """
    if not window_title:
        return None

    # Pattern 1: "filename - projectname" or "filename - projectname (Workspace)"
    # Look for pattern after " - " and before optional " (Workspace)"
    match = re.search(r'\s-\s([a-zA-Z][a-zA-Z0-9_-]{2,}?)(?:\s*\(|$)', window_title)
    if match:
        project = match.group(1).strip()
        # Filter out common non-project patterns
        excluded = ['google chrome', 'visual studio code', 'untitled', 'welcome',
                   'extensions', 'settings', 'output', 'debug console', 'terminal',
                   'working tree', 'index', 'problems']
        if project.lower() not in excluded and len(project) >= 4:
            return project

    return None

def extract_project_from_browser_title(window_title):
    """
    Extract project/company name from browser window titles.
    Examples:
      "HDFC Life Insurance | HDFC Life Term..." -> "HDFC"
      "Waaree Solar | Products..." -> "Waaree"
      "Mahindra Manulife | Home..." -> "Mahindra Manulife"
    """
    if not window_title:
        return None

    # Remove common browser suffixes
    title = window_title
    for suffix in [' - Google Chrome', ' - Mozilla Firefox', ' - Microsoft Edge', ' - Chrome', ' - Firefox', ' - Edge']:
        title = title.replace(suffix, '')

    title = title.strip()

    # Extract first meaningful part (before |, :, or -)
    separators = [' | ', ' : ', ' - ']
    for sep in separators:
        if sep in title:
            first_part = title.split(sep)[0].strip()
            # Filter out generic terms
            excluded = ['home', 'login', 'dashboard', 'welcome', 'new tab', 'about', 'untitled',
                       'settings', 'help', 'search', 'google', 'gmail', 'inbox']
            if len(first_part) >= 4 and first_part.lower() not in excluded:
                return first_part

    # If no separator, use title if it's reasonable length
    if 4 <= len(title) <= 60 and title.lower() not in ['home', 'login', 'dashboard']:
        return title

    return None

print("\n" + "="*80)
print("FIXING PROJECT NAMES FOR 'GENERAL' CATEGORY RECORDS")
print("="*80 + "\n")

with engine.connect() as conn:
    # Get statistics before fix
    print("1. Current state:")
    print("-" * 80)

    result = conn.execute(text("""
        SELECT
            COUNT(*) as total_records,
            SUM(duration) / 3600.0 as total_hours
        FROM activity_records
        WHERE project_name = 'general'
    """))

    row = result.fetchone()
    total_general_records = row[0]
    total_general_hours = row[1]

    print(f"Total 'general' records: {total_general_records:,}")
    print(f"Total 'general' hours: {total_general_hours:.2f}h\n")

    # Get sample of fixable records (both IDE and browser)
    print("2. Analyzing fixable records:")
    print("-" * 80)

    result = conn.execute(text("""
        SELECT
            id,
            window_title,
            application_name
        FROM activity_records
        WHERE project_name = 'general'
        AND (
            application_name ILIKE '%code%'
            OR application_name ILIKE '%chrome%'
            OR application_name ILIKE '%firefox%'
            OR application_name ILIKE '%edge%'
        )
    """))

    fixable_records = []
    project_stats = {}

    for row in result:
        record_id, window_title, app_name = row

        # Try IDE extraction first
        project = extract_project_from_vscode_title(window_title)

        # If not IDE, try browser extraction
        if not project:
            project = extract_project_from_browser_title(window_title)

        if project:
            fixable_records.append((record_id, project))
            project_stats[project] = project_stats.get(project, 0) + 1

    print(f"Found {len(fixable_records):,} fixable records")
    print(f"Identified {len(project_stats)} unique projects\n")

    # Show top projects that will be fixed
    print("Top 20 projects to be fixed:")
    sorted_projects = sorted(project_stats.items(), key=lambda x: x[1], reverse=True)[:20]
    for project, count in sorted_projects:
        print(f"  {project:50} {count:>6} records")

    # Proceed with update
    print("\n" + "="*80)
    print(f"\nProceeding with update of {len(fixable_records):,} records...")

    # Update records in batches
    print("\n3. Updating records...")
    print("-" * 80)

    batch_size = 1000
    updated_count = 0

    for i in range(0, len(fixable_records), batch_size):
        batch = fixable_records[i:i + batch_size]

        for record_id, project_name in batch:
            conn.execute(text("""
                UPDATE activity_records
                SET project_name = :project_name
                WHERE id = :id
            """), {"project_name": project_name, "id": record_id})

        conn.commit()
        updated_count += len(batch)
        print(f"Updated {updated_count:,} / {len(fixable_records):,} records...", end='\r')

    print(f"\n\n[OK] Successfully updated {updated_count:,} records!")

    # Show statistics after fix
    print("\n4. Results:")
    print("-" * 80)

    result = conn.execute(text("""
        SELECT
            COUNT(*) as remaining_records,
            SUM(duration) / 3600.0 as remaining_hours
        FROM activity_records
        WHERE project_name = 'general'
    """))

    row = result.fetchone()
    remaining_general_records = row[0]
    remaining_general_hours = row[1]

    print(f"Remaining 'general' records: {remaining_general_records:,}")
    print(f"Remaining 'general' hours: {remaining_general_hours:.2f}h")
    print(f"\nFixed records: {total_general_records - remaining_general_records:,}")
    print(f"Fixed hours: {total_general_hours - remaining_general_hours:.2f}h")

    # Show updated project distribution
    print("\n5. Top projects after fix (productive category):")
    print("-" * 80)

    result = conn.execute(text("""
        SELECT
            project_name,
            COUNT(*) as count,
            SUM(duration) / 3600.0 as hours
        FROM activity_records
        WHERE category = 'productive'
        AND project_name != 'general'
        AND project_name IS NOT NULL
        GROUP BY project_name
        ORDER BY hours DESC
        LIMIT 20
    """))

    for row in result:
        pname, count, hours = row
        print(f"{pname:50} {hours:>8.2f}h")

print("\n" + "="*80)
print("COMPLETE!")
print("="*80 + "\n")
