# Productivity and Project Analysis Features

This document explains the new productivity tracking and project analysis features added to the timesheet application.

## Features Overview

### 1. **Productivity Metrics** (Database-based)
- Calculate productivity hours for each developer
- Track daily, weekly, and monthly productivity trends
- Identify productive vs non-productive time
- Show top applications and their usage
- Hourly productivity distribution

### 2. **Project Breakdown** (Database-based)
- Group activities by project
- Show time spent on each project
- Track project progress over time
- View applications used per project
- Daily project distribution

### 3. **Team Productivity Summary**
- Overview of all developers' productivity
- Active developer count
- Team-wide productivity percentage
- Average hours per developer
- Top performers

## How It Works

### Productivity Calculation

**Productive Applications** include:
- IDEs: VS Code, IntelliJ, PyCharm, Sublime Text, etc.
- Terminals: Command Prompt, PowerShell, Git Bash
- Development Tools: Postman, Docker Desktop
- Communication: Teams, Slack (during work hours)
- Documentation: Word, Excel, Google Docs

**Productive Categories**:
- Development
- IDE
- Code
- Terminal
- Documentation

### Project Detection

Projects are identified through:

1. **Automatic Extraction** (run `python extract_projects.py`):
   - IDE window titles (e.g., "file.py - MyProject - Visual Studio Code")
   - File paths (e.g., "/projects/myapp/src/main.py")
   - GitHub/GitLab URLs
   - JIRA ticket numbers

2. **Manual Assignment** (through UI):
   - Assign projects to unassigned activities
   - Bulk assign based on patterns
   - Create custom project names

## API Endpoints

### Productivity Endpoints

1. **Get Developer Productivity**
   ```
   GET /api/developer/{developer_id}/productivity-hours
   Query params: start_date, end_date
   ```
   Returns daily productivity stats, hourly distribution, and top applications.

2. **Get Project Breakdown**
   ```
   GET /api/developer/{developer_id}/project-breakdown
   Query params: start_date, end_date
   ```
   Returns project-wise time distribution and statistics.

3. **Team Productivity Summary**
   ```
   GET /api/all-developers/productivity-summary
   Query params: start_date, end_date
   ```
   Returns team-wide productivity metrics.

### Project Assignment Endpoints

1. **Get Unassigned Activities**
   ```
   GET /api/developer/{developer_id}/activities-without-project
   Query params: limit (default: 50)
   ```

2. **Assign Project to Activities**
   ```
   POST /api/developer/{developer_id}/assign-project
   Body: {
     "activity_ids": [1, 2, 3],
     "project_name": "MyProject",
     "project_type": "Development"
   }
   ```

3. **Get Project Suggestions**
   ```
   GET /api/developer/{developer_id}/project-suggestions
   ```

4. **Bulk Assign Similar Activities**
   ```
   POST /api/developer/{developer_id}/bulk-assign-similar
   Body: {
     "pattern": {
       "application_name": "Code.exe",
       "window_title_contains": "myproject"
     },
     "project_name": "MyProject",
     "project_type": "Development"
   }
   ```

## Frontend Components

### 1. ProductivityMetrics Component
Shows:
- Total work hours vs productive hours
- Productivity percentage
- Daily productivity chart
- Top applications with productive/non-productive classification

### 2. ProjectBreakdown Component
Shows:
- Project summary with total hours
- Percentage distribution per project
- Expandable project details
- Applications used per project
- Recent project timeline

### 3. TeamProductivitySummary Component
Shows:
- Active developer count
- Team productivity percentage
- Total team hours
- Developer activity list with individual productivity

## Setup Instructions

### 1. Backend Setup

1. **Run Database Migrations** (if needed):
   ```bash
   python add_missing_columns.py
   ```

2. **Extract Projects from Existing Data**:
   ```bash
   python extract_projects.py
   ```
   This will analyze existing activity records and extract project names.

3. **Start the Backend**:
   ```bash
   python main.py
   ```

### 2. Frontend Setup

The components are already integrated. Just ensure the frontend is running:
```bash
cd frontend
npm start
```

### 3. View the Features

1. **Team Dashboard**: Shows team productivity summary at the top
2. **Individual Developer**: Click on a developer to see:
   - Activity Data tab (existing)
   - Productivity tab (new)
   - Projects tab (new)

## Customization

### Adding Productive Applications

Edit `productivity_api.py` and add to `PRODUCTIVE_APPS` list:
```python
PRODUCTIVE_APPS = [
    'Your App Name',
    # ... existing apps
]
```

### Adding Project Patterns

Edit `extract_projects.py` and add patterns to:
- `IDE_PATTERNS` for new IDEs
- `BROWSER_PATTERNS` for web services

### Modifying Productivity Calculation

The productivity percentage is calculated as:
```
productivity = (productive_hours / total_hours) * 100
```

You can modify the logic in `productivity_api.py`.

## Database Schema

The system uses these columns in `activity_records`:
- `project_name`: Name of the project
- `project_type`: Type of project (Development, Database, etc.)
- `category`: Activity category
- `duration`: Time in seconds
- `developer_id`: Links to developers table

## Best Practices

1. **Run Project Extraction Regularly**:
   ```bash
   # Add to cron job or scheduled task
   python extract_projects.py
   ```

2. **Review Unassigned Activities**:
   - Check the Projects tab regularly
   - Assign projects to improve accuracy

3. **Customize for Your Workflow**:
   - Add your team's specific applications
   - Define project naming conventions
   - Set productivity goals

## Troubleshooting

1. **No Productivity Data**:
   - Ensure activities have duration > 0
   - Check if applications are in PRODUCTIVE_APPS list

2. **Projects Not Detected**:
   - Check window title patterns
   - Verify IDE patterns match your setup
   - Use manual assignment for edge cases

3. **Performance Issues**:
   - Limit date ranges to reasonable periods
   - Use pagination for large datasets
   - Consider archiving old data

## Future Enhancements

1. **Productivity Goals**: Set daily/weekly targets
2. **Project Budgets**: Track time vs estimates
3. **Team Analytics**: Compare team members
4. **Export Reports**: PDF/Excel exports
5. **Notifications**: Alerts for low productivity
6. **Machine Learning**: Auto-categorize activities
