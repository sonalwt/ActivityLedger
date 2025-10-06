import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FolderOpen, Clock, Activity, TrendingUp, Layers } from 'lucide-react';
import './CategoryBreakdown.css';

const CategoryBreakdown = ({ developerId, dateRange }) => {
  const [categoryData, setCategoryData] = useState({
    summary: {},
    categories: {},
    date_range: dateRange
  });
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null);
  
  const API_BASE = process.env.REACT_APP_API_URL || '';

  const categoryIcons = {
    'productivity': '💻',
    'browser': '🌐',
    'server': '☁️',
    'non-work': '🎮',
    'uncategorized': '❓'
  };

  const categoryColors = {
    'productivity': '#10b981',
    'browser': '#3b82f6',
    'server': '#8b5cf6',
    'non-work': '#ef4444',
    'uncategorized': '#6b7280'
  };

  useEffect(() => {
    fetchCategoryData();
  }, [developerId, dateRange]);

  const fetchCategoryData = async () => {
    if (!developerId) {
      console.error('No developerId provided');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    try {
      console.log('Fetching categories for developer:', developerId);
      const response = await axios.get(
        `${API_BASE}/api/activity-categories/${developerId}`,
        {
          params: {
            start_date: dateRange.start,
            end_date: dateRange.end
          }
        }
      );
      
      console.log('Category data response:', response.data);
      
      if (response.data && response.data.summary) {
        setCategoryData(response.data);
        // Auto-select productivity category if it exists
        if (response.data.categories && response.data.categories.productivity) {
          setSelectedCategory('productivity');
        }
      } else {
        console.error('Invalid response structure:', response.data);
        setCategoryData({
          summary: {},
          categories: {},
          date_range: dateRange
        });
      }
    } catch (error) {
      console.error('Error fetching category data:', error.response || error);
      setCategoryData({
        summary: {},
        categories: {},
        date_range: dateRange
      });
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  if (loading) {
    return (
      <div className="category-loading">
        <div className="spinner"></div>
        <p>Loading category data...</p>
      </div>
    );
  }

  // Check if we have actual data
  const hasData = categoryData && categoryData.summary && Object.keys(categoryData.summary).length > 0;
  
  if (!hasData && !loading) {
    return (
      <div className="category-empty">
        <FolderOpen size={48} />
        <p>No category data available</p>
      </div>
    );
  }

  return (
    <div className="category-breakdown-container">
      {/* Category Overview Cards */}
      <div className="category-overview-grid">
        {categoryData.summary && Object.entries(categoryData.summary).map(([category, data]) => (
          <div 
            key={category}
            className={`category-overview-card ${selectedCategory === category ? 'active' : ''}`}
            onClick={() => setSelectedCategory(category)}
            style={{ borderColor: categoryColors[category] }}
          >
            <div className="category-card-header">
              <span className="category-icon">{categoryIcons[category]}</span>
              <h3>{category.charAt(0).toUpperCase() + category.slice(1).replace('-', ' ')}</h3>
            </div>
            
            <div className="category-card-stats">
              <div className="stat-item">
                <span className="stat-value" style={{ color: categoryColors[category] }}>
                  {data.percentage}%
                </span>
                <span className="stat-label">of total time</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{data.hours}h</span>
                <span className="stat-label">total</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Category Details */}
      {selectedCategory && categoryData.categories && categoryData.categories[selectedCategory] && (
        <div className="category-details">
          <h2 className="category-details-title">
            {categoryIcons[selectedCategory]} {selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1).replace('-', ' ')} Activities
          </h2>

          {/* Top Applications */}
          <div className="top-applications">
            <h3>Top Applications</h3>
            <div className="applications-list">
              {categoryData.categories[selectedCategory].top_applications && categoryData.categories[selectedCategory].top_applications.map((app, index) => (
                <div key={index} className="application-item">
                  <div className="app-info">
                    <span className="app-rank">#{index + 1}</span>
                    <span className="app-name">{app.name || 'Unknown'}</span>
                  </div>
                  <div className="app-stats">
                    <span className="app-duration">{formatDuration(app.duration)}</span>
                    <span className="app-percentage">{app.percentage}%</span>
                  </div>
                  <div className="app-progress">
                    <div 
                      className="app-progress-bar"
                      style={{ 
                        width: `${app.percentage}%`,
                        backgroundColor: categoryColors[selectedCategory]
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activities */}
          <div className="recent-activities">
            <h3>Recent Activities</h3>
            <div className="activities-table">
              <table>
                <thead>
                  <tr>
                    <th>Application</th>
                    <th>Window Title</th>
                    <th>Duration</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {categoryData.categories[selectedCategory].activities && categoryData.categories[selectedCategory].activities.slice(0, 20).map((activity) => (
                    <tr key={activity.id}>
                      <td className="app-cell">
                        <span className="app-name-badge">{activity.application_name}</span>
                      </td>
                      <td className="title-cell" title={activity.window_title}>
                        {activity.window_title}
                      </td>
                      <td className="duration-cell">{formatDuration(activity.duration)}</td>
                      <td className="time-cell">
                        {new Date(activity.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryBreakdown;
