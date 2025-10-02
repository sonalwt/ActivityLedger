// Multi-Developer Dashboard Wrapper - shows list in production, direct dashboard locally
import React, { useState, useEffect } from 'react';
import { Users, User, Eye, Activity, Monitor } from 'lucide-react';
import DeveloperDashboard from './DeveloperDashboard'; // Your original dashboard renamed
import TeamProductivitySummary from './TeamProductivitySummary';
import './Dashboard.css';

const Dashboard = () => {
  const [developers, setDevelopers] = useState([]);
  const [selectedDeveloper, setSelectedDeveloper] = useState(null);
  const [environment, setEnvironment] = useState('local');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Use environment variable or relative path (proxy handles routing)
  const API_BASE = process.env.REACT_APP_API_URL || ''; // Use empty string for relative URLs via proxy

  useEffect(() => {
    loadDevelopers();
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

  // Local mode - show dashboard directly
  if (environment === 'local') {
    if (selectedDeveloper) {
      return <DeveloperDashboard developer={selectedDeveloper} onBack={null} />;
    }
    
    if (loading) {
      return (
        <div className="local-mode-loading">
          <div className="local-mode-loading-icon">⏳</div>
          <p>Loading your dashboard...</p>
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
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">
            <Users size={36} color="#2563eb" />
            All Developers Dashboard
          </h1>
          <div className="dashboard-badge">
            Production Mode - {developers.length} Developer{developers.length !== 1 ? 's' : ''}
          </div>
        </div>
        
        <button onClick={loadDevelopers} disabled={loading} className="refresh-button">
          {loading ? 'Loading...' : 'Refresh List'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Team Productivity Summary - Only in Production Mode */}
      {environment === 'production' && !loading && (
        <TeamProductivitySummary />
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-container">
          <div className="loading-icon">🔍</div>
          <h3>Loading Developers...</h3>
          <p style={{ color: '#6b7280' }}>Discovering all developers on the network...</p>
        </div>
      )}

      {/* Developers Grid */}
      {!loading && developers.length > 0 && (
        <div className="developers-grid">
          {developers.map((developer) => (
            <div 
              key={developer.id} 
              className={`developer-card ${developer.status || 'unknown'}`}
            >
              {/* Developer Header */}
              <div className="developer-header">
                <div className="developer-info">
                  <div className={`developer-status-icon ${developer.status || 'unknown'}`}>
                    {developer.status === 'online' ? '🟢' : 
                     developer.status === 'offline' ? '🔴' : '⚪'}
                  </div>
                  <div>
                    <h3 className="developer-name">
                      {developer.name}
                    </h3>
                    <p className="developer-hostname">
                      {developer.hostname}
                    </p>
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
                    {developer.activity_count || 0}
                  </div>
                  <div className="stat-label">Activities</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value source">
                    {developer.source || 'Unknown'}
                  </div>
                  <div className="stat-label">Source</div>
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
      {!loading && developers.length === 0 && (
        <div className="no-developers">
          <div className="no-developers-icon">👥</div>
          <h3 className="no-developers-title">No Developers Found</h3>
          <p className="no-developers-text">
            No developers were discovered on the network or in the database.
          </p>
          <button onClick={loadDevelopers} className="discover-button">
            Discover Developers
          </button>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
