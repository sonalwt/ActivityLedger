// DeveloperDashboard.js - Fully updated with FastAPI integration and date filters
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format, startOfDay, endOfDay } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import ActivityChart from './ActivityChart';
import ActivityTable from './ActivityTable';
import ProductivityMetrics from './ProductivityMetrics';
import ProjectBreakdown from './ProjectBreakdown';
import CategoryBreakdown from './CategoryBreakdown';
import { Calendar, RefreshCw, Activity, Clock, ChevronDown, ChevronUp, ArrowLeft, BarChart2, Briefcase, FolderOpen } from 'lucide-react';
import './DeveloperDashboard.css';

// Live Daily Hours Component
const LiveDailyHoursReport = ({ activityData }) => {
  const calculateDailyHours = () => {
    const dailyData = {};

    activityData.forEach(activity => {
      if (!activity.timestamp) return;

      const date = new Date(activity.timestamp).toISOString().split('T')[0];
      if (!dailyData[date]) {
        dailyData[date] = { total: 0, activities: 0 };
      }
      dailyData[date].total += activity.duration || 0;
      dailyData[date].activities += 1;
    });

    return Object.entries(dailyData).map(([date, data]) => ({
      date,
      total_hours: data.total / 3600,
      activities: data.activities,
      color: data.total / 3600 >= 8 ? '#10b981' : 
             data.total / 3600 >= 6 ? '#f59e0b' : 
             data.total / 3600 >= 4 ? '#f97316' : '#ef4444'
    })).sort((a, b) => new Date(a.date) - new Date(b.date));
  };

  const dailyHours = calculateDailyHours();
  const totalHours = dailyHours.reduce((sum, day) => sum + day.total_hours, 0);
  const avgHours = dailyHours.length > 0 ? totalHours / dailyHours.length : 0;

  return (
    <div className="report-card">
      <h3>📅 Daily Hours Report</h3>
      <div className="report-stats-grid">
        <div className="report-stat-item">
          <div className="report-stat-value">{totalHours.toFixed(1)}h</div>
          <div className="report-stat-label">Total Hours</div>
        </div>
        <div className="report-stat-item green">
          <div className="report-stat-value">{avgHours.toFixed(1)}h</div>
          <div className="report-stat-label">Average/Day</div>
        </div>
      </div>
      <div className="daily-hours-list">
        {dailyHours.map(day => {
          const hourClass = day.total_hours >= 8 ? 'excellent' : 
                           day.total_hours >= 6 ? 'good' : 
                           day.total_hours >= 4 ? 'fair' : 'low';
          return (
            <div key={day.date} className={`daily-hour-item ${hourClass}`}>
              <div>
                <span className="daily-hour-date">{format(new Date(day.date), 'MMM d, yyyy')}</span>
                <span className="daily-hour-activities">({day.activities} activities)</span>
              </div>
              <div className={`daily-hour-value ${hourClass}`}>{day.total_hours.toFixed(1)}h</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Live Productivity Component
const LiveProductivityDashboard = ({ activityData }) => {
  const calculateProductivity = () => {
    const totalTime = activityData.reduce((sum, activity) => sum + (activity.duration || 0), 0);
    const workTime = activityData
      .filter(activity => ['productivity', 'development', 'browser', 'server'].includes(activity.category))
      .reduce((sum, activity) => sum + (activity.duration || 0), 0);

    const productivityScore = totalTime > 0 ? (workTime / totalTime) * 100 : 0;

    const categories = ['productivity', 'browser', 'server', 'non-work', 'uncategorized'].map(cat => {
      const categoryTime = activityData
        .filter(activity => activity.category === cat)
        .reduce((sum, activity) => sum + (activity.duration || 0), 0);
      return {
        name: cat,
        time: categoryTime / 3600,
        percentage: totalTime > 0 ? (categoryTime / totalTime) * 100 : 0
      };
    });

    return {
      totalTime: totalTime / 3600,
      workTime: workTime / 3600,
      productivityScore: Math.round(productivityScore),
      categories
    };
  };

  const productivity = calculateProductivity();

  return (
    <div className="productivity-card">
      <h3>📊 Productivity Analysis</h3>
      <div className="productivity-metrics">
        <div className="productivity-metric primary">
          <div className="metric-value primary">{productivity.productivityScore}%</div>
          <div className="metric-label">Productivity Score</div>
        </div>
        <div className="productivity-metric success">
          <div className="metric-value success">{productivity.workTime.toFixed(1)}h</div>
          <div className="metric-label">Work Time</div>
        </div>
        <div className="productivity-metric warning">
          <div className="metric-value warning">{productivity.totalTime.toFixed(1)}h</div>
          <div className="metric-label">Total Time</div>
        </div>
      </div>

      <div className="category-breakdown">
        <h4>Category Breakdown</h4>
        {productivity.categories.map(category => {
          const categoryClass = category.name.toLowerCase().replace(/\s+/g, '-');
          return (
            <div key={category.name} className="category-item">
              <div className="category-header">
                <span className="category-name">{category.name}</span>
                <span className="category-stats">{category.time.toFixed(1)}h ({category.percentage.toFixed(1)}%)</span>
              </div>
              <div className="category-progress">
                <div className={`category-progress-bar ${categoryClass}`} style={{ width: `${category.percentage}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

function DeveloperDashboard({ developer, onBack }) {
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(startOfDay(new Date()));
  const [endDate, setEndDate] = useState(endOfDay(new Date()));
  const [totalTime, setTotalTime] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);
  const [activeTab, setActiveTab] = useState('activity');

  const API_BASE = process.env.REACT_APP_API_URL || '';

  const fetchActivityData = async () => {
    setLoading(true);
    try {
      if (!developer) return;

      const developerId = developer.developer_id || developer.id;

      const response = await axios.get(`${API_BASE}/api/activity-data/${developerId}`, {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        }
      });

      const data = response.data.data || [];
      const total_time = response.data.total_time || 0;
      const category_data = response.data.category_breakdown || null;

      setActivityData(data);
      setTotalTime(total_time);
      setCategoryBreakdown(category_data);
      setLastUpdated(new Date());

      console.log('Fetched activity data:', data);
      console.log('Category breakdown:', category_data);

    } catch (error) {
      console.error('Error fetching activity data:', error);
      toast.error('Failed to fetch activity data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (developer) {
      fetchActivityData();
    }
  }, [startDate, endDate, developer]);

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const extractProjectInfo = (item) => {
    if (item.project_name) return { project: item.project_name, type: item.project_type || 'Work' };
    if (item.application_name) return { project: item.application_name.replace('.exe', ''), type: 'Work' };
    return { project: 'General Work', type: 'Work' };
  };

  return (
    <div className="developer-dashboard">
      <div className="dev-dashboard-header">
        <div className="header-left">
          {onBack && <button onClick={onBack} className="back-button"><ArrowLeft size={16} />Back</button>}
          <h1 className="dev-dashboard-title"><Activity size={36} color="#667eea" />{developer ? `${developer.name}'s Dashboard` : 'Activity Dashboard'}</h1>
        </div>
        <div className="dashboard-controls">
          <div className="date-picker-wrapper">
            <Calendar size={20} color="#667eea" />
            <DatePicker selected={startDate} onChange={setStartDate} selectsStart startDate={startDate} endDate={endDate} dateFormat="MMM d, yyyy" />
            <span>to</span>
            <DatePicker selected={endDate} onChange={setEndDate} selectsEnd startDate={startDate} endDate={endDate} minDate={startDate} dateFormat="MMM d, yyyy" />
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <Clock size={32} color="#667eea" className="stat-icon" />
          <h3>Total Time</h3>
          <p className="stat-value">{formatTime(totalTime)}</p>
        </div>
        <div className="stat-card">
          <Activity size={32} color="#28a745" className="stat-icon" />
          <h3>Active Projects</h3>
          <p className="stat-value green">{new Set(activityData.map(item => extractProjectInfo(item).project)).size}</p>
          <p className="stat-subtitle">in selected period</p>
        </div>
        <div className="stat-card">
          <RefreshCw size={32} color="#ffc107" className="stat-icon" />
          <h3>Last Updated</h3>
          <p className="stat-value yellow">{lastUpdated ? format(lastUpdated, 'MMM d, yyyy HH:mm') : 'Never'}</p>
        </div>
      </div>

      {!loading && (
        <>
          {categoryBreakdown && (
            <div className="category-summary">
              <h3>Activity Categories</h3>
              <div className="category-cards">
                {['productivity', 'browser', 'server', 'uncategorized', 'non-work'].map(cat => (
                  <div key={cat} className={`category-card ${cat}`}>
                    <div className="category-icon">{cat === 'productivity' ? '💻' : cat === 'browser' ? '🌐' : cat === 'server' ? '☁️' : cat === 'non-work' ? '🎮' : '❓'}</div>
                    <h4>{cat.charAt(0).toUpperCase() + cat.slice(1)}</h4>
                    <p className="category-percentage">{categoryBreakdown[cat]?.percentage || 0}%</p>
                    <p className="category-time">{categoryBreakdown[cat]?.hours || 0}h</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <LiveDailyHoursReport activityData={activityData} />
          <LiveProductivityDashboard activityData={activityData} />
        </>
      )}

      {loading && <div className="loading-spinner-container"><div className="spinner loading-spinner"></div><p className="loading-text">Loading activity data...</p></div>}
    </div>
  );
}

export default DeveloperDashboard;
