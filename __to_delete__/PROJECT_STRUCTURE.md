# Project Structure

```
timesheet/
├── backend/                          # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                      # FastAPI app and routes
│   ├── database.py                  # Database configuration
│   ├── models.py                    # SQLAlchemy models
│   ├── schemas.py                   # Pydantic schemas
│   ├── crud.py                      # Database operations
│   ├── auth.py                      # Authentication logic
│   ├── activitywatch_client.py      # ActivityWatch integration
│   └── sample_data.py               # Sample data generator
│
├── frontend/                        # React Frontend
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.js             # Login page
│   │   │   ├── Register.js          # Registration page
│   │   │   ├── Navbar.js            # Navigation bar
│   │   │   ├── Dashboard.js         # Main dashboard
│   │   │   ├── ActivityChart.js     # Pie chart component
│   │   │   └── ActivityTable.js     # Data table component
│   │   ├── contexts/
│   │   │   └── AuthContext.js       # Authentication context
│   │   ├── App.js                   # Main App component
│   │   ├── index.js                 # React entry point
│   │   └── index.css                # Global styles
│   └── package.json                 # Frontend dependencies
│
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── README.md                        # Project documentation
├── PROJECT_STRUCTURE.md             # This file
├── setup.bat                        # Setup script for Windows
├── start_app.bat                    # Application launcher
├── run_backend.py                   # Backend runner script
├── run_backend.bat                  # Backend runner (Windows)
└── run_frontend.bat                 # Frontend runner (Windows)
```

## Key Components

### Backend (FastAPI)

**main.py**
- FastAPI application setup
- CORS configuration
- Authentication routes
- Activity data endpoints

**models.py**
- User model (id, username, email, password)
- ActivityRecord model (app, duration, timestamp, etc.)

**activitywatch_client.py**
- ActivityWatch API integration
- Data fetching and processing
- Application categorization
- URL extraction from browser titles

**auth.py**
- JWT token creation and verification
- Password hashing with bcrypt
- User authentication

### Frontend (React)

**Dashboard.js**
- Main application interface
- Date range filtering
- Activity data synchronization
- Statistics display

**ActivityChart.js**
- Interactive pie chart using Recharts
- Color-coded categories
- Hover tooltips with details

**ActivityTable.js**
- Sortable data table
- Expandable rows for URL details
- Category icons and progress bars

**AuthContext.js**
- Global authentication state
- JWT token management
- API request interceptors

## Data Flow

1. **ActivityWatch** → Collects system activity data
2. **Backend** → Fetches data from ActivityWatch API
3. **Processing** → Categorizes apps, extracts URLs, calculates durations
4. **Database** → Stores processed activity records
5. **Frontend** → Displays data with charts and tables
6. **User** → Filters by date, views analytics

## Features Implemented

✅ User registration and authentication
✅ JWT-based security
✅ ActivityWatch integration
✅ Real-time data synchronization
✅ Interactive pie charts
✅ Detailed activity tables
✅ Date range filtering
✅ Application categorization
✅ Browser URL tracking
✅ Responsive design
✅ Sample data generator
✅ Setup and run scripts

## Categories

- **Browser**: Chrome, Firefox, Safari, Edge
- **Development**: VS Code, PyCharm, IntelliJ, Cursor
- **Productivity**: Office apps, Slack, Teams, Notion
- **Entertainment**: Spotify, YouTube, Netflix
- **System**: Explorer, Terminal, Task Manager
