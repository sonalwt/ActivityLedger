# 📊 Timesheet Application - Complete Documentation

## 🎯 What This Application Does

This is an **intelligent timesheet system** that automatically tracks your computer activity using ActivityWatch and calculates meaningful work metrics. It goes beyond simple time tracking by analyzing **what** you're doing and determining how much of that time is actually productive work.

## 🔢 Understanding Your Numbers

### Daily Breakdown Explained

When you see values like:
- **0.59h** of 0.62h total (95.3% productive)
- **1.02h** of 2.4h total (42.6% productive)

Here's what they mean:

#### **Working Hours (0.59h, 1.02h)**
This is the **calculated productive work time** based on intelligent analysis of your activities. Not all computer time is work time!

#### **Total Hours (0.62h, 2.4h)**
This is the **raw time tracked** by ActivityWatch - every second your computer was active.

#### **Productivity Percentage (95.3%, 42.6%)**
This is **Working Hours ÷ Total Hours × 100** - showing what percentage of your computer time was actually productive.

#### **Activities Count (56, 131)**
This is the **number of individual activities** tracked - every app switch, window change, or website visit counts as one activity.

## 🧮 How Working Hours Are Calculated

The system uses **smart category-based weighting** to determine productive time:

### Category Weights

| Category | Weight | Examples | Reasoning |
|----------|--------|----------|-----------|
| **Development** | 100% | VS Code, Cursor, PyCharm, IntelliJ | All coding time is work |
| **Database** | 100% | DataGrip, pgAdmin, SQL tools | All database work is productive |
| **Productivity** | 100% | Office apps, Slack, Teams, Notion | All productivity tools are work |
| **Browser** | 85% | Chrome, Firefox, Safari | Most browsing is work-related (docs, research) |
| **Other** | Smart Analysis | Various apps | Intelligent per-app analysis |
| **System** | 10% | File Explorer, Task Manager | Minimal productivity value |
| **Entertainment** | 0% | Spotify, YouTube, Netflix | Not work time |

### Smart Analysis for "Other" Category

The system intelligently analyzes unknown applications:

```python
if 'lockapp' in app.lower():
    work_time = app_time * 0.9  # 90% work time
elif 'datagrip' in app.lower() or 'postman' in app.lower():
    work_time = app_time * 1.0  # 100% work time  
elif 'snipping' in app.lower():
    work_time = app_time * 0.9  # 90% work time
else:
    work_time = app_time * 0.5  # 50% work time (conservative)
```

## 📈 Status Color Coding

Your daily hours are color-coded based on productivity:

- 🟢 **GREEN (Excellent)**: 8+ working hours
- 🟡 **YELLOW (Good)**: 6-8 working hours  
- 🔴 **RED (Low)**: Less than 6 working hours

## 🔍 What Gets Tracked

### Activity Records
Every activity record contains:

- **Application Name**: The program you were using
- **Window Title**: What was displayed in the window
- **Duration**: How long you spent (in seconds)
- **Timestamp**: When the activity occurred
- **Category**: Automatically assigned category
- **URL**: For browser activities, the website visited
- **File Path**: For development, the file you were editing

### Example Activity Record
```json
{
  "application_name": "Cursor.exe",
  "window_title": "backend/main.py - timesheet",
  "duration": 180,
  "timestamp": "2025-09-15T10:30:00Z",
  "category": "development",
  "file_path": "E:/timesheet/backend/main.py"
}
```

## 🏗️ System Architecture

### Backend Components

#### 1. **ActivityWatch Client** (`activitywatch_client.py`)
- Connects to ActivityWatch API
- Fetches raw activity data
- Categorizes applications automatically
- Extracts URLs from browser titles

#### 2. **Hours Calculators**
- **`daily_hours_calculator.py`**: Basic daily hour calculations
- **`realistic_hours_calculator.py`**: Advanced realistic working hours
- **`productivity_calculator.py`**: Productivity scoring with focus sessions

#### 3. **Database Models** (`models.py`)
- **User**: Authentication and user management
- **ActivityRecord**: Core activity tracking data

#### 4. **API Endpoints** (`main.py`)
- `/daily-hours`: Get daily working hours report
- `/productivity-analysis`: Get productivity analysis
- `/activity-data`: Sync from ActivityWatch
- `/activity-summary`: Get processed summary

