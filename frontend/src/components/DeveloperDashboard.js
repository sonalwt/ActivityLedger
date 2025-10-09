// DeveloperDashboard.js - Updated with Pie Chart, Top 5 Activities, and Productivity
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format, startOfDay, endOfDay } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Calendar, RefreshCw, Activity, Clock, ArrowLeft } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './DeveloperDashboard.css';

// Existing Components
import LiveDailyHoursReport from './LiveDailyHoursReport';
import LiveProductivityDashboard from './LiveProductivityDashboard';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#6b7280'];

function DeveloperDashboard({ developer, onBack }) {
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(startOfDay(new Date()));
  const [endDate, setEndDate] = useState(endOfDay(new Date()));
  const [totalTime, setTotalTime] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);
  const [activeTab, setActiveTab] = useState('activity'); // tabs: activity | top5

  const API_BASE = process.env.REACT_APP_API_URL || '';

  const fetchActivityData = async () => {
    setLoading(true);
    try {
      if (!developer) return;

      const developerId = developer.developer_id || developer.id;

      const response = await axios.get(`${API_BASE}/activity-data/${developerId}`, {
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

  // Calculate Category Breakdown Pie Chart
  const pieData = ['productivity', 'browser', 'server', 'non-work', 'uncategorized'].map(cat => {
    const total = activityData
      .filter(a => a.category === cat)
      .reduce((sum, a) => sum + (a.duration || 0), 0);
    return { name: cat, value: total };
  }).filter(d => d.value > 0);

  // Calculate Top 5 Activities
  const top5Activities = [...activityData]
    .sort((a, b) => (b.duration || 0) - (a.duration || 0))
    .slice(0, 5);

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

      <div className="tabs">
        <button className={activeTab === 'activity' ? 'active' : ''} onClick={() => setActiveTab('activity')}>Category Breakdown</button>
        <button className={activeTab === 'top5' ? 'active' : ''} onClick={() => setActiveTab('top5')}>Top 5 Activities</button>
      </div>

      {!loading && activeTab === 'activity' && (
        <div className="category-tab">
          <h3>Category Breakdown</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}>
                  {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={value => formatTime(value)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="activity-list">
            {['productivity', 'browser', 'server', 'non-work', 'uncategorized'].map(cat => {
              const acts = activityData.filter(a => a.category === cat);
              if (acts.length === 0) return null;
              return (
                <div key={cat} className="category-section">
                  <h4>{cat.charAt(0).toUpperCase() + cat.slice(1)}</h4>
                  {acts.map((act, idx) => (
                    <div key={idx} className="activity-item">
                      <span>{format(new Date(act.timestamp), 'MMM d, yyyy HH:mm')}</span> - 
                      <span>{act.project_name || 'General Work'}</span> - 
                      <span>{act.detailed_activity}</span> - 
                      <span>{formatTime(act.duration)}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && activeTab === 'top5' && (
        <div className="top5-tab">
          <h3>Top 5 Time-Consuming Activities</h3>
          {top5Activities.map((act, idx) => (
            <div key={idx} className="top-activity-item">
              <strong>{idx+1}. {act.detailed_activity}</strong>
              <div>Project: {act.project_name || 'General Work'}</div>
              <div>Category: {act.category}</div>
              <div>Duration: {formatTime(act.duration)}</div>
              <div>Timestamp: {format(new Date(act.timestamp), 'MMM d, yyyy HH:mm')}</div>
            </div>
          ))}
        </div>
      )}

      {!loading && (
        <>
          <LiveDailyHoursReport activityData={activityData} />
          <LiveProductivityDashboard activityData={activityData} />
        </>
      )}

      {loading && <div className="loading-spinner-container"><div className="spinner loading-spinner"></div><p className="loading-text">Loading activity data...</p></div>}
    </div>
  );
}

export default DeveloperDashboard;
