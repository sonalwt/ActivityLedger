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
    <div style={{
      background: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      marginBottom: '30px'
    }}>
      <h3 style={{ marginBottom: '20px', color: '#333' }}>📅 Daily Hours Report</h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f0f9ff', borderRadius: '8px' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#0ea5e9' }}>
            {totalHours.toFixed(1)}h
          </div>
          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Total Hours</div>
        </div>
        <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#ecfdf5', borderRadius: '8px' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>
            {avgHours.toFixed(1)}h
          </div>
          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Average/Day</div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
        {dailyHours.map(day => (
          <div key={day.date} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px',
            borderRadius: '6px',
            backgroundColor: '#f8fafc',
            borderLeft: `4px solid ${day.color}`
          }}>
            <div>
              <span style={{ fontWeight: '500' }}>{format(new Date(day.date), 'MMM d, yyyy')}</span>
              <span style={{ fontSize: '0.875rem', color: '#64748b', marginLeft: '8px' }}>
                ({day.activities} activities)
              </span>
            </div>
            <div style={{ fontWeight: 'bold', color: day.color }}>
              {day.total_hours.toFixed(1)}h
            </div>
          </div>
        ))}
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
    <div style={{
      background: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      marginBottom: '30px'
    }}>
      <h3 style={{ marginBottom: '20px', color: '#333' }}>📊 Productivity Analysis</h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        <div style={{ textAlign: 'center', padding: '20px', backgroundColor: '#f0f9ff', borderRadius: '8px' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#0ea5e9' }}>
            {productivity.productivityScore}%
          </div>
          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Productivity Score</div>
        </div>
        <div style={{ textAlign: 'center', padding: '20px', backgroundColor: '#ecfdf5', borderRadius: '8px' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#10b981' }}>
            {productivity.workTime.toFixed(1)}h
          </div>
          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Work Time</div>
        </div>
        <div style={{ textAlign: 'center', padding: '20px', backgroundColor: '#fefce8', borderRadius: '8px' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#eab308' }}>
            {productivity.totalTime.toFixed(1)}h
          </div>
          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Total Time</div>
        </div>
      </div>

      <div>
        <h4 style={{ marginBottom: '12px', color: '#374151' }}>Category Breakdown</h4>
        {productivity.categories.map(category => (
          <div key={category.name} style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>{category.name}</span>
              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                {category.time.toFixed(1)}h ({category.percentage.toFixed(1)}%)
              </span>
            </div>
            <div style={{ 
              height: '6px', 
              backgroundColor: '#e5e7eb', 
              borderRadius: '3px', 
              overflow: 'hidden' 
            }}>
              <div style={{
                width: `${category.percentage}%`,
                height: '100%',
                backgroundColor: category.name === 'Development' ? '#10b981' :
                               category.name === 'Web Browsing' ? '#3b82f6' : '#f59e0b',
                borderRadius: '3px'
              }} />
            </div>
          </div>
        ))}
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

  const API_BASE = 'http://localhost:8000';

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
        response = await axios.get(endpoint, {
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
      const response = await axios.get('/top-window-titles', {
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

  const dashboardStyle = {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto'
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '30px',
    flexWrap: 'wrap',
    gap: '20px'
  };

  const titleStyle = {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  };

  const controlsStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap'
  };

  const datePickerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    background: 'white',
    padding: '12px 16px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
  };

  const statsStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginBottom: '30px'
  };

  const statCardStyle = {
    background: 'white',
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    textAlign: 'center'
  };

  const contentStyle = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '30px',
    marginBottom: '30px'
  };

  const chartContainerStyle = {
    background: 'white',
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
  };

  const tabStyle = {
    display: 'flex',
    gap: '4px',
    marginBottom: '30px',
    borderBottom: '2px solid #e5e7eb',
    paddingBottom: '0'
  };

  const tabButtonStyle = (isActive) => ({
    padding: '12px 24px',
    background: isActive ? 'white' : 'transparent',
    border: 'none',
    borderBottom: isActive ? '2px solid #667eea' : '2px solid transparent',
    marginBottom: '-2px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: isActive ? '600' : '400',
    color: isActive ? '#667eea' : '#6b7280',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.2s ease'
  });

  return (
    <div style={dashboardStyle}>
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {onBack && (
            <button
              onClick={onBack}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                backgroundColor: '#f3f4f6',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                color: '#374151'
              }}
            >
              <ArrowLeft size={16} />
              Back
            </button>
          )}
          <h1 style={titleStyle}>
            <Activity size={36} color="#667eea" />
            {developer ? `${developer.name}'s Dashboard` : 'Activity Dashboard'}
          </h1>
        </div>
        
        <div style={controlsStyle}>
          <div style={datePickerStyle}>
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
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            Sync from ActivityWatch
          </button>
        </div>
      </div>

      <div style={statsStyle}>
        <div style={statCardStyle}>
          <Clock size={32} color="#667eea" style={{ marginBottom: '12px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>Total Time</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea', margin: 0 }}>
            {formatTime(totalTime)}
          </p>
        </div>
        
        <div style={statCardStyle}>
          <Activity size={32} color="#28a745" style={{ marginBottom: '12px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>Active Projects</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745', margin: 0 }}>
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
          <p style={{ fontSize: '12px', color: '#666', margin: '4px 0 0 0' }}>
            in selected period
          </p>
        </div>
        
        <div style={statCardStyle}>
          <RefreshCw size={32} color="#ffc107" style={{ marginBottom: '12px' }} />
          <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>Last Updated</h3>
          <p style={{ fontSize: '14px', color: '#666', margin: 0 }}>
            {lastUpdated ? format(lastUpdated, 'MMM d, yyyy HH:mm') : 'Never'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p style={{ marginTop: '16px', color: '#666' }}>Loading activity data...</p>
        </div>
      )}

      {/* Tab Navigation */}
      {developer && (
        <div style={tabStyle}>
          <button
            style={tabButtonStyle(activeTab === 'activity')}
            onClick={() => setActiveTab('activity')}
          >
            <Activity size={16} />
            Activity Data
          </button>
          <button
            style={tabButtonStyle(activeTab === 'productivity')}
            onClick={() => setActiveTab('productivity')}
          >
            <BarChart2 size={16} />
            Productivity
          </button>
          <button
            style={tabButtonStyle(activeTab === 'projects')}
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
          {/* Live Daily Hours Report */}
          <LiveDailyHoursReport activityData={activityData} startDate={startDate} endDate={endDate} />
          
          {/* Live Productivity Analysis */}
          <LiveProductivityDashboard activityData={activityData} />
          
          <div style={contentStyle}>
            <div style={chartContainerStyle}>
              <h3 style={{ marginBottom: '20px', color: '#333' }}>Activity Distribution</h3>
              <ActivityChart data={activityData} />
            </div>
            
            <div style={chartContainerStyle}>
              <h3 style={{ marginBottom: '20px', color: '#333' }}>
                Project Details
                <span style={{ fontSize: '14px', color: '#666', fontWeight: 'normal', marginLeft: '8px' }}>
                  ({format(startDate, 'MMM d')} - {format(endDate, 'MMM d, yyyy')})
                </span>
              </h3>
              
              {/* Only show top window titles for original dashboard (no developer prop) */}
              {!developer && topWindowTitles.length > 0 && (
                <div style={{ marginBottom: '30px' }}>
                  <h4 style={{ 
                    fontSize: '16px', 
                    color: '#333', 
                    marginBottom: '15px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    🏆 Top Window Titles from ActivityWatch
                    <span style={{ 
                      fontSize: '12px', 
                      color: '#666', 
                      fontWeight: 'normal',
                      background: '#f3f4f6',
                      padding: '2px 8px',
                      borderRadius: '12px'
                    }}>
                      Live Data
                    </span>
                  </h4>
                  
                  <div style={{
                    display: 'grid',
                    gap: '12px',
                    maxHeight: '400px',
                    overflowY: 'auto',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    padding: '16px'
                  }}>
                    {topWindowTitles.map((title, index) => (
                      <div key={index} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '12px',
                        background: '#f9fafb',
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <span style={{
                              fontSize: '14px',
                              fontWeight: '600',
                              color: '#1f2937',
                              background: title.project_info?.project_type === 'Development' ? '#dcfce7' :
                                         title.project_info?.project_type === 'Web Development' ? '#dbeafe' :
                                         title.project_info?.project_type === 'Server Management' ? '#fef3c7' :
                                         title.project_info?.project_type === 'Database' ? '#f3e8ff' :
                                         '#f3f4f6',
                              color: title.project_info?.project_type === 'Development' ? '#166534' :
                                     title.project_info?.project_type === 'Web Development' ? '#1e40af' :
                                     title.project_info?.project_type === 'Server Management' ? '#92400e' :
                                     title.project_info?.project_type === 'Database' ? '#7c3aed' :
                                     '#374151',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '11px'
                            }}>
                              {title.project_info?.project_type || 'Work'}
                            </span>
                            <span style={{ fontSize: '14px', fontWeight: '500', color: '#1f2937' }}>
                              {title.project_info?.project_name || title.application_name}
                            </span>
                          </div>
                          
                          <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '2px' }}>
                            📄 {title.project_info?.file_name || title.window_title}
                          </div>
                          
                          <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                            💻 {title.application_name} • {title.activity_count} activities
                          </div>
                        </div>
                        
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ 
                            fontSize: '16px', 
                            fontWeight: '600', 
                            color: '#059669',
                            marginBottom: '2px'
                          }}>
                            {formatDecimalHoursToHoursMinutes(title.duration_formatted)}
                          </div>
                          <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                            Last: {new Date(title.last_seen).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Top Activities - Accordion */}
          <div style={chartContainerStyle}>
            <div 
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                padding: '16px 0',
                borderBottom: isTopActivitiesOpen ? '1px solid #e5e7eb' : 'none',
                marginBottom: isTopActivitiesOpen ? '20px' : '0'
              }}
              onClick={() => setIsTopActivitiesOpen(!isTopActivitiesOpen)}
            >
              <h3 style={{ margin: 0, color: '#333' }}>Top Activities</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {isTopActivitiesOpen ? 
                  <ChevronUp size={20} color="#667eea" /> : 
                  <ChevronDown size={20} color="#667eea" />
                }
              </div>
            </div>
            
            {isTopActivitiesOpen && (
              <div style={{
                animation: 'fadeIn 0.3s ease-in-out'
              }}>
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
        <div style={chartContainerStyle}>
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#666' }}>
            <Activity size={64} color="#ccc" style={{ marginBottom: '20px' }} />
            <h3 style={{ marginBottom: '12px' }}>No Activity Data</h3>
            <p style={{ marginBottom: '20px' }}>
              No activity data found for the selected date range.
            </p>
            <button
              onClick={() => fetchActivityData(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
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
