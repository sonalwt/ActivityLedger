// CategoryBreakdown.js - Display activities categorized by type
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Monitor, Globe, Server, Activity, AlertCircle } from 'lucide-react';
import './CategoryBreakdown.css';

const CategoryBreakdown = ({ developerId, dateRange }) => {
  const [categoryData, setCategoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const API_BASE = process.env.REACT_APP_API_URL || '';

  // Define colors for each category
  const CATEGORY_COLORS = {
    productive: '#10B981',  // Green
    browser: '#3B82F6',     // Blue
    server: '#8B5CF6',      // Purple
    uncategorized: '#6B7280', // Gray
    'non-work': '#EF4444'   // Red
  };

  const CATEGORY_ICONS = {
    productive: <Monitor size={20} />,
    browser: <Globe size={20} />,
    server: <Server size={20} />,
    uncategorized: <AlertCircle size={20} />,
    'non-work': <Activity size={20} />
  };

  useEffect(() => {
    fetchCategoryData();
  }, [developerId, dateRange]);

  const fetchCategoryData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${API_BASE}/api/activity-categories/${developerId}`, {
        params: {
          start_date: dateRange.start,
          end_date: dateRange.end
        }
      });

      setCategoryData(response.data);
    } catch (err) {
      console.error('Error fetching category data:', err);
      setError('Failed to fetch categorized activities');
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (hours) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)}m`;
    }
    return `${hours.toFixed(1)}h`;
  };

  if (loading) {
    return (
      <div className="category-breakdown-loading">
        <div className="spinner"></div>
        <p>Analyzing activities...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="category-breakdown-error">
        <AlertCircle size={48} color="#EF4444" />
        <p>{error}</p>
        <button onClick={fetchCategoryData} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  if (!categoryData) {
    return null;
  }

  const { statistics, top_activities_by_category, productivity_score, total_duration_hours } = categoryData;

  // Prepare data for pie chart
  const pieData = Object.entries(statistics)
    .filter(([category, stats]) => stats.duration_hours > 0)
    .map(([category, stats]) => ({
      name: category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' '),
      value: stats.duration_hours,
      percentage: stats.percentage,
      count: stats.count
    }));

  // Prepare data for bar chart
  const barData = Object.entries(statistics).map(([category, stats]) => ({
    category: category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' '),
    hours: stats.duration_hours,
    activities: stats.count
  }));

  return (
    <div className="category-breakdown-container">
      <div className="category-header">
        <h2>Activity Categories</h2>
        <div className="productivity-score">
          <span className="score-label">Productivity Score</span>
          <span className={`score-value ${productivity_score >= 80 ? 'high' : productivity_score >= 60 ? 'medium' : 'low'}`}>
            {productivity_score}%
          </span>
        </div>
      </div>

      <div className="category-summary">
        <div className="summary-item">
          <span className="summary-label">Total Time</span>
          <span className="summary-value">{formatDuration(total_duration_hours)}</span>
        </div>
        {Object.entries(statistics).map(([category, stats]) => (
          <div key={category} className="summary-item">
            <div className="category-label">
              {CATEGORY_ICONS[category]}
              <span>{category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' ')}</span>
            </div>
            <span className="summary-value" style={{ color: CATEGORY_COLORS[category] }}>
              {formatDuration(stats.duration_hours)} ({stats.percentage.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>

      <div className="charts-grid">
        <div className="chart-container">
          <h3>Time Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={CATEGORY_COLORS[entry.name.toLowerCase().replace(' ', '-')]} 
                    onClick={() => setSelectedCategory(entry.name.toLowerCase().replace(' ', '-'))}
                    style={{ cursor: 'pointer' }}
                  />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatDuration(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Activity Count by Category</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="activities" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="top-activities-section">
        <h3>Top Activities by Category</h3>
        <div className="category-tabs">
          {Object.keys(top_activities_by_category).map((category) => (
            <button
              key={category}
              className={`category-tab ${selectedCategory === category ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category)}
              style={{ 
                borderColor: selectedCategory === category ? CATEGORY_COLORS[category] : 'transparent',
                color: selectedCategory === category ? CATEGORY_COLORS[category] : '#6B7280'
              }}
            >
              {CATEGORY_ICONS[category]}
              {category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' ')}
            </button>
          ))}
        </div>

        {selectedCategory && top_activities_by_category[selectedCategory] && (
          <div className="activities-list">
            {top_activities_by_category[selectedCategory].length === 0 ? (
              <p className="no-activities">No activities in this category</p>
            ) : (
              top_activities_by_category[selectedCategory].map((activity, index) => (
                <div key={index} className="activity-item">
                  <div className="activity-info">
                    <div className="activity-title">{activity.window_title || 'Untitled'}</div>
                    <div className="activity-details">
                      <span className="app-name">{activity.application_name}</span>
                      <span className="subcategory">{activity.subcategory}</span>
                    </div>
                  </div>
                  <div className="activity-stats">
                    <span className="duration">{formatDuration(activity.duration_hours)}</span>
                    <div className="confidence-indicator">
                      <div 
                        className="confidence-bar"
                        style={{ 
                          width: `${activity.confidence * 100}%`,
                          backgroundColor: activity.confidence > 0.7 ? '#10B981' : activity.confidence > 0.4 ? '#F59E0B' : '#EF4444'
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryBreakdown;
