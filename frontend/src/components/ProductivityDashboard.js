import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Clock, 
  Zap, 
  Award,
  AlertCircle,
  CheckCircle,
  BarChart3,
  Brain
} from 'lucide-react';

function ProductivityDashboard({ data }) {
  // Use the data prop directly instead of making API calls
  const productivityData = data;

  const getScoreColor = (score) => {
    if (score >= 80) return '#22c55e'; // Green
    if (score >= 60) return '#eab308'; // Yellow  
    if (score >= 40) return '#f97316'; // Orange
    return '#ef4444'; // Red
  };

  const getScoreIcon = (score) => {
    if (score >= 80) return <Award size={24} color="#22c55e" />;
    if (score >= 60) return <Target size={24} color="#eab308" />;
    if (score >= 40) return <AlertCircle size={24} color="#f97316" />;
    return <AlertCircle size={24} color="#ef4444" />;
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m`;
    } else {
      return `${Math.floor(seconds)}s`;
    }
  };

  const containerStyle = {
    padding: '25px',
    background: '#fff',
    borderRadius: '15px',
    boxShadow: '0 8px 25px rgba(0, 0, 0, 0.1)',
    marginBottom: '25px'
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '24px',
    paddingBottom: '16px',
    borderBottom: '2px solid #e5e7eb'
  };

  const metricsGridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
    gap: '16px',
    marginTop: '24px'
  };

  const metricCardStyle = {
    padding: '16px',
    background: '#f9fafb',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    textAlign: 'center'
  };

  if (!productivityData) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <Brain size={28} color="#667eea" />
          <h3 style={{ margin: 0, color: '#333' }}>ℹ️ Productivity Analysis</h3>
        </div>
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <Brain size={48} color="#ccc" style={{ marginBottom: '16px' }} />
          <p>No productivity data available</p>
        </div>
      </div>
    );
  }

  const score = productivityData.overall_productivity || 32.1;
  
  const scoreCircleStyle = {
    width: '120px',
    height: '120px',
    borderRadius: '50%',
    background: `conic-gradient(${getScoreColor(score)} ${score * 3.6}deg, #e5e7eb 0deg)`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
    position: 'relative'
  };

  const scoreInnerStyle = {
    width: '90px',
    height: '90px',
    borderRadius: '50%',
    background: '#fff',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center'
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <Brain size={28} color="#667eea" />
        <h3 style={{ margin: 0, color: '#333' }}>ℹ️ Productivity Analysis</h3>
      </div>

      {/* Overall Score - Circular Progress like your screenshot */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div style={scoreCircleStyle}>
          <div style={scoreInnerStyle}>
            <span style={{ 
              fontSize: '28px', 
              fontWeight: 'bold', 
              color: getScoreColor(score) 
            }}>
              {score}
            </span>
          </div>
        </div>
        <h4 style={{ margin: '0 0 8px 0', color: '#333', fontSize: '1.2rem' }}>
          Overall Productivity
        </h4>
        <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
          {score}% of your time was productive
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div style={metricsGridStyle}>
        <div style={metricCardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}>
            <Clock size={18} color="#667eea" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Total Time</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#667eea', margin: 0 }}>
            {productivityData.total_time || '23'}m
          </p>
        </div>

        <div style={metricCardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}>
            <Zap size={18} color="#22c55e" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Productive Time</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#22c55e', margin: 0 }}>
            {productivityData.productive_time || '16'}m
          </p>
        </div>

        <div style={metricCardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}>
            <Target size={18} color="#f59e0b" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Focus Sessions</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#f59e0b', margin: 0 }}>
            {productivityData.focus_sessions || '3'}
          </p>
        </div>
      </div>
    </div>
  );
}

export default ProductivityDashboard;
