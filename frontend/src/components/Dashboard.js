// Multi-Developer Dashboard Wrapper - shows list in production, direct dashboard locally
import React, { useState, useEffect } from 'react';
import { Users, User, Eye, Activity, Monitor } from 'lucide-react';
import DeveloperDashboard from './DeveloperDashboard'; // Your original dashboard renamed

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
      const response = await fetch(`${API_BASE}/api/all-developers`, 
        {
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
        <div style={{ 
          display: 'flex', justifyContent: 'center', alignItems: 'center', 
          height: '400px', flexDirection: 'column' 
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '16px' }}>⏳</div>
          <p>Loading your dashboard...</p>
        </div>
      );
    }
    
    if (error) {
      return (
        <div style={{ 
          padding: '40px', textAlign: 'center', 
          backgroundColor: '#fef2f2', color: '#b91c1c', 
          borderRadius: '12px', margin: '20px' 
        }}>
          <h3>Error Loading Dashboard</h3>
          <p>{error}</p>
          <button onClick={loadDevelopers} style={{
            padding: '8px 16px', backgroundColor: '#dc2626', color: 'white',
            border: 'none', borderRadius: '6px', cursor: 'pointer', marginTop: '16px'
          }}>
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
    <div style={{ 
      maxWidth: '1200px', margin: '0 auto', padding: '24px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        marginBottom: '32px' 
      }}>
        <div>
          <h1 style={{ 
            fontSize: '2rem', fontWeight: 'bold', color: '#1f2937', 
            margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '12px' 
          }}>
            <Users size={36} color="#2563eb" />
            All Developers Dashboard
          </h1>
          <div style={{ 
            padding: '4px 12px', borderRadius: '20px', fontSize: '0.875rem',
            backgroundColor: '#dbeafe', color: '#1e40af', fontWeight: '500', display: 'inline-block'
          }}>
            Production Mode - {developers.length} Developer{developers.length !== 1 ? 's' : ''}
          </div>
        </div>
        
        <button onClick={loadDevelopers} disabled={loading} style={{
          padding: '8px 16px', fontSize: '0.875rem', color: '#2563eb',
          backgroundColor: 'white', border: '1px solid #dbeafe', borderRadius: '8px',
          cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1
        }}>
          {loading ? 'Loading...' : 'Refresh List'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{ 
          padding: '16px', backgroundColor: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: '8px', color: '#b91c1c', marginBottom: '24px' 
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ 
          textAlign: 'center', padding: '48px', backgroundColor: 'white',
          borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' 
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '16px' }}>🔍</div>
          <h3>Loading Developers...</h3>
          <p style={{ color: '#6b7280' }}>Discovering all developers on the network...</p>
        </div>
      )}

      {/* Developers Grid */}
      {!loading && developers.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
          gap: '24px'
        }}>
          {developers.map((developer) => (
            <div key={developer.id} style={{
              backgroundColor: 'white',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              border: developer.status === 'online' ? '2px solid #10b981' : 
                     developer.status === 'offline' ? '2px solid #ef4444' : '2px solid #6b7280',
              transition: 'transform 0.2s, box-shadow 0.2s'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 15px -3px rgba(0, 0, 0, 0.1)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
            }}
            >
              {/* Developer Header */}
              <div style={{ 
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: '48px', height: '48px', borderRadius: '50%',
                    backgroundColor: developer.status === 'online' ? '#10b981' : 
                                   developer.status === 'offline' ? '#ef4444' : '#6b7280',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                    {developer.status === 'online' ? '🟢' : 
                     developer.status === 'offline' ? '🔴' : '⚪'}
                  </div>
                  <div>
                    <h3 style={{ 
                      fontSize: '1.25rem', fontWeight: '600', color: '#1f2937', 
                      margin: '0 0 4px 0' 
                    }}>
                      {developer.name}
                    </h3>
                    <p style={{ 
                      fontSize: '0.875rem', color: '#6b7280', margin: 0 
                    }}>
                      {developer.hostname}
                    </p>
                  </div>
                </div>
                
                <div style={{
                  padding: '4px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '500',
                  backgroundColor: developer.status === 'online' ? '#d1fae5' : 
                                 developer.status === 'offline' ? '#fee2e2' : '#f3f4f6',
                  color: developer.status === 'online' ? '#065f46' :
                         developer.status === 'offline' ? '#991b1b' : '#374151'
                }}>
                  {developer.status.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              {/* Developer Stats */}
              <div style={{ 
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px',
                marginBottom: '20px', padding: '16px', backgroundColor: '#f9fafb',
                borderRadius: '8px'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#2563eb' }}>
                    {developer.activity_count || 0}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Activities</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1rem', fontWeight: '500', color: '#059669' }}>
                    {developer.source || 'Unknown'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Source</div>
                </div>
              </div>

              {/* Developer Info */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '0.875rem', color: '#4b5563', marginBottom: '8px' }}>
                  <strong>Description:</strong> {developer.description || 'No description'}
                </div>
                {developer.last_seen && (
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                    Last seen: {new Date(developer.last_seen).toLocaleString()}
                  </div>
                )}
              </div>

              {/* View Button */}
              <button
                onClick={() => handleViewDeveloper(developer)}
                style={{
                  width: '100%', padding: '12px 24px', fontSize: '0.875rem', fontWeight: '500',
                  backgroundColor: '#2563eb', color: 'white', border: 'none',
                  borderRadius: '8px', cursor: 'pointer', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', gap: '8px',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => e.target.style.backgroundColor = '#1d4ed8'}
                onMouseOut={(e) => e.target.style.backgroundColor = '#2563eb'}
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
        <div style={{ 
          textAlign: 'center', padding: '48px', backgroundColor: 'white',
          borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' 
        }}>
          <div style={{ fontSize: '4rem', marginBottom: '16px' }}>👥</div>
          <h3>No Developers Found</h3>
          <p style={{ color: '#6b7280', marginBottom: '24px' }}>
            No developers were discovered on the network or in the database.
          </p>
          <button onClick={loadDevelopers} style={{
            padding: '12px 24px', backgroundColor: '#2563eb', color: 'white',
            border: 'none', borderRadius: '8px', cursor: 'pointer'
          }}>
            Discover Developers
          </button>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
