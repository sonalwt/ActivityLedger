import React, { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import { TrendingUp, Calendar, Clock, Activity, BarChart3, Users } from 'lucide-react';
import { toast } from 'react-toastify';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import './AnalyticsTab.css';

const PERIOD_OPTIONS = [
  { value: 'current_month', label: 'Current Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: '3_months', label: 'Last 3 Months' },
  { value: 'current_fy', label: 'Current Financial Year' },
  { value: 'last_fy', label: 'Last Financial Year' },
  { value: 'ytd', label: 'Year to Date' },
];

const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

function AnalyticsTab() {
  const [developers, setDevelopers] = useState([]);
  const [selectedDeveloper, setSelectedDeveloper] = useState('');
  const [period, setPeriod] = useState('current_month');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDevs, setLoadingDevs] = useState(true);

  // Fetch developers list
  useEffect(() => {
    const fetchDevelopers = async () => {
      setLoadingDevs(true);
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/api/developers-orm`, {
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        });
        if (response.ok) {
          const data = await response.json();
          const devs = data.developers || [];
          setDevelopers(devs);
          if (devs.length > 0) {
            setSelectedDeveloper(devs[0].id || devs[0].developer_id);
          }
        }
      } catch (err) {
        console.error(err);
        toast.error('Failed to load developers');
      } finally {
        setLoadingDevs(false);
      }
    };
    fetchDevelopers();
  }, []);

  // Fetch analytics data
  const fetchAnalytics = useCallback(async () => {
    if (!selectedDeveloper) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${API_BASE}/api/developer/${encodeURIComponent(selectedDeveloper)}/analytics?period=${period}`,
        { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        setAnalyticsData(await response.json());
      } else {
        throw new Error('Failed to fetch analytics');
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch analytics data');
      setAnalyticsData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedDeveloper, period]);

  useEffect(() => { fetchAnalytics(); }, [fetchAnalytics]);

  // Prepare chart data
  const chartData = (analyticsData?.daily_analytics || []).map(day => ({
    date: format(new Date(day.date + 'T00:00:00'), 'MMM d'),
    fullDate: format(new Date(day.date + 'T00:00:00'), 'EEE, MMM d, yyyy'),
    productivity: day.productivity_percentage,
    workHours: day.total_hours,
    isHoliday: day.is_holiday,
    holidayName: day.holiday_name || null,
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0]?.payload;
    return (
      <div className="analytics-tooltip">
        <p className="tooltip-date">{data?.fullDate}</p>
        {data?.isHoliday && <p className="tooltip-holiday">Holiday: {data.holidayName}</p>}
        {payload.map((entry, i) => (
          <p key={i} style={{ color: entry.color, margin: '2px 0' }}>
            {entry.name}: {entry.name === 'Productivity %' ? `${entry.value}%` : `${entry.value}h`}
          </p>
        ))}
      </div>
    );
  };

  // Custom dot — holidays in amber, normal in line color
  const renderDot = (color) => (props) => {
    const { cx, cy, payload } = props;
    if (!cx || !cy) return null;
    if (payload?.isHoliday) {
      return <circle cx={cx} cy={cy} r={6} fill="#f59e0b" stroke="#d97706" strokeWidth={2} />;
    }
    return <circle cx={cx} cy={cy} r={3} fill={color} stroke="none" />;
  };

  const summary = analyticsData?.summary;

  return (
    <div className="analytics-tab">
      {/* Header */}
      <div className="analytics-header">
        <h1><BarChart3 size={28} color="white" /> Productivity Analytics</h1>
        <div className="analytics-filters">
          <div className="filter-group">
            <label><Users size={14} /> Developer</label>
            <select value={selectedDeveloper} onChange={e => setSelectedDeveloper(e.target.value)} disabled={loadingDevs}>
              {loadingDevs ? <option>Loading...</option> : developers.map(dev => (
                <option key={dev.id || dev.developer_id} value={dev.id || dev.developer_id}>{dev.name}</option>
              ))}
            </select>
          </div>
          <div className="filter-group">
            <label><Calendar size={14} /> Period</label>
            <select value={period} onChange={e => setPeriod(e.target.value)}>
              {PERIOD_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && !loading && (
        <div className="analytics-summary-cards">
          <div className="summary-card">
            <div className="summary-icon" style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}>
              <TrendingUp size={20} color="white" />
            </div>
            <div className="summary-content">
              <div className="summary-value">{summary.avg_productivity_percentage}%</div>
              <div className="summary-label">Avg Productivity</div>
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-icon" style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
              <Clock size={20} color="white" />
            </div>
            <div className="summary-content">
              <div className="summary-value">{summary.avg_work_hours}h</div>
              <div className="summary-label">Avg Work Hours/Day</div>
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
              <Calendar size={20} color="white" />
            </div>
            <div className="summary-content">
              <div className="summary-value">{summary.total_working_days}</div>
              <div className="summary-label">Working Days</div>
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-icon" style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)' }}>
              <Activity size={20} color="white" />
            </div>
            <div className="summary-content">
              <div className="summary-value">{summary.total_work_hours}h</div>
              <div className="summary-label">Total Hours</div>
            </div>
          </div>
        </div>
      )}

      {/* Line Chart */}
      {loading ? (
        <div className="analytics-loading">
          <div className="spinner"></div>
          <p>Loading analytics...</p>
        </div>
      ) : chartData.length > 0 ? (
        <div className="analytics-chart-card">
          <div className="chart-header">
            <h3><TrendingUp size={20} /> Daily Productivity & Work Hours Trend</h3>
            <div className="chart-legend-custom">
              <span className="legend-item">
                <span className="legend-dot" style={{ background: '#667eea' }}></span>
                Productivity %
              </span>
              <span className="legend-item">
                <span className="legend-dot" style={{ background: '#10b981' }}></span>
                Work Hours
              </span>
              <span className="legend-item">
                <span className="legend-dot holiday-dot"></span>
                Holiday
              </span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12, fill: '#64748b' }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12, fill: '#667eea' }}
                tickFormatter={v => `${v}%`}
                domain={[0, 100]}
                label={{ value: 'Productivity %', angle: -90, position: 'insideLeft',
                         style: { fill: '#667eea', fontSize: 12 } }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 12, fill: '#10b981' }}
                tickFormatter={v => `${v}h`}
                label={{ value: 'Work Hours', angle: 90, position: 'insideRight',
                         style: { fill: '#10b981', fontSize: 12 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="productivity"
                name="Productivity %"
                stroke="#667eea"
                strokeWidth={2}
                dot={renderDot('#667eea')}
                activeDot={{ r: 6 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="workHours"
                name="Work Hours"
                stroke="#10b981"
                strokeWidth={2}
                dot={renderDot('#10b981')}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="analytics-no-data">
          <BarChart3 size={64} color="#d1d5db" />
          <h3>No Data Available</h3>
          <p>Select a developer and period to view analytics</p>
        </div>
      )}
    </div>
  );
}

export default AnalyticsTab;