### Frontend Components

#### 1. **Dashboard** (`Dashboard.js`)
- Main interface showing daily breakdown
- Date filtering and navigation
- Real-time data synchronization

#### 2. **Charts & Tables**
- **ActivityChart.js**: Interactive pie charts
- **ActivityTable.js**: Detailed activity breakdowns
- **DailyHoursReport.js**: Daily hours visualization

## 🎛️ Advanced Features

### 1. **Productivity Analysis**
Beyond basic time tracking, the system includes:

- **Time-based multipliers**: Peak hours (9-5) get 1.2x weight
- **Focus session bonuses**: Continuous work gets productivity bonuses
- **Deep work detection**: 3+ hour focus sessions get 1.5x bonus

### 2. **Smart Browser Tracking**
- Extracts actual URLs from browser window titles
- Categorizes websites (work vs entertainment)
- Tracks research and documentation time

### 3. **Development Workflow Tracking**
- Tracks specific files being edited
- Monitors IDE usage patterns
- Database connection tracking

### 4. **Real-time Data Validation**
The system includes multiple validation scripts:

- **`check_any_date.py`**: Verify calculations for any date
- **`debug_working_hours.py`**: Debug hour calculations
- **`explain_dashboard_numbers.py`**: Explain dashboard metrics

## 🔧 Configuration & Setup

### Environment Variables
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/timesheet
SECRET_KEY=your-super-secret-key
ACTIVITYWATCH_HOST=http://localhost:5600
```

### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Activity records table  
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

## 📊 Sample Calculations

### Example Day Analysis

**Raw Data:**
- Chrome: 45 minutes (browser category)
- VS Code: 120 minutes (development category)  
- Slack: 15 minutes (productivity category)
- YouTube: 30 minutes (entertainment category)

**Calculation:**
```
Chrome:   45 min × 0.85 = 38.25 min working time
VS Code: 120 min × 1.00 = 120.00 min working time  
Slack:    15 min × 1.00 = 15.00 min working time
YouTube:  30 min × 0.00 = 0.00 min working time

Total Time: 210 minutes (3.5 hours)
Working Time: 173.25 minutes (2.89 hours)
Productivity: 82.5%
```

## 🚀 Usage Tips

### 1. **Interpreting Your Data**
- High activity count usually means task switching
- Low productivity % might indicate distraction or breaks
- Consistent 8+ hour days show good work habits

### 2. **Improving Productivity**
- Focus on longer sessions in development tools
- Minimize entertainment during work hours
- Use the data to identify distraction patterns

### 3. **Data Accuracy**
- The system learns from your patterns
- Manual categorization overrides are possible
- Regular ActivityWatch sync ensures fresh data

## 🔍 Troubleshooting

### Common Issues

1. **Low Working Hours Despite Feeling Productive**
   - Check if your main work apps are properly categorized
   - Browser time is weighted at 85% (not 100%)
   - System/background apps have low productivity weights

2. **High Activity Count**
   - This is normal - every window switch counts
   - Indicates multitasking or frequent app switching
   - Not necessarily bad, just different work style

3. **Missing Time**
   - Ensure ActivityWatch is running continuously
   - Check for computer sleep/hibernate periods
   - Verify ActivityWatch permissions

## 📈 Future Enhancements

Potential improvements to consider:

1. **Machine Learning**: Learn personal productivity patterns
2. **Goal Setting**: Set daily/weekly hour targets
3. **Team Analytics**: Compare productivity across team members
4. **Custom Categories**: User-defined application categories
5. **Time Blocking**: Integration with calendar systems

## 🎯 Key Takeaways

Your timesheet system is **not just a time tracker** - it's an **intelligent productivity analyzer** that:

- ✅ Automatically categorizes all your computer activities
- ✅ Calculates realistic working hours using smart weighting
- ✅ Provides actionable productivity insights
- ✅ Tracks detailed patterns for optimization
- ✅ Validates calculations to ensure accuracy

The **0.59h** and **1.02h** values represent your actual productive work time, calculated from raw computer usage data using intelligent analysis of what you were actually doing.
