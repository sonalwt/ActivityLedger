import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { format } from 'date-fns';
import { TrendingUp, Calendar, Clock, BarChart3, Users, UserX } from 'lucide-react';
import { toast } from 'react-toastify';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import './AnalyticsTab.css';

const PERIOD_OPTIONS = [
  { value: 'current_month', label: 'Current Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: '3_months', label: 'Last 3 Months' },
  { value: 'current_fy', label: 'Current Financial Year' },
  { value: 'last_fy', label: 'Last Financial Year' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'custom', label: 'Custom Date Range' },
];

const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

function AnalyticsTab() {
  const [developers, setDevelopers] = useState([]);
  const [selectedDeveloper, setSelectedDeveloper] = useState('');
  const [period, setPeriod] = useState('current_month');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDevs, setLoadingDevs] = useState(true);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

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
    if (period === 'custom' && (!customStart || !customEnd)) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      let url = `${API_BASE}/api/developer/${encodeURIComponent(selectedDeveloper)}/analytics?period=${period}`;
      if (period === 'custom') {
        url += `&start_date=${customStart}&end_date=${customEnd}`;
      }
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
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
  }, [selectedDeveloper, period, customStart, customEnd]);

  useEffect(() => { fetchAnalytics(); }, [fetchAnalytics]);

  // Prepare chart data — trim empty leading dates, split line vs dots
  const chartData = useMemo(() => {
    const days = analyticsData?.daily_analytics || [];
    if (!days.length) return [];

    // Find first day with any activity (skip empty months before developer started)
    const firstActiveIdx = days.findIndex(d => d.productivity_percentage > 0);
    const trimmed = firstActiveIdx > 0 ? days.slice(firstActiveIdx) : days;

    return trimmed.map(day => {
      const isWorking = day.status === 'working' || day.productivity_percentage > 0;
      return {
        date: format(new Date(day.date + 'T00:00:00'), 'MMM d'),
        fullDate: format(new Date(day.date + 'T00:00:00'), 'EEE, MMM d, yyyy'),
        // Trend line — null for non-working days, connectNulls bridges smoothly
        trend: isWorking ? day.productivity_percentage : null,
        // Dot value — always present for marker rendering
        dotValue: day.productivity_percentage,
        isHoliday: day.is_holiday,
        isLeave: day.is_leave,
        isWeekend: day.is_weekend,
        status: day.status,
        holidayName: day.holiday_name || null,
        productiveHours: day.productive_hours,
        totalHours: day.total_hours,
      };
    });
  }, [analyticsData]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    // Use the last payload entry (dotValue series has all data points)
    const data = (payload.find(p => p.dataKey === 'dotValue') || payload[0])?.payload;
    if (!data) return null;

    const statusLabel = {
      working: 'Working Day',
      leave: 'On Leave',
      holiday: `Holiday${data.holidayName ? ': ' + data.holidayName : ''}`,
      weekend: data.dotValue > 0 ? 'Weekend (Worked)' : 'Weekend',
    }[data.status] || data.status;

    return (
      <div className="analytics-tooltip">
        <p className="tooltip-date">{data.fullDate}</p>
        <p className={`tooltip-status tooltip-status--${data.status}`}>{statusLabel}</p>
        {data.dotValue > 0 && (
          <>
            <p className="tooltip-value">Productivity: <strong>{data.dotValue}%</strong></p>
            <p className="tooltip-hours">{data.productiveHours}h productive / {data.totalHours}h total</p>
          </>
        )}
      </div>
    );
  };

  // Single dot renderer — distinct color per day type
  const renderDot = (props) => {
    const { cx, cy, payload } = props;
    if (!cx || !cy) return null;
    if (payload?.isLeave) {
      return <circle cx={cx} cy={cy} r={8} fill="#ef4444" stroke="#fff" strokeWidth={2} />;
    }
    if (payload?.isHoliday) {
      return <circle cx={cx} cy={cy} r={8} fill="#f59e0b" stroke="#fff" strokeWidth={2} />;
    }
    if (payload?.isWeekend && payload?.dotValue === 0) {
      return <circle cx={cx} cy={cy} r={5} fill="#94a3b8" stroke="#fff" strokeWidth={1.5} />;
    }
    if (payload?.isWeekend) {
      return <circle cx={cx} cy={cy} r={6} fill="#38bdf8" stroke="#fff" strokeWidth={2} />;
    }
    return <circle cx={cx} cy={cy} r={5} fill="#667eea" stroke="#fff" strokeWidth={2} />;
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
          {period === 'custom' && (
            <>
              <div className="filter-group">
                <label>From</label>
                <input type="date" className="filter-date" value={customStart} onChange={e => setCustomStart(e.target.value)} />
              </div>
              <div className="filter-group">
                <label>To</label>
                <input type="date" className="filter-date" value={customEnd} onChange={e => setCustomEnd(e.target.value)} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Loading State — skeleton shimmer */}
      {loading && (
        <>
          <div className="analytics-summary-cards">
            {[0, 1, 2, 3].map(i => (
              <div className="summary-card skeleton-card" key={i}>
                <div className="skeleton-icon shimmer"></div>
                <div className="summary-content">
                  <div className="skeleton-value shimmer"></div>
                  <div className="skeleton-label shimmer"></div>
                </div>
              </div>
            ))}
          </div>
          <div className="analytics-chart-card">
            <div className="chart-header">
              <div className="skeleton-title shimmer"></div>
            </div>
            <div className="skeleton-chart shimmer"></div>
          </div>
        </>
      )}

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
            <div className="summary-icon" style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}>
              <UserX size={20} color="white" />
            </div>
            <div className="summary-content">
              <div className="summary-value">{summary.leave_days || 0}</div>
              <div className="summary-label">Leave Days</div>
            </div>
          </div>
        </div>
      )}

      {/* Line Chart */}
      {!loading && chartData.length > 0 ? (
        <div className="analytics-chart-card">
          <div className="chart-header">
            <h3><TrendingUp size={20} /> Daily Productivity Trend</h3>
            <div className="chart-legend-custom">
              <span className="legend-item">
                <span className="legend-dot working-dot"></span>
                Working Day
              </span>
              <span className="legend-item">
                <span className="legend-dot leave-dot"></span>
                Leave
              </span>
              <span className="legend-item">
                <span className="legend-dot holiday-dot"></span>
                Holiday
              </span>
              <span className="legend-item">
                <span className="legend-dot weekend-dot"></span>
                Weekend
              </span>
              <span className="legend-item">
                <span className="legend-dot weekend-worked-dot"></span>
                Weekend (Worked)
              </span>
            </div>
          </div>

          {/* Full width for ≤31 days, scrollable for longer periods */}
          <div className={chartData.length > 31 ? 'chart-scroll-wrapper' : ''}>
            <div style={{ width: chartData.length > 31 ? chartData.length * 40 : '100%', height: 420 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 20, right: 80, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#667eea' }}
                    tickFormatter={v => `${v}%`}
                    domain={[0, 100]}
                    label={{ value: 'Productivity %', angle: -90, position: 'insideLeft',
                             style: { fill: '#667eea', fontSize: 12 } }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  {summary && (
                    <ReferenceLine
                      y={summary.avg_productivity_percentage}
                      stroke="#667eea"
                      strokeDasharray="6 4"
                      strokeWidth={1.5}
                      label={{ value: `Avg ${summary.avg_productivity_percentage}%`, position: 'right',
                               style: { fill: '#667eea', fontSize: 11, fontWeight: 600 } }}
                    />
                  )}
                  {/* Smooth trend line — bridges over non-working days */}
                  <Line
                    type="monotone"
                    dataKey="trend"
                    name="Productivity %"
                    stroke="#667eea"
                    strokeWidth={2}
                    dot={false}
                    activeDot={false}
                    connectNulls={true}
                  />
                  {/* Marker dots — all days at actual positions */}
                  <Line
                    type="monotone"
                    dataKey="dotValue"
                    name="Day Markers"
                    stroke="none"
                    strokeWidth={0}
                    dot={renderDot}
                    activeDot={{ r: 7 }}
                    legendType="none"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : !loading ? (
        <div className="analytics-no-data">
          <BarChart3 size={64} color="#d1d5db" />
          <h3>No Data Available</h3>
          <p>Select a developer and period to view analytics</p>
        </div>
      ) : null}
    </div>
  );
}

export default AnalyticsTab;
