import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Clock, LogOut, User, FolderOpen, RefreshCw } from 'lucide-react';

function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isDashboard = location.pathname === '/dashboard';
  const isProjects = location.pathname === '/project-time';

  const navStyle = {
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    padding: '16px 0',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
    position: 'sticky',
    top: 0,
    zIndex: 1000
  };

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const logoStyle = {
    display: 'flex',
    alignItems: 'center',
    textDecoration: 'none',
    color: '#333',
    fontSize: '24px',
    fontWeight: 'bold'
  };

  const navLinksStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  };

  const getNavLinkStyle = (isActive) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    borderRadius: '6px',
    textDecoration: 'none',
    color: isActive ? '#667eea' : '#4b5563',
    backgroundColor: isActive ? '#eef2ff' : 'transparent',
    fontSize: '14px',
    fontWeight: isActive ? '600' : '500',
    transition: 'all 0.2s ease'
  });

  const userInfoStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  };

  const userNameStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#666',
    fontSize: '16px'
  };

  const buttonStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'none',
    border: 'none',
    color: '#666',
    cursor: 'pointer',
    padding: '8px 16px',
    borderRadius: '6px',
    transition: 'background-color 0.2s ease'
  };

  return (
    <nav style={navStyle}>
      <div style={containerStyle}>
        <Link to="/dashboard" style={logoStyle} onClick={() => window.dispatchEvent(new CustomEvent('navigateHome'))}>
          <Clock size={28} color="#667eea" style={{ marginRight: '12px' }} />
          Resources Timesheet
        </Link>

        {user && (
          <div style={navLinksStyle}>
            <Link
              to="/project-time"
              style={getNavLinkStyle(isProjects)}
              onMouseEnter={(e) => { if (!isProjects) e.currentTarget.style.backgroundColor = '#f3f4f6'; }}
              onMouseLeave={(e) => { if (!isProjects) e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <FolderOpen size={16} />
              Projects
            </Link>
          </div>
        )}

        {user && (
          <div style={userInfoStyle}>
            <div style={userNameStyle}>
              <User size={16} />
              {user.username}
            </div>
            {isDashboard && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent('refreshDeveloperList'))}
                style={buttonStyle}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <RefreshCw size={16} />
                Refresh List
              </button>
            )}
            <button
              onClick={logout}
              style={buttonStyle}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
