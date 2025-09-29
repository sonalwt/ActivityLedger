# 🕒 Timesheet Application - Project Overview

## 🎯 Project Purpose

This is an **intelligent productivity tracking system** that integrates with ActivityWatch to automatically monitor computer usage and convert raw activity data into meaningful work metrics. Unlike simple time trackers, this application provides sophisticated analysis to determine actual productive work time from total computer usage.

## 🏗️ Architecture Overview

### Tech Stack
- **Backend**: FastAPI with SQLAlchemy ORM
- **Frontend**: React 18 with modern hooks and components
- **Database**: PostgreSQL (with SQLite option for development)
- **Authentication**: JWT-based secure authentication
- **Data Source**: ActivityWatch integration for real-time activity tracking
- **Charts**: Recharts for interactive visualizations

### Core Components

#### Backend (`/backend/`)
- **`main.py`**: FastAPI application with comprehensive API endpoints
- **`activitywatch_client.py`**: ActivityWatch integration and data fetching
- **`realistic_hours_calculator.py`**: Advanced working hours calculation with smart weighting
- **`productivity_calculator.py`**: Productivity analysis with focus sessions and time-based multipliers
- **`models.py`**: SQLAlchemy models for Users and ActivityRecords
- **`auth.py`**: JWT authentication and password hashing
- **`crud.py`**: Database operations and data processing

#### Frontend (`/frontend/src/`)
- **`Dashboard.js`**: Main interface with daily breakdowns and analytics
- **`DailyHoursReport.js`**: Color-coded daily hours visualization
- **`ProductivityDashboard.js`**: Advanced productivity metrics display
- **`ActivityChart.js`**: Interactive pie charts using Recharts
- **`ActivityTable.js`**: Detailed activity breakdowns with filtering

## 🧮 Core Calculation Logic

### Working Hours Calculation
The system uses **intelligent category-based weighting** to determine productive work time:

```
Category Weights:
- Development (VS Code, Cursor, PyCharm): 100% productive
- Database Tools (DataGrip, pgAdmin): 100% productive  
- Productivity (Office, Slack, Teams): 100% productive
- Browser Activity: 85% productive (research/docs)
- System Tools: 10% productive
- Entertainment: 0% productive
```

### Advanced Features
- **Time-based multipliers**: Peak hours (9 AM - 5 PM) get 1.2x weight
- **Focus session bonuses**: Continuous work sessions get productivity bonuses
- **Deep work detection**: 3+ hour focus sessions receive 1.5x bonus
- **Smart app analysis**: Unknown apps get intelligent analysis for productivity value

## 📊 Key Metrics Explained

### Dashboard Numbers
When you see values like **"0.59h of 0.62h total (95.3% productive)"**:

- **0.59h**: Calculated productive work time using intelligent weighting
- **0.62h**: Raw computer usage time from ActivityWatch  
- **95.3%**: Productivity percentage (Working Hours ÷ Total Hours × 100)
- **Activities Count**: Number of individual activities tracked (app switches, window changes)

### Color Coding
- 🟢 **Green**: 8+ working hours (Excellent)
- 🟡 **Yellow**: 6-8 working hours (Good)  
- 🔴 **Red**: <6 working hours (Needs improvement)

## 🗃️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Activity Records Table
```sql
CREATE TABLE activity_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    application_name VARCHAR,
    window_title TEXT,
    url TEXT,
    file_path TEXT,
    category VARCHAR,
    duration FLOAT,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔌 API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /token` - JWT login  
- `GET /users/me` - Current user info

### Core Data
- `GET /activity-data` - Sync data from ActivityWatch and store in database
- `GET /activity-summary` - Get processed activity summary from database
- `GET /daily-hours` - Daily working hours report with color coding
- `GET /productivity-analysis` - Advanced productivity metrics
- `GET /top-window-titles` - Most used applications/windows

## 🛠️ Development Tools & Scripts

### Data Analysis Scripts
- **`check_any_date.py`**: Verify calculations for any specific date
- **`debug_working_hours.py`**: Debug hour calculations step by step
- **`explain_dashboard_numbers.py`**: Explain dashboard metrics in detail
- **`test_realistic_hours.py`**: Test realistic hours calculation
- **`view_saved_data.py`**: Inspect saved activity data

### Database Management
- **`setup_postgres.py`**: PostgreSQL database setup
- **`create_user.py`**: Create test users
- **`clean_duplicates.py`**: Remove duplicate activity records
- **`migrate_detailed_info.py`**: Database migrations

