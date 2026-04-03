// Multi-Developer Dashboard Wrapper - shows list in production, direct dashboard locally
import React, { useState, useEffect } from 'react';
import { Users, User, Eye, Activity, Monitor } from 'lucide-react';
import DeveloperDashboard from './DeveloperDashboard'; // Your original dashboard renamed
import TeamProductivitySummary from './TeamProductivitySummary';
import './Dashboard.css';

const Dashboard = () => {
  const [developers, setDevelopers] = useState([]);
  const [filteredActivityCounts, setFilteredActivityCounts] = useState({});
  const [developerProductivity, setDeveloperProductivity] = useState({});
  const [selectedDeveloper, setSelectedDeveloper] = useState(null);
  const [environment, setEnvironment] = useState('local');
  const [loading, setLoading] = useState(true);
  const [productivityLoaded, setProductivityLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState('week');
  // Use environment variable or relative path (proxy handles routing)
  const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com'; // Use empty string for relative URLs via proxy

  useEffect(() => {
    loadDevelopers();

    const handleRefreshEvent = () => loadDevelopers();
    const handleNavigateHome = () => setSelectedDeveloper(null);
    window.addEventListener('refreshDeveloperList', handleRefreshEvent);
    window.addEventListener('navigateHome', handleNavigateHome);
    return () => {
      window.removeEventListener('refreshDeveloperList', handleRefreshEvent);
      window.removeEventListener('navigateHome', handleNavigateHome);
    };
  }, []);

  const loadDevelopers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/api/developers-orm`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDevelopers(data.developers || []);
        setEnvironment(data.environment || 'local');
        
        // In local mode, auto-select the developer and show dashboard directly
        if (data.environment === 'local' && data.developers.length > 0) {
          setSelectedDeveloper(data.developers[0]);
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      setError(`Failed to load developers: ${error.message}`);
    }
    setLoading(false);
  };

  const handleViewDeveloper = (developer) => {
    setSelectedDeveloper(developer);
  };

  const handleBackToList = () => {
    setSelectedDeveloper(null);
  };

  // Handle filtered activity data from TeamProductivitySummary
  const handleProductivityDataLoaded = (devData) => {
    const counts = {};
    const productivity = {};
    devData.forEach(dev => {
      counts[dev.developer_id] = dev.activities_count || 0;
      productivity[dev.developer_id] = dev.productivity_percentage || 0;
    });
    setFilteredActivityCounts(counts);
    setDeveloperProductivity(productivity);
    setProductivityLoaded(true);
  };

  // Show full-page loader until both developers AND productivity data are ready
  const isFullyLoaded = !loading && productivityLoaded;

  // Local mode - show dashboard directly
  if (environment === 'local') {
    if (selectedDeveloper) {
      return <DeveloperDashboard developer={selectedDeveloper} onBack={null} />;
    }
    
    if (loading) {
      return (
        <div className="fullpage-loader">
          <div className="dashboard-loading-spinner"></div>
          <h3>Loading your dashboard...</h3>
        </div>
      );
    }
    
    if (error) {
      return (
        <div className="local-mode-error">
          <h3>Error Loading Dashboard</h3>
          <p>{error}</p>
          <button onClick={loadDevelopers} className="retry-button">
            Try Again
          </button>
        </div>
      );
    }
    
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h3>No Developer Data Found</h3>
        <p>Unable to load your dashboard data.</p>
        <button onClick={loadDevelopers}>Retry</button>
      </div>
    );
  }

  if (selectedDeveloper) {
    return <DeveloperDashboard developer={selectedDeveloper} onBack={handleBackToList} />;
  }

  // Production developer list view
  return (
    <div className="dashboard-wrapper">
      {/* Header */}
      

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Team Productivity Summary - fetch in background even while loading */}
      {environment === 'production' && !loading && (
        <TeamProductivitySummary
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          onDataLoaded={handleProductivityDataLoaded}
        />
      )}

      {/* Full-page loader until both developers + productivity are ready */}
      {!isFullyLoaded && (
        <div className="fullpage-loader">
          <div className="dashboard-loading-spinner"></div>
          <h3>Loading Resources...</h3>
          <p>Discovering all resources on the network...</p>
        </div>
      )}

      {/* Developers Grid - only show when fully loaded */}
      {isFullyLoaded && developers.length > 0 && (
        <div className="developers-grid">
          {[...developers]
            .sort((a, b) => {
              const prodA = developerProductivity[a.id] || 0;
              const prodB = developerProductivity[b.id] || 0;
              return prodB - prodA; // Sort by productivity descending
            })
            .map((developer) => (
            <div 
              key={developer.id} 
              className={`developer-card ${developer.status || 'unknown'}`}
            >
              {/* Developer Header */}
              <div className="developer-header">
                <div className="developer-info">
                  <div>
                    <h3 className="developer-name">
                      {developer.name}
                    </h3>
                  </div>
                </div>
                
                <div className={`developer-status-badge ${developer.status || 'unknown'}`}>
                  {developer.status.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {/* Developer Stats */}
              <div className="developer-stats">
                <div className="stat-item">
                  <div className="stat-value">
                    {filteredActivityCounts[developer.id] !== undefined
                      ? filteredActivityCounts[developer.id]
                      : (developer.activity_count || 0)}
                  </div>
                  <div className="stat-label">Activities</div>
                </div>
                <div className="stat-item">
                  <div className={`stat-value productivity ${
                    (developerProductivity[developer.id] || 0) >= 70 ? 'high' :
                    (developerProductivity[developer.id] || 0) >= 40 ? 'medium' : 'low'
                  }`}>
                    {developerProductivity[developer.id] !== undefined
                      ? `${developerProductivity[developer.id].toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <div className="stat-label">Work Activity</div>
                </div>
              </div>

              {/* Developer Info */}
              <div className="developer-details">
                <div className="developer-description">
                  <strong>Description:</strong> {developer.description || 'No description'}
                </div>
                {developer.last_seen && (
                  <div className="developer-last-seen">
                    Last seen: {new Date(developer.last_seen).toLocaleString()}
                  </div>
                )}
              </div>

              {/* View Button */}
              <button
                onClick={() => handleViewDeveloper(developer)}
                className="view-dashboard-button"
              >
                <Eye size={16} />
                View Dashboard
              </button>
            </div>
          ))}
        </div>
      )}

      {/* No Developers State */}
      {isFullyLoaded && developers.length === 0 && (
        <div className="no-developers">
          <div className="no-developers-icon">👥</div>
          <h3 className="no-developers-title">No Resources Found</h3>
          <p className="no-developers-text">
            No resources were discovered on the network or in the database.
          </p>
          <button onClick={loadDevelopers} className="discover-button">
            Discover Resources
          </button>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
