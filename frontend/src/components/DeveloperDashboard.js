// DeveloperDashboard.js - Your original dashboard with live data fixes
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
import { Calendar, RefreshCw, Activity, Clock, ChevronDown, ChevronUp, ArrowLeft, BarChart2, Briefcase, FileText } from 'lucide-react';
import './DeveloperDashboard.css';

// Live Daily Hours Component
const LiveDailyHoursReport = ({ activityData, startDate, endDate }) => {
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
          <div className="report-stat-value">
            {totalHours.toFixed(1)}h
          </div>
          <div className="report-stat-label">Total Hours</div>
        </div>
        <div className="report-stat-item green">
          <div className="report-stat-value">
            {avgHours.toFixed(1)}h
          </div>
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
                <span className="daily-hour-activities">
                  ({day.activities} activities)
                </span>
              </div>
              <div className={`daily-hour-value ${hourClass}`}>
                {day.total_hours.toFixed(1)}h
              </div>
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
    const workCategories = ['Development', 'Web Browsing', 'Productivity'];
    const totalTime = activityData.reduce((sum, activity) => sum + (activity.duration || 0), 0);
    const workTime = activityData
      .filter(activity => workCategories.includes(activity.category))
      .reduce((sum, activity) => sum + (activity.duration || 0), 0);
    
    const productivityScore = totalTime > 0 ? (workTime / totalTime) * 100 : 0;
    
    return {
      totalTime: totalTime / 3600,
      workTime: workTime / 3600,
      productivityScore: Math.round(productivityScore),
      categories: workCategories.map(category => {
        const categoryTime = activityData
          .filter(activity => activity.category === category)
          .reduce((sum, activity) => sum + (activity.duration || 0), 0);
        return {
          name: category,
          time: categoryTime / 3600,
          percentage: totalTime > 0 ? (categoryTime / totalTime) * 100 : 0
        };
      })
    };
  };

  const productivity = calculateProductivity();

  return (
    <div className="productivity-card">
      <h3>📊 Productivity Analysis</h3>
      
      <div className="productivity-metrics">
        <div className="productivity-metric primary">
          <div className="metric-value primary">
            {productivity.productivityScore}%
          </div>
          <div className="metric-label">Productivity Score</div>
        </div>
        <div className="productivity-metric success">
          <div className="metric-value success">
            {productivity.workTime.toFixed(1)}h
          </div>
          <div className="metric-label">Work Time</div>
        </div>
        <div className="productivity-metric warning">
          <div className="metric-value warning">
            {productivity.totalTime.toFixed(1)}h
          </div>
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
                <span className="category-stats">
                  {category.time.toFixed(1)}h ({category.percentage.toFixed(1)}%)
                </span>
              </div>
              <div className="category-progress">
                <div 
                  className={`category-progress-bar ${categoryClass === 'development' ? 'development' : categoryClass === 'web-browsing' ? 'browsing' : 'productivity'}`}
                  style={{ width: `${category.percentage}%` }}
                />
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
  const [topWindowTitles, setTopWindowTitles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(startOfDay(new Date()));
  const [endDate, setEndDate] = useState(endOfDay(new Date()));
  const [totalTime, setTotalTime] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isTopActivitiesOpen, setIsTopActivitiesOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('activity');

  const API_BASE = process.env.REACT_APP_API_URL || 'api-timesheet.firsteconomy.com';

  const fetchActivityData = async (fetchFromAW = false) => {
    setLoading(true);
    try {
      let response;
      
      if (developer) {
        // Use new API for specific developer
        response = await axios.get(`${API_BASE}/activity-data/${developer.id}`, {
          params: {
            start_date: startDate.toISOString(),
            end_date: endDate.toISOString()
          }
        });
      } else {
        // Fallback to old API
        const endpoint = fetchFromAW ? '/activity-data' : '/activity-summary';
        response = await axios.get(`${API_BASE}${endpoint}`, {
          params: {
            start_date: startDate.toISOString(),
            end_date: endDate.toISOString()
          }
        });
      }

      setActivityData(response.data.data || []);
      setTotalTime(response.data.total_time || 0);
      setLastUpdated(new Date());
      
      if (fetchFromAW) {
        toast.success('Activity data synced from ActivityWatch!');
      }
    } catch (error) {
      console.error('Error fetching activity data:', error);
      if (error.response?.status === 500 && fetchFromAW) {
        toast.error('Could not connect to ActivityWatch. Make sure it\'s running on localhost:5600');
      } else {
        toast.error('Failed to fetch activity data');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchTopWindowTitles = async () => {
    try {
      const response = await axios.get(`${API_BASE}/top-window-titles`, {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
          limit: 30
        }
      });

      setTopWindowTitles(response.data.top_window_titles || []);
    } catch (error) {
      console.error('Error fetching top window titles:', error);
    }
  };

  useEffect(() => {
    fetchActivityData(false);
    if (!developer) {
      fetchTopWindowTitles();
    }
  }, [startDate, endDate, developer]);

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatDecimalHoursToHoursMinutes = (decimalHoursString) => {
    const numericValue = parseFloat(decimalHoursString.replace(/[^\d.]/g, ''));
    
    if (isNaN(numericValue)) return decimalHoursString;
    
    const hours = Math.floor(numericValue);
    const minutes = Math.round((numericValue - hours) * 60);
    
    if (hours > 0 && minutes > 0) {
      return `${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h`;
    } else if (minutes > 0) {
      return `${minutes}m`;
    } else {
      return '0m';
    }
  };

  const isWorkRelatedActivity = (item) => {
    const appName = (item.application_name || '').toLowerCase();
    const windowTitle = (item.window_title || '').toLowerCase();
    const category = (item.category || '').toLowerCase();
    
    const workApps = [
      'cursor', 'vscode', 'visual studio', 'pycharm', 'intellij', 'sublime', 'atom', 'vim', 'emacs', 'notepad++',
      'filezilla', 'winscp', 'putty', 'ssh', 'terminal',
      'plesk', 'cpanel', 'whm', 'directadmin', 'webmin',
      'datagrip', 'pgadmin', 'phpmyadmin', 'mysql', 'postgresql', 'mongodb',
      'postman', 'insomnia', 'git', 'github', 'gitlab', 'docker', 'kubernetes',
      'figma', 'photoshop', 'illustrator', 'canva',
      'notion', 'obsidian', 'trello', 'asana', 'jira', 'confluence'
    ];
    
    const isWorkApp = workApps.some(workApp => appName.includes(workApp));
    const isWorkCategory = ['development', 'database', 'productivity'].includes(category);
    const isWorkBrowser = category === 'browser' && item.urls && item.urls.length > 0 && 
      item.urls.some(url => {
        const domain = url.toLowerCase();
        return domain.includes('github') || domain.includes('stackoverflow') || 
               domain.includes('docs.') || domain.includes('api.') ||
               domain.includes('developer') || domain.includes('tutorial') ||
               domain.includes('plesk') || domain.includes('cpanel') ||
               domain.includes('aws') || domain.includes('azure') || domain.includes('gcp');
      });
    
    const isSystemLock = windowTitle.includes('lock') || windowTitle.includes('locked') || 
                        appName.includes('lockapp') || appName.includes('logonui');
    const isEntertainment = category === 'entertainment' || 
                           windowTitle.includes('youtube') || windowTitle.includes('netflix') ||
                           windowTitle.includes('spotify') || windowTitle.includes('music');
    
    return (isWorkApp || isWorkCategory || isWorkBrowser) && !isSystemLock && !isEntertainment;
  };

  const extractProjectInfo = (item) => {
    if (item.project_name) {
      return { 
        project: item.project_name, 
        type: item.project_type || 'Work',
        file: item.project_file || 'Activity'
      };
    }
    
    const appName = (item.application_name || '').toLowerCase();
    const windowTitle = item.window_title || '';
    
    const isSystemLock = windowTitle.toLowerCase().includes('lock') || windowTitle.toLowerCase().includes('locked') || 
                        appName.includes('lockapp') || appName.includes('logonui');
    const isEntertainment = item.category === 'entertainment' || 
                           windowTitle.toLowerCase().includes('youtube') || windowTitle.toLowerCase().includes('netflix') ||
                           windowTitle.toLowerCase().includes('spotify') || windowTitle.toLowerCase().includes('music');
    
    if (isSystemLock || isEntertainment) {
      return null;
    }
    
    if (appName.includes('cursor') || appName.includes('vscode') || appName.includes('code')) {
      const idePattern = /^(.+?)\s*-\s*(.+?)\s*-\s*(Visual Studio Code|Cursor|Code)/i;
      const ideMatch = windowTitle.match(idePattern);
      
      if (ideMatch) {
        return { project: ideMatch[2].trim(), type: 'Development' };
      }
    }
    
    if (item.application_name && item.application_name.length > 3) {
      return { 
        project: item.application_name.replace('.exe', ''), 
        type: 'Work' 
      };
    }
    
    return { project: 'General Work', type: 'Work' };
  };

  // All inline styles removed - now using CSS classes

  return (
    <div className="developer-dashboard">
      <div className="dev-dashboard-header">
        <div className="header-left">
          {onBack && (
            <button
              onClick={onBack}
              className="back-button"
            >
              <ArrowLeft size={16} />
              Back
            </button>
          )}
          <h1 className="dev-dashboard-title">
            <Activity size={36} color="#667eea" />
            {developer ? `${developer.name}'s Dashboard` : 'Activity Dashboard'}
          </h1>
        </div>
        
        <div className="dashboard-controls">
          <div className="date-picker-wrapper">
            <Calendar size={20} color="#667eea" />
            <DatePicker
              selected={startDate}
              onChange={setStartDate}
              selectsStart
              startDate={startDate}
              endDate={endDate}
              placeholderText="Start Date"
              dateFormat="MMM d, yyyy"
            />
            <span>to</span>
            <DatePicker
              selected={endDate}
              onChange={setEndDate}
              selectsEnd
              startDate={startDate}
              endDate={endDate}
              minDate={startDate}
              placeholderText="End Date"
              dateFormat="MMM d, yyyy"
            />
          </div>
          
          <button
            onClick={() => fetchActivityData(true)}
            disabled={loading}
            className="btn btn-primary"
          >
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            Sync from ActivityWatch
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <Clock size={32} color="#667eea" className="stat-icon" />
          <h3>Total Time</h3>
          <p className="stat-value">
            {formatTime(totalTime)}
          </p>
        </div>
        
        <div className="stat-card">
          <Activity size={32} color="#28a745" className="stat-icon" />
          <h3>Active Projects</h3>
          <p className="stat-value green">
            {(() => {
              const uniqueProjects = new Set();
              activityData.forEach(item => {
                const projectInfo = extractProjectInfo(item);
                if (projectInfo && projectInfo.project) {
                  uniqueProjects.add(projectInfo.project);
                }
              });
              return uniqueProjects.size;
            })()}
          </p>
          <p className="stat-subtitle">
            in selected period
          </p>
        </div>
        
        <div className="stat-card">
          <RefreshCw size={32} color="#ffc107" className="stat-icon" />
          <h3>Last Updated</h3>
          <p className="stat-value yellow">
            {lastUpdated ? format(lastUpdated, 'MMM d, yyyy HH:mm') : 'Never'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="loading-spinner-container">
          <div className="spinner loading-spinner"></div>
          <p className="loading-text">Loading activity data...</p>
        </div>
      )}

      {/* Tab Navigation */}
      {developer && (
        <div className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'activity' ? 'active' : ''}`}
            onClick={() => setActiveTab('activity')}
          >
            <Activity size={16} />
            Activity Data
          </button>
          <button
            className={`tab-button ${activeTab === 'productivity' ? 'active' : ''}`}
            onClick={() => setActiveTab('productivity')}
          >
            <BarChart2 size={16} />
            Productivity
          </button>
          <button
            className={`tab-button ${activeTab === 'projects' ? 'active' : ''}`}
            onClick={() => setActiveTab('projects')}
          >
            <Briefcase size={16} />
            Projects
          </button>
        </div>
      )}

      {/* Tab Content */}
      {!loading && activeTab === 'activity' && activityData.length > 0 && (
        <>
          {/* Category Summary - NEW */}
          <div className="category-summary">
            <h3>Activity Categories</h3>
            <div className="category-cards">
              <div className="category-card productive">
                <div className="category-icon">💻</div>
                <h4>Productive</h4>
                <p className="category-percentage">
                  {(() => {
                    const productiveTime = activityData
                      .filter(item => item.category === 'productive')
                      .reduce((sum, item) => sum + (item.duration || 0), 0);
                    const percentage = totalTime > 0 ? (productiveTime / totalTime * 100).toFixed(1) : 0;
                    return `${percentage}%`;
                  })()}
                </p>
                <p className="category-time">
                  {formatTime(activityData
                    .filter(item => item.category === 'productive')
                    .reduce((sum, item) => sum + (item.duration || 0), 0)
                  )}
                </p>
              </div>
              
              <div className="category-card browser">
                <div className="category-icon">🌐</div>
                <h4>Browser</h4>
                <p className="category-percentage">
                  {(() => {
                    const browserTime = activityData
                      .filter(item => item.category === 'browser')
                      .reduce((sum, item) => sum + (item.duration || 0), 0);
                    const percentage = totalTime > 0 ? (browserTime / totalTime * 100).toFixed(1) : 0;
                    return `${percentage}%`;
                  })()}
                </p>
                <p className="category-time">
                  {formatTime(activityData
                    .filter(item => item.category === 'browser')
                    .reduce((sum, item) => sum + (item.duration || 0), 0)
                  )}
                </p>
              </div>
              
              <div className="category-card server">
                <div className="category-icon">☁️</div>
                <h4>Server</h4>
                <p className="category-percentage">
                  {(() => {
                    const serverTime = activityData
                      .filter(item => item.category === 'server')
                      .reduce((sum, item) => sum + (item.duration || 0), 0);
                    const percentage = totalTime > 0 ? (serverTime / totalTime * 100).toFixed(1) : 0;
                    return `${percentage}%`;
                  })()}
                </p>
                <p className="category-time">
                  {formatTime(activityData
                    .filter(item => item.category === 'server')
                    .reduce((sum, item) => sum + (item.duration || 0), 0)
                  )}
                </p>
              </div>
            </div>
          </div>
          
          {/* Live Daily Hours Report */}
          <LiveDailyHoursReport activityData={activityData} startDate={startDate} endDate={endDate} />
          
          {/* Live Productivity Analysis */}
          <LiveProductivityDashboard activityData={activityData} />
          
          <div className="content-grid">
            <div className="chart-container">
              <h3>Activity Distribution</h3>
              <ActivityChart data={activityData} />
            </div>
            
            <div className="chart-container">
              <h3>
                Project Details
                <span style={{ fontSize: '14px', color: '#666', fontWeight: 'normal', marginLeft: '8px' }}>
                  ({format(startDate, 'MMM d')} - {format(endDate, 'MMM d, yyyy')})
                </span>
              </h3>
              
              {/* Only show top window titles for original dashboard (no developer prop) */}
              {!developer && topWindowTitles.length > 0 && (
                <div className="window-titles-section">
                  <h4>
                    🏆 Top Window Titles from ActivityWatch
                    <span className="live-data-badge">
                      Live Data
                    </span>
                  </h4>
                  
                  <div className="window-titles-grid">
                    {topWindowTitles.map((title, index) => {
                      const projectType = title.project_info?.project_type || 'Work';
                      const projectTypeClass = projectType.toLowerCase().replace(/\s+/g, '-');
                      return (
                        <div key={index} className="window-title-item">
                          <div className="window-title-info">
                            <div className="window-title-header">
                              <span className={`project-type-badge ${projectTypeClass}`}>
                                {projectType}
                              </span>
                              <span className="project-name">
                                {title.project_info?.project_name || title.application_name}
                              </span>
                            </div>
                            
                            <div className="window-title-details">
                              📄 {title.project_info?.file_name || title.window_title}
                            </div>
                            
                            <div className="application-info">
                              💻 {title.application_name} • {title.activity_count} activities
                            </div>
                          </div>
                          
                          <div className="window-title-duration">
                            <div className="duration-value">
                              {formatDecimalHoursToHoursMinutes(title.duration_formatted)}
                            </div>
                            <div className="last-seen-time">
                              Last: {new Date(title.last_seen).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Top Activities - Accordion */}
          <div className="chart-container">
            <div 
              className={`accordion-header ${isTopActivitiesOpen ? 'open' : ''}`}
              onClick={() => setIsTopActivitiesOpen(!isTopActivitiesOpen)}
            >
              <h3>Top Activities</h3>
              <div className="accordion-icon">
                {isTopActivitiesOpen ? 
                  <ChevronUp size={20} color="#667eea" /> : 
                  <ChevronDown size={20} color="#667eea" />
                }
              </div>
            </div>
            
            {isTopActivitiesOpen && (
              <div className="accordion-content">
                <ActivityTable data={activityData.filter(item => isWorkRelatedActivity(item))} formatTime={formatTime} showUrls={true} showDetails={false} />
              </div>
            )}
          </div>
        </>
      )}

      {/* Productivity Tab Content */}
      {!loading && activeTab === 'productivity' && developer && (
        <ProductivityMetrics 
          developerId={developer.developer_id || developer.id} 
          dateRange={{ start: startDate.toISOString(), end: endDate.toISOString() }}
        />
      )}

      {/* Projects Tab Content */}
      {!loading && activeTab === 'projects' && developer && (
        <ProjectBreakdown 
          developerId={developer.developer_id || developer.id} 
          dateRange={{ start: startDate.toISOString(), end: endDate.toISOString() }}
        />
      )}

      {!loading && activityData.length === 0 && (
        <div className="chart-container">
          <div className="no-data-container">
            <Activity size={64} color="#ccc" className="no-data-icon" />
            <h3>No Activity Data</h3>
            <p className="no-data-text">
              No activity data found for the selected date range.
            </p>
            <button
              onClick={() => fetchActivityData(true)}
              className="btn btn-primary"
            >
              <RefreshCw size={16} />
              Sync from ActivityWatch
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DeveloperDashboard;
