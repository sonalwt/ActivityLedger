import React from 'react';
import { 
  Calendar, 
  Clock, 
  TrendingUp, 
  Target, 
  Award,
  AlertTriangle,
  CheckCircle,
  BarChart3
} from 'lucide-react';

function DailyHoursReport({ data }) {

  // Use the data prop directly instead of making API calls
  const dailyHoursData = data;

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
      });
    } catch (error) {
      return dateStr; // Return original if parsing fails
    }
  };

  const getStatusIcon = (color) => {
    switch (color) {
      case 'green':
        return <CheckCircle size={16} color="#22c55e" />;
      case 'yellow':
        return <AlertTriangle size={16} color="#f59e0b" />;
      case 'red':
        return <Target size={16} color="#ef4444" />;
      default:
        return <Clock size={16} color="#6b7280" />;
    }
  };

  const getStatusColor = (color) => {
    switch (color) {
      case 'green':
        return '#22c55e';
      case 'yellow':
        return '#f59e0b';
      case 'red':
        return '#ef4444';
      default:
        return '#6b7280';
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
    justifyContent: 'space-between',
    paddingBottom: '20px',
    borderBottom: '2px solid #e5e7eb'
  };
  if (!dailyHoursData || !Array.isArray(dailyHoursData) || dailyHoursData.length === 0) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Calendar size={24} color="#667eea" />
            <h3 style={{ margin: 0, color: '#333' }}>📊 Daily Working Hours</h3>
          </div>
          <span style={{ 
            background: '#f0f0f0', 
            padding: '4px 12px', 
            borderRadius: '12px', 
            fontSize: '0.8rem', 
            color: '#666' 
          }}>
            7 working days
          </span>
        </div>
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <BarChart3 size={48} color="#ccc" style={{ marginBottom: '16px' }} />
          <p>No daily hours data available</p>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Calendar size={24} color="#667eea" />
          <h3 style={{ margin: 0, color: '#333' }}>📊 Daily Working Hours</h3>
        </div>
        <span style={{ 
          background: '#f0f0f0', 
          padding: '4px 12px', 
          borderRadius: '12px', 
          fontSize: '0.8rem', 
          color: '#666' 
        }}>
          7 working days
        </span>
      </div>

      {/* Daily Hours Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginTop: '20px'
      }}>
        {dailyHoursData.map((day, index) => (
          <div key={index} style={{
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '12px',
            border: `3px solid ${getStatusColor(day.color)}20`,
            borderLeft: `5px solid ${getStatusColor(day.color)}`,
            transition: 'all 0.3s ease'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              marginBottom: '12px' 
            }}>
              <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>
                {formatDate(day.date)}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {getStatusIcon(day.color)}
                <span style={{ 
                  fontSize: '0.8rem', 
                  color: getStatusColor(day.color), 
                  fontWeight: '600' 
                }}>
                  {day.status}
                </span>
              </div>
            </div>
            
            <div style={{ marginBottom: '10px' }}>
              <div style={{ 
                fontSize: '1.8rem', 
                fontWeight: 'bold', 
                color: getStatusColor(day.color) 
              }}>
                {day.hours.toFixed(1)}h
              </div>
            </div>

            {/* Progress Bar */}
            <div style={{
              background: '#e5e7eb',
              borderRadius: '10px',
              height: '6px',
              overflow: 'hidden'
            }}>
              <div style={{
                background: getStatusColor(day.color),
                height: '100%',
                width: `${Math.min(100, (day.hours / 8) * 100)}%`,
                borderRadius: '10px',
                transition: 'width 0.5s ease'
              }}></div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
        gap: '15px',
        marginTop: '25px',
        padding: '20px',
        background: '#f0f9ff',
        borderRadius: '12px',
        border: '1px solid #bae6fd'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '8px' }}>
            <Clock size={18} color="#667eea" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Avg Hours</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#667eea', margin: 0 }}>
            {dailyHoursData.length > 0 ? 
              (dailyHoursData.reduce((sum, day) => sum + day.hours, 0) / dailyHoursData.length).toFixed(1) : 0
            }h
          </p>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '8px' }}>
            <CheckCircle size={18} color="#22c55e" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Excellent</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#22c55e', margin: 0 }}>
            {dailyHoursData.filter(day => day.color === 'green').length}
          </p>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '8px' }}>
            <AlertTriangle size={18} color="#f59e0b" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>On Track</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#f59e0b', margin: 0 }}>
            {dailyHoursData.filter(day => day.color === 'yellow').length}
          </p>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '8px' }}>
            <Target size={18} color="#ef4444" />
            <span style={{ fontWeight: '600', color: '#333', fontSize: '0.9rem' }}>Below Target</span>
          </div>
          <p style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#ef4444', margin: 0 }}>
            {dailyHoursData.filter(day => day.color === 'red').length}
          </p>
        </div>
      </div>
    </div>
  );
}

export default DailyHoursReport;
