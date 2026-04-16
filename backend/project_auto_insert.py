# project_auto_insert.py
"""
Auto-insert projects into the projects table during activity ingestion.
Only inserts when:
  1. project_name exists and is not generic
  2. Name length > 4 characters
  3. Name is not in the excluded folders list
  4. Activity comes from a development editor
  5. Total editor hours on this project > 2 hours
"""
from typing import Optional
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError

# Development editor application names (lowercase)
DEV_EDITOR_NAMES = [
    'code.exe', 'visual studio code', 'code',
    'cursor', 'cursor.exe',
    'pycharm', 'pycharm64.exe', 'pycharm.exe',
    'webstorm', 'webstorm64.exe', 'webstorm.exe',
    'phpstorm', 'phpstorm64.exe', 'phpstorm.exe',
    'sublime_text', 'sublime_text.exe', 'sublime text',
    'eclipse', 'eclipse.exe',
    'notepad++', 'notepad++.exe',
    'intellij', 'idea64.exe', 'intellij idea',
    'android studio', 'studio64.exe',
    'atom', 'atom.exe',
    'netbeans', 'netbeans64.exe', 'netbeans.exe',
    'vim', 'nvim', 'emacs',
    'filezilla', 'filezilla.exe',
]

# Common code subfolders, framework dirs, system folders — not real projects
EXCLUDED_FOLDER_NAMES = {
    'backend', 'frontend', 'components', 'controllers', 'models', 'routes',
    'views', 'helpers', 'middleware', 'config', 'database', 'migrations',
    'factories', 'seeders', 'services', 'repositories', 'resources',
    'functions', 'constants', 'messages', 'products', 'console',
    'traits', 'interfaces', 'abstract', 'enums', 'types',
    'hooks', 'store', 'reducers', 'actions', 'selectors',
    'pages', 'screens', 'widgets', 'adapters', 'entities',
    'schemas', 'pipes', 'guards', 'interceptors', 'commands',
    'events', 'jobs', 'notifications', 'policies', 'channels',
    'exceptions', 'filters', 'observers', 'investors',
    'public', 'static', 'images', 'uploads', 'assets', 'dist', 'build',
    'node_modules', 'vendor', 'packages', 'modules', 'tests', 'specs',
    'fixtures', 'lang', 'layouts', 'layout',
    'downloads', 'desktop', 'documents', 'users', 'home',
    'prelogin', 'imports', 'cursor', '.claude',
    'general', 'unknown', 'nodeserver', 'ajaxservice',
    'startup',
    'switch', 'transactions', 'sql_data',
}

# SQL IN clause for dev editors
_DEV_EDITORS_SQL = ", ".join(f"'{e}'" for e in DEV_EDITOR_NAMES)


def _is_valid_project_name(name: str) -> bool:
    """Check if project name passes all validation rules."""
    if not name or len(name) <= 4:
        return False
    if name.lower() in ('general', 'unknown', ''):
        return False
    if name.lower() in EXCLUDED_FOLDER_NAMES:
        return False
    if name.startswith('.'):
        return False
    import re
    if re.search(r'fz\d+temp', name, re.IGNORECASE):
        return False
    return True


def _is_dev_editor(app_name: str) -> bool:
    """Check if application is a development editor."""
    app_lower = app_name.lower().strip()
    return any(editor in app_lower for editor in DEV_EDITOR_NAMES)


def resolve_or_create_project(db, project_name: str, app_name: str, logger=None) -> Optional[int]:
    """
    Look up project_id from projects table.
    If not found and conditions are met (dev editor, valid name, >2h editor work),
    auto-insert into projects table and return the new project_id.

    Returns project_id or None.
    """
    if not project_name:
        return None

    # Step 1: Check if project already exists (active or inactive)
    from models import Project
    project_row = db.query(Project).filter(
        func.lower(Project.name) == project_name.lower()
    ).first()
    if project_row:
        return project_row.id if project_row.is_active else None

    # Step 2: Validate — must be dev editor + valid name
    if not _is_dev_editor(app_name) or not _is_valid_project_name(project_name):
        return None

    # Step 3: Check if total editor hours on this project > 2
    editor_hours_row = db.execute(text(f"""
        SELECT COALESCE(SUM(duration), 0) / 3600.0
        FROM activity_records
        WHERE LOWER(project_name) = LOWER(:pname)
          AND LOWER(application_name) IN ({_DEV_EDITORS_SQL})
    """), {"pname": project_name}).fetchone()
    editor_hours = float(editor_hours_row[0]) if editor_hours_row else 0

    if editor_hours <= 2.0:
        return None

    # Step 4: Insert new project (use savepoint to avoid corrupting parent transaction)
    try:
        with db.begin_nested():
            new_project = Project(
                name=project_name,
                description=f"Auto-added from dev editors ({editor_hours:.1f}h)",
                is_active=True
            )
            db.add(new_project)
        if logger:
            logger.info(f"Auto-inserted project '{project_name}' ({editor_hours:.1f}h from editors)")
        return new_project.id
    except IntegrityError:
        # Concurrent insert — savepoint auto-rolled back, fetch existing
        project_row = db.query(Project).filter(
            func.lower(Project.name) == project_name.lower()
        ).first()
        return project_row.id if project_row else None
