import React, { useState, useEffect } from 'react';
import { Users, TrendingUp, Clock, Activity } from 'lucide-react';
import './TeamProductivitySummary.css';

const TeamProductivitySummary = () => {
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState('today');
  
  const API_BASE = process.env.REACT_APP_API_URL || '';

  useEffect(() => {
    fetchSummaryData();
  }, [dateRange]);

  const fetchSummaryData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      // Set date range based on selection
      const now = new Date();
      let startDate = new Date();
      
      switch (dateRange) {
        case 'today':
          startDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          startDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          startDate.setDate(now.getDate() - 30);
          break;
        default:
          startDate.setHours(0, 0, 0, 0);
      }
      
      params.append('start_date', startDate.toISOString());
      params.append('end_date', now.toISOString());
      
      const response = await fetch(
        `${API_BASE}/api/all-developers/productivity-summary?${params}`, 
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setSummaryData(data);
    } catch (error) {
      setError(error.message);
      console.error('Error fetching team summary:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="team-productivity-card">
        <div className="loading-placeholder">
          <div className="loading-header"></div>
          <div className="row">
            <div className="col-md-3 mb-3">
              <div className="loading-stat"></div>
            </div>
            <div className="col-md-3 mb-3">
              <div className="loading-stat"></div>
            </div>
            <div className="col-md-3 mb-3">
              <div className="loading-stat"></div>
            </div>
            <div className="col-md-3 mb-3">
              <div className="loading-stat"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !summaryData) {
    return null;
  }

  const { team_summary, developers } = summaryData;

  return (
    <div className="team-productivity-card">
      <div className="card-header-custom">
        <h2 className="card-title">
          <TrendingUp className="icon-header" />
          Team Productivity Overview
        </h2>
        
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="form-select form-select-sm date-range-select"
        >
          <option value="today">Today</option>
          <option value="week">Last 7 Days</option>
          <option value="month">Last 30 Days</option>
        </select>
      </div>
      
      <div className="row mb-4">
        <div className="col-lg-3 col-md-6 mb-3">
          <div className="stat-card stat-card-blue">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Active Developers</div>
                <div className="stat-value">
                  {team_summary.active_developers}/{team_summary.total_developers}
                </div>
              </div>
              <Users className="stat-icon" />
            </div>
          </div>
        </div>
        
        <div className="col-lg-3 col-md-6 mb-3">
          <div className="stat-card stat-card-green">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Team Productivity</div>
                <div className="stat-value">
                  {team_summary.team_productivity_percentage}%
                </div>
              </div>
              <TrendingUp className="stat-icon" />
            </div>
          </div>
        </div>
        
        <div className="col-lg-3 col-md-6 mb-3">
          <div className="stat-card stat-card-purple">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Total Hours</div>
                <div className="stat-value">
                  {team_summary.team_total_hours}h
                </div>
              </div>
              <Clock className="stat-icon" />
            </div>
          </div>
        </div>
        
        <div className="col-lg-3 col-md-6 mb-3">
          <div className="stat-card stat-card-orange">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Avg Hours/Dev</div>
                <div className="stat-value">
                  {team_summary.average_hours_per_developer}h
                </div>
              </div>
              <Activity className="stat-icon" />
            </div>
          </div>
        </div>
      </div>

      {/* Developer Activity */}
      <div className="developer-activity">
        <h3 className="section-title">Developer Activity</h3>
        <div className="developer-list">
          {developers.slice(0, 5).map((dev, index) => (
            <div key={index} className="developer-item">
              <div className="developer-info">
                <div className={`status-indicator status-${dev.status}`}></div>
                <span className="developer-name">{dev.name}</span>
              </div>
              
              <div className="developer-stats">
                <span className="hours-worked">{dev.total_hours}h worked</span>
                <span className={`productivity-percentage ${
                  dev.productivity_percentage >= 80 ? 'high-productivity' :
                  dev.productivity_percentage >= 60 ? 'medium-productivity' :
                  'low-productivity'
                }`}>
                  {dev.productivity_percentage}% productive
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TeamProductivitySummary;
