# Developer Productivity Dashboard

A beautiful, modern dashboard to visualize and analyze developer productivity based on ActivityWatch data stored in PostgreSQL.

## Features

- **Real-time Activity Categorization**: Automatically categorizes activities into:
  - **Projects**: VS Code activities
  - **Cloud Services**: AWS, Azure, Google Cloud usage
  - **Development**: GitHub, localhost, development sites
  - **Communication**: Slack, Teams, Discord, Zoom
  - **File Management**: File Explorer activities
  - **Browsing**: General web browsing
  
- **Beautiful Visualizations**:
  - Activity distribution bar chart
  - Weekly productivity trend line chart
  - Productivity score ring chart
  - Detailed category breakdowns

- **Productivity Analytics**:
  - Calculated productivity score (0-100%)
  - Total active time tracking
  - Top category identification
  - Historical trends

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database**:
   - Copy `.env.example` to `.env`
   - Update database credentials:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=timesheet_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

3. **Run the Dashboard**:
   ```bash
   # Windows
   start_dashboard.bat
   
   # Or manually
   cd backend
   python dashboard_api_enhanced.py
   ```

4. **Access Dashboard**:
   Open http://localhost:5001 in your browser

## Usage

1. **Select Developer**: Choose a developer from the dropdown
2. **Pick Date**: Select the date to view activities (defaults to today)
3. **View Analytics**: 
   - Productivity score and trends
   - Time spent by category
   - Detailed activity breakdowns

## Database Schema Requirements

The dashboard expects an `activity_records` table with:
- `developer_id` (integer)
- `app` (text) - Application name (e.g., "chrome.exe", "Code.exe")
- `title` (text) - Window title
- `timestamp` (timestamp)
- `duration` (integer) - Duration in seconds

## Customization

### Add New Categories

Edit `backend/activity_analyzer.py` to add new categorization rules:

```python
# Example: Add IDE category
elif "pycharm" in app_lower or "intellij" in app_lower:
    return "ide", "JetBrains IDE"
```

### Change Colors

Edit `frontend/static/css/dashboard.css` to customize colors:

```css
:root {
    --primary-color: #6366f1;  /* Change main color */
    --success-color: #10b981;  /* Change productivity color */
}
```

### Productivity Weights

Adjust productivity calculation in `activity_analyzer.py`:

```python
productive_categories = {
    'project': 1.0,      # 100% productive
    'cloud': 0.9,        # 90% productive
    # Add your weights here
}
```

## API Endpoints

- `GET /` - Dashboard UI
- `GET /api/dashboard/<developer_id>?date=YYYY-MM-DD` - Dashboard data
- `GET /api/productivity/<developer_id>/weekly` - Weekly trend
- `GET /api/developers` - List all developers
- `GET /api/test-connection` - Test database connection

## Troubleshooting

### Database Connection Issues
1. Check `.env` file has correct credentials
2. Ensure PostgreSQL is running
3. Test connection: http://localhost:5001/api/test-connection

### No Data Showing
1. Verify ActivityWatch sync is running
2. Check database has activity records
3. Ensure developer_id matches in sync script

### Dashboard Not Loading
1. Check all dependencies are installed
2. Verify port 5001 is not in use
3. Check browser console for errors

## Architecture

```
timesheet_new/
├── backend/
│   ├── activity_analyzer.py      # Activity categorization logic
│   └── dashboard_api_enhanced.py # Flask API server
├── frontend/
│   ├── templates/
│   │   └── dashboard.html        # Dashboard UI
│   └── static/
│       ├── css/
│       │   └── dashboard.css     # Beautiful styles
│       └── js/
│           └── dashboard.js      # Dashboard functionality
```

## Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Export reports to PDF
- [ ] Team productivity comparisons
- [ ] Custom time range selection
- [ ] Email productivity reports
- [ ] Mobile responsive improvements

## License

This project is part of the timesheet system and follows the same license terms.
