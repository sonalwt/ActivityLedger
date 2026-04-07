import React, { useState, useEffect } from 'react';
import { Users, TrendingUp, Clock, Activity } from 'lucide-react';
import './TeamProductivitySummary.css';

const TeamProductivitySummary = ({ onDataLoaded, dateRange, onDateRangeChange }) => {
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [localDateRange, setLocalDateRange] = useState('this_week');

  const API_BASE = process.env.REACT_APP_API_URL || '';

  // Use props if provided, otherwise use local state
  const currentDateRange = dateRange !== undefined ? dateRange : localDateRange;
  const handleDateRangeChange = (value) => {
    if (onDateRangeChange) {
      onDateRangeChange(value);
    } else {
      setLocalDateRange(value);
    }
  };

  useEffect(() => {
    fetchSummaryData();
  }, [currentDateRange]);

  const fetchSummaryData = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();

      // Set date range based on selection
      const now = new Date();
      let startDate = new Date();
      let endDate = new Date();

      // Week starts on Monday (1=Mon, 0=Sun)
      const getMonday = (d) => {
        const date = new Date(d);
        const day = date.getDay();
        const diff = day === 0 ? 6 : day - 1; // Sun=6, Mon=0, Tue=1...
        date.setDate(date.getDate() - diff);
        date.setHours(0, 0, 0, 0);
        return date;
      };

      switch (currentDateRange) {
        case 'this_week':
          startDate = getMonday(now);
          endDate.setHours(23, 59, 59, 999);
          break;
        case 'last_week': {
          const lastMon = getMonday(now);
          lastMon.setDate(lastMon.getDate() - 7);
          startDate = lastMon;
          endDate = new Date(lastMon);
          endDate.setDate(endDate.getDate() + 6);
          endDate.setHours(23, 59, 59, 999);
          break;
        }
        case 'this_month':
          startDate = new Date(now.getFullYear(), now.getMonth(), 1);
          endDate.setHours(23, 59, 59, 999);
          break;
        case 'last_month':
          startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
          endDate = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59, 999);
          break;
        default:
          startDate = getMonday(now);
          endDate.setHours(23, 59, 59, 999);
      }

      params.append('start_date', startDate.toISOString());
      params.append('end_date', endDate.toISOString());

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

      // Pass developer data to parent if callback provided
      if (onDataLoaded && data.developers) {
        onDataLoaded(data.developers);
      }
    } catch (error) {
      setError(error.message);
      console.error('Error fetching team summary:', error);
      // Notify parent even on error so it can stop showing the loader
      if (onDataLoaded) {
        onDataLoaded([]);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return null; // Full-page loader is shown by Dashboard parent
  }

  if (error || !summaryData) {
    return null;
  }

  function formatDurationFromHours(decimalHours) {
  if (!decimalHours || isNaN(decimalHours)) return "0h 0m 0s";

  const totalSeconds = Math.floor(decimalHours * 3600);

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return `${hours}h ${minutes}m ${seconds}s`;
}


  const { team_summary } = summaryData;

  return (
    <div className="team-productivity-card">
      <div className="card-header-custom">
        <h2 className="card-title">
          <TrendingUp className="icon-header" />
          Team Productivity Overview
        </h2>
        <select
          value={currentDateRange}
          onChange={(e) => handleDateRangeChange(e.target.value)}
          className="form-select form-select-sm date-range-select"
        >
          <option value="this_week">Current Week</option>
          <option value="last_week">Last Week</option>
          <option value="this_month">Current Month</option>
          <option value="last_month">Last Month</option>
        </select>
      </div>

      <div className="row">
        <div className="col-lg-4 col-md-6 mb-3">
          <div className="stat-card stat-card-blue">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Active Resources</div>
                <div className="stat-value">
                  {team_summary.active_developers}/{team_summary.total_developers}
                </div>
              </div>
              <Users className="stat-icon" />
            </div>
          </div>
        </div>

        <div className="col-lg-4 col-md-6 mb-3">
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

        <div className="col-lg-4 col-md-6 mb-3">
          <div className="stat-card stat-card-purple">
            <div className="stat-content">
              <div className="stat-details">
                <div className="stat-label">Productive Hours</div>
                <div className="stat-value">
                    {formatDurationFromHours(team_summary.team_productive_hours)}
                </div>
              </div>
              <Clock className="stat-icon" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeamProductivitySummary;
