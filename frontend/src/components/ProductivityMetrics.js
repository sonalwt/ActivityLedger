import React, { useState, useEffect } from 'react';
import { BarChart, Clock, TrendingUp, Calendar, Activity } from 'lucide-react';

const ProductivityMetrics = ({ developerId, dateRange }) => {
  const [productivityData, setProductivityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const API_BASE = process.env.REACT_APP_API_URL || '';

  useEffect(() => {
    fetchProductivityData();
  }, [developerId, dateRange]);

  const fetchProductivityData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (dateRange?.start) params.append('start_date', dateRange.start);
      if (dateRange?.end) params.append('end_date', dateRange.end);
      
      const response = await fetch(
        `${API_BASE}/api/developer/${developerId}/productivity-hours?${params}`, 
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
      setProductivityData(data);
    } catch (error) {
      setError(error.message);
      console.error('Error fetching productivity data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-200 rounded"></div>
            <div className="h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600">Error loading productivity data: {error}</div>
      </div>
    );
  }

  if (!productivityData) {
    return null;
  }

  const { overall_stats, daily_productivity, top_applications } = productivityData;

  return (
    <div className="space-y-6">
      {/* Overall Statistics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          Productivity Overview
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Total Work Hours</div>
            <div className="text-2xl font-bold text-blue-600">
              {overall_stats.total_work_hours}h
            </div>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Productive Hours</div>
            <div className="text-2xl font-bold text-green-600">
              {overall_stats.total_productive_hours}h
            </div>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Productivity Rate</div>
            <div className="text-2xl font-bold text-purple-600">
              {overall_stats.productivity_percentage}%
            </div>
          </div>
          
          <div className="bg-orange-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Avg Daily Hours</div>
            <div className="text-2xl font-bold text-orange-600">
              {overall_stats.average_daily_hours}h
            </div>
          </div>
        </div>
      </div>

      {/* Daily Productivity Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-blue-600" />
          Daily Productivity
        </h3>
        
        <div className="space-y-3">
          {daily_productivity.slice(0, 7).map((day, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className="w-24 text-sm text-gray-600">
                {new Date(day.date).toLocaleDateString('en-US', { 
                  weekday: 'short', 
                  month: 'short', 
                  day: 'numeric' 
                })}
              </div>
              
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className="text-sm font-medium">{day.total_hours}h total</div>
                  <div className="text-sm text-gray-500">
                    ({day.productive_hours}h productive)
                  </div>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${day.productivity_percentage}%` }}
                  ></div>
                </div>
              </div>
              
              <div className="text-sm font-medium text-gray-700 w-12 text-right">
                {day.productivity_percentage}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Applications */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          Top Applications
        </h3>
        
        <div className="space-y-2">
          {top_applications.slice(0, 10).map((app, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className={`w-2 h-2 rounded-full ${
                app.is_productive ? 'bg-green-500' : 'bg-gray-400'
              }`}></div>
              
              <div className="flex-1 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{app.application}</span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {app.category}
                  </span>
                </div>
                
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">{app.hours}h</span>
                  <span className="text-xs text-gray-500">{app.usage_count} uses</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProductivityMetrics;
