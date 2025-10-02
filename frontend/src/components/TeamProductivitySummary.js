import React, { useState, useEffect } from 'react';
import { Users, TrendingUp, Clock, Activity } from 'lucide-react';

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
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
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
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          Team Productivity Overview
        </h2>
        
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="text-sm border border-gray-300 rounded-md px-3 py-1"
          style={{ minWidth: '120px' }}
        >
          <option value="today">Today</option>
          <option value="week">Last 7 Days</option>
          <option value="month">Last 30 Days</option>
        </select>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600">Active Developers</div>
              <div className="text-2xl font-bold text-blue-600">
                {team_summary.active_developers}/{team_summary.total_developers}
              </div>
            </div>
            <Users className="w-8 h-8 text-blue-400" />
          </div>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600">Team Productivity</div>
              <div className="text-2xl font-bold text-green-600">
                {team_summary.team_productivity_percentage}%
              </div>
            </div>
            <TrendingUp className="w-8 h-8 text-green-400" />
          </div>
        </div>
        
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600">Total Hours</div>
              <div className="text-2xl font-bold text-purple-600">
                {team_summary.team_total_hours}h
              </div>
            </div>
            <Clock className="w-8 h-8 text-purple-400" />
          </div>
        </div>
        
        <div className="bg-orange-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-600">Avg Hours/Dev</div>
              <div className="text-2xl font-bold text-orange-600">
                {team_summary.average_hours_per_developer}h
              </div>
            </div>
            <Activity className="w-8 h-8 text-orange-400" />
          </div>
        </div>
      </div>

      {/* Top Performers */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">Developer Activity</h3>
        <div className="space-y-2">
          {developers.slice(0, 5).map((dev, index) => (
            <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  dev.status === 'active' ? 'bg-green-500' :
                  dev.status === 'idle' ? 'bg-yellow-500' : 'bg-gray-400'
                }`}></div>
                <span className="font-medium text-sm">{dev.name}</span>
              </div>
              
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-600">{dev.total_hours}h worked</span>
                <span className={`font-medium ${
                  dev.productivity_percentage >= 80 ? 'text-green-600' :
                  dev.productivity_percentage >= 60 ? 'text-yellow-600' :
                  'text-red-600'
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