### Discovery & Analysis  
- **`developer_discovery.py`**: Discover development patterns
- **`project_extractor.py`**: Extract project information from activities
- **`dynamic_discovery.py`**: Dynamic activity pattern discovery

## 🚀 Quick Start Commands

### Setup & Installation
```bash
# Setup (Windows)
setup.bat

# Start application (Windows)  
start_app.bat

# Manual startup
# Backend:
cd backend && python -m uvicorn main:app --reload --port 8000

# Frontend:
cd frontend && npm start
```

### Environment Configuration
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/timesheet
SECRET_KEY=your-super-secret-key-change-this
ACTIVITYWATCH_HOST=http://localhost:5600
```

## 📈 Advanced Features

### 1. **Smart Activity Categorization**
- Automatic categorization of 100+ common applications
- Browser URL extraction and analysis
- Development file path tracking
- Project detection from window titles

### 2. **Productivity Analysis**
- Focus session detection and scoring
- Peak hours analysis (9 AM - 5 PM multiplier)
- Deep work identification (3+ hour sessions)
- Distraction pattern analysis

### 3. **Real-time Data Validation**
- Multiple validation scripts ensure accuracy
- Step-by-step debugging tools
- Data integrity checks
- Calculation verification utilities

### 4. **Dynamic Discovery**
- Automatic discovery of new development patterns
- Project extraction from file paths
- Dynamic endpoint generation
- Pattern learning from user behavior

## 🎨 Frontend Features

### Interactive Dashboard
- **Date Navigation**: Easy date range selection
- **Real-time Sync**: Live data updates from ActivityWatch
- **Responsive Design**: Works on desktop and mobile
- **Toast Notifications**: User feedback for all actions

### Advanced Visualizations
- **Pie Charts**: Interactive category breakdowns
- **Daily Reports**: Color-coded productivity tracking
- **Activity Tables**: Sortable, filterable detailed views
- **Progress Bars**: Visual duration indicators

## 🔧 Configuration Options

### ActivityWatch Integration
- Configurable host/port settings
- Custom date range queries
- Real-time data synchronization
- Automatic categorization rules

### Database Options
- PostgreSQL for production
- SQLite for development
- Configurable connection strings
- Migration support with Alembic

### Authentication
- JWT token-based security
- Configurable token expiration
- Secure password hashing with bcrypt
- User session management

## 📊 Sample Data Flow

1. **ActivityWatch** collects raw system activity data
2. **Backend** fetches data via ActivityWatch API
3. **Processing** categorizes apps, extracts URLs, calculates durations
4. **Database** stores processed activity records with user association
5. **Calculation** applies intelligent weighting to determine work time
6. **Frontend** displays analytics with charts, tables, and summaries
7. **User** views productivity insights and filters by date ranges

## 🎯 Use Cases

### Individual Productivity
- Track actual working hours vs. computer time
- Identify productivity patterns and peak hours
- Monitor focus sessions and deep work
- Analyze time distribution across projects

### Time Tracking & Reporting
- Generate accurate timesheets for clients
- Validate billing hours with data
- Track project time allocation
- Monitor work-life balance

### Productivity Optimization
- Identify distraction sources
- Optimize work schedules based on productivity data
- Track improvement over time
- Set realistic productivity goals

## 🔍 Troubleshooting Guide

### Common Issues
1. **ActivityWatch Connection**: Ensure AW is running on localhost:5600
2. **Database Connection**: Verify PostgreSQL is running and accessible
3. **Low Productivity %**: Check if main work apps are properly categorized
4. **Missing Data**: Ensure ActivityWatch has proper permissions
5. **Frontend Errors**: Check if backend API is accessible on port 8000

### Debug Tools
- Use `check_any_date.py` to verify specific day calculations
- Run `debug_working_hours.py` for step-by-step analysis
- Check `explain_dashboard_numbers.py` for metric explanations
- Use browser developer tools for frontend debugging

## 📝 Important Notes for Future Development

### Code Organization
- Backend follows FastAPI best practices with clear separation of concerns
- Frontend uses modern React patterns with hooks and context
- Database operations are abstracted through CRUD layer
- Authentication is handled consistently across all endpoints

### Extensibility
- New activity categories can be easily added
- Calculation algorithms are modular and replaceable
- Database schema supports additional fields without breaking changes
- API endpoints follow RESTful conventions for easy expansion

### Performance Considerations
- Database queries are optimized with proper indexing
- Activity data is processed in batches to handle large datasets
- Frontend implements efficient re-rendering with React optimization
- Caching strategies are in place for frequently accessed data

This project represents a sophisticated productivity tracking system that goes far beyond simple time tracking, providing actionable insights through intelligent data analysis and modern web technologies.
