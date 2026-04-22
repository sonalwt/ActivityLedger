// ProjectDeveloperTime.js - Project-wise Developer Time Spent View (Analytics-style UI)
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { format } from 'date-fns';
import { Calendar, Users, Clock, ChevronDown, FolderOpen, TrendingUp, Search, X, Layers} from 'lucide-react';
import { toast } from 'react-toastify';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, ReferenceLine
} from 'recharts';
import './ProjectDeveloperTime.css';

const PERIOD_OPTIONS = [
  { value: 'current_week', label: 'Current Week' },
  { value: 'last_week', label: 'Last Week' },
  { value: 'current_month', label: 'Current Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: '3_months', label: 'Last 3 Months' },
  { value: 'current_year', label: 'Current Year' },
  { value: 'last_year', label: 'Last Year' },
  { value: 'custom', label: 'Custom Date Range' },
];

const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

function ProjectDeveloperTime({ onBack }) {
  const [allDevelopers, setAllDevelopers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [projectData, setProjectData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Developer multi-select filter (drives project filtering)
  const [selectedDevelopers, setSelectedDevelopers] = useState([]);
  const [devDropdownOpen, setDevDropdownOpen] = useState(false);
  const devDropdownRef = useRef(null);
  const [devSearchQuery, setDevSearchQuery] = useState('');

  const [period, setPeriod] = useState('current_week');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Color palette for developers
  const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];

  // Is this a year-based period? (month-wise aggregation)
  const isYearPeriod = period === 'current_year' || period === 'last_year';

  // Build query string for period
  const buildPeriodParams = useCallback(() => {
    let params = `period=${period}`;
    if (period === 'custom' && customStart && customEnd) {
      params += `&start_date=${customStart}&end_date=${customEnd}`;
    }
    return params;
  }, [period, customStart, customEnd]);

  // Fetch all developers (once on mount)
  useEffect(() => {
    const fetchDevelopers = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/api/developers-orm`, {
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          const data = await response.json();
          setAllDevelopers(data.developers || []);
        }
      } catch (err) {
        console.error('Failed to fetch developers:', err);
      }
    };
    fetchDevelopers();
  }, []);

  // Fetch projects (re-fetches when developer selection or period changes)
  const fetchProjects = useCallback(async () => {
    if (period === 'custom' && (!customStart || !customEnd)) return;
    setLoadingProjects(true);
    try {
      const token = localStorage.getItem('token');
      let url = `${API_BASE}/api/all-projects?${buildPeriodParams()}`;
      if (selectedDevelopers.length > 0) {
        url += `&developer_ids=${selectedDevelopers.join(',')}`;
      }
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        const excludedNames = ['scripts', 'ide work', 'mails'];
        const filteredProjects = (data.projects || []).filter(p =>
          p.project_name && p.project_name.trim() !== '' &&
          !excludedNames.includes(p.project_name.toLowerCase())
        );
        setProjects(filteredProjects);
      } else {
        throw new Error('Failed to fetch projects');
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch projects list');
    } finally {
      setLoadingProjects(false);
    }
  }, [buildPeriodParams, selectedDevelopers]);

  // Fetch project developer time data
  const fetchProjectData = useCallback(async () => {
    if (!selectedProject) { setProjectData(null); return; }
    if (period === 'custom' && (!customStart || !customEnd)) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${API_BASE}/api/project/${encodeURIComponent(selectedProject)}/developers-time?${buildPeriodParams()}`,
        { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        setProjectData(await response.json());
      } else {
        throw new Error('Failed to fetch project data');
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch project developer data');
    } finally {
      setLoading(false);
    }
  }, [selectedProject, buildPeriodParams]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);
  useEffect(() => { fetchProjectData(); }, [fetchProjectData]);

  // Reset selected project when developer selection changes (projects list will refresh)
  useEffect(() => { setSelectedProject(''); setProjectData(null); }, [selectedDevelopers]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
      if (devDropdownRef.current && !devDropdownRef.current.contains(e.target)) {
        setDevDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredProjects = projects.filter(p =>
    p.project_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatTime = (hours) => {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  // Toggle developer in multi-select
  const toggleDeveloper = (devId) => {
    setSelectedDevelopers(prev =>
      prev.includes(devId) ? prev.filter(id => id !== devId) : [...prev, devId]
    );
  };

  // Filter projectData by selected developers
  const filteredProjectData = useMemo(() => {
    if (!projectData) return null;
    if (selectedDevelopers.length === 0) return projectData;

    const filteredDevs = projectData.developers.filter(d =>
      selectedDevelopers.includes(d.developer_id)
    );

    const totalHours = filteredDevs.reduce((sum, d) => sum + d.total_hours, 0);
    const devsWithPct = filteredDevs.map(d => ({
      ...d,
      percentage: totalHours > 0 ? parseFloat((d.total_hours / totalHours * 100).toFixed(1)) : 0
    }));

    // Filter datewise_breakdown
    const filteredDatewise = {};
    if (projectData.datewise_breakdown) {
      Object.entries(projectData.datewise_breakdown).forEach(([date, devData]) => {
        const filtered = devData.filter(d => selectedDevelopers.includes(d.developer_id));
        if (filtered.length > 0) filteredDatewise[date] = filtered;
      });
    }

    return {
      ...projectData,
      developers: devsWithPct,
      datewise_breakdown: filteredDatewise,
      summary: {
        ...projectData.summary,
        total_hours: parseFloat(totalHours.toFixed(2)),
        total_developers: filteredDevs.length,
      }
    };
  }, [projectData, selectedDevelopers]);

  // Prepare chart data - day-wise or month-wise based on period
  const chartData = useMemo(() => {
    if (!filteredProjectData?.datewise_breakdown) return [];

    const entries = Object.entries(filteredProjectData.datewise_breakdown)
      .sort(([a], [b]) => new Date(a) - new Date(b));

    if (isYearPeriod) {
      // Month-wise aggregation
      const monthMap = {};
      entries.forEach(([dateStr, devData]) => {
        const d = new Date(dateStr);
        const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!monthMap[monthKey]) {
          monthMap[monthKey] = { total: 0 };
        }
        devData.forEach(dev => {
          monthMap[monthKey].total += dev.hours;
        });
      });

      return Object.entries(monthMap)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([monthKey, data]) => {
          const [year, month] = monthKey.split('-');
          return {
            date: format(new Date(parseInt(year), parseInt(month) - 1, 1), 'MMM yyyy'),
            fullDate: format(new Date(parseInt(year), parseInt(month) - 1, 1), 'MMMM yyyy'),
            total: parseFloat(data.total.toFixed(2))
          };
        });
    } else {
      // Day-wise
      return entries.map(([dateStr, devData]) => {
        const entry = {
          date: format(new Date(dateStr), 'MMM d'),
          fullDate: format(new Date(dateStr), 'EEE, MMM d'),
          total: 0
        };
        devData.forEach(d => {
          entry.total += d.hours;
        });
        entry.total = parseFloat(entry.total.toFixed(2));
        return entry;
      });
    }
  }, [filteredProjectData, isYearPeriod]);

  // Prepare pie chart data for developer contribution
  const pieChartData = useMemo(() => {
    if (!filteredProjectData?.developers) return [];
    return filteredProjectData.developers.map((dev, index) => ({
      name: dev.developer_name || dev.developer_id,
      value: parseFloat(dev.total_hours.toFixed(2)),
      percentage: dev.percentage,
      color: COLORS[index % COLORS.length]
    }));
  }, [filteredProjectData]);

  // Custom tooltip for pie chart
  const CustomPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="pdt-tooltip">
          <p className="pdt-tooltip-name">{data.name}</p>
          <p className="pdt-tooltip-value">Time: <strong>{formatTime(data.value)}</strong></p>
          <p className="pdt-tooltip-value">Contribution: <strong>{data.percentage}%</strong></p>
        </div>
      );
    }
    return null;
  };

  const summary = filteredProjectData?.summary;
  const avgLabel = isYearPeriod
    ? `Avg ${(summary ? summary.total_hours / (chartData.length || 1) : 0).toFixed(1)}h/month`
    : `Avg ${(summary ? summary.total_hours / (summary.total_days || 1) : 0).toFixed(1)}h/day`;
  const avgValue = isYearPeriod
    ? parseFloat((summary ? summary.total_hours / (chartData.length || 1) : 0).toFixed(1))
    : parseFloat((summary ? summary.total_hours / (summary.total_days || 1) : 0).toFixed(1));

  return (
    <div className="pdt-tab">
      {/* Header */}
      <div className="pdt-header">
        <h1><FolderOpen size={28} color="white" /> Project Time Analysis</h1>
        <div className="pdt-filters">
          {/* Developer Multi-Select Dropdown (always visible, drives project filter) */}
          <div className="pdt-filter-group pdt-dev-filter" ref={devDropdownRef}>
            <label><Users size={14} /> Resource</label>
            <div className="pdt-dropdown-wrapper">
              <div
                className={`pdt-dropdown-trigger ${devDropdownOpen ? 'open' : ''}`}
                onClick={() => setDevDropdownOpen(!devDropdownOpen)}
              >
                <span className={selectedDevelopers.length > 0 ? 'pdt-selected-text' : 'pdt-placeholder-text'}>
                  {selectedDevelopers.length === 0
                    ? 'All Resources'
                    : selectedDevelopers.length === 1
                      ? (allDevelopers.find(d => d.id === selectedDevelopers[0])?.name || '1 selected')
                      : `${selectedDevelopers.length} selected`}
                </span>
                <ChevronDown className={`pdt-chevron ${devDropdownOpen ? 'rotated' : ''}`} size={16} />
              </div>
              {devDropdownOpen && (
                <div className="pdt-dropdown-menu">
                  <div className="pdt-dropdown-search">
                    <Search size={14} className="pdt-search-icon" />
                    <input
                      type="text"
                      placeholder="Search resources..."
                      value={devSearchQuery}
                      onChange={(e) => setDevSearchQuery(e.target.value)}
                      autoFocus
                    />
                    {devSearchQuery && (
                      <X size={14} className="pdt-search-clear" onClick={(e) => { e.stopPropagation(); setDevSearchQuery(''); }} />
                    )}
                  </div>
                  <div className="pdt-dropdown-actions">
                    <button onClick={() => setSelectedDevelopers(allDevelopers.map(d => d.id))}>Select All</button>
                    <button onClick={() => setSelectedDevelopers([])}>Clear</button>
                  </div>
                  <div className="pdt-dropdown-options">
                    {allDevelopers
                      .filter(d => d.name.toLowerCase().includes(devSearchQuery.toLowerCase()))
                      .map((dev, index) => (
                        <div
                          key={dev.id}
                          className={`pdt-dropdown-option pdt-checkbox-option ${selectedDevelopers.includes(dev.id) ? 'active' : ''}`}
                          onClick={() => toggleDeveloper(dev.id)}
                        >
                          <input
                            type="checkbox"
                            checked={selectedDevelopers.includes(dev.id)}
                            readOnly
                            className="pdt-dev-checkbox"
                          />
                          <span className="pdt-option-name">{dev.name}</span>
                        </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Project Dropdown (auto-filtered by selected developers) */}
          <div className="pdt-filter-group pdt-project-filter" ref={dropdownRef}>
            <label><Layers size={14} /> Project</label>
            {loadingProjects ? (
              <div className="pdt-dropdown-loading">Loading...</div>
            ) : (
              <div className="pdt-dropdown-wrapper">
                <div
                  className={`pdt-dropdown-trigger ${dropdownOpen ? 'open' : ''}`}
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                >
                  <span className={selectedProject ? 'pdt-selected-text' : 'pdt-placeholder-text'}>
                    {selectedProject || '-- Select Project --'}
                  </span>
                  <ChevronDown className={`pdt-chevron ${dropdownOpen ? 'rotated' : ''}`} size={16} />
                </div>
                {dropdownOpen && (
                  <div className="pdt-dropdown-menu">
                    <div className="pdt-dropdown-search">
                      <Search size={14} className="pdt-search-icon" />
                      <input
                        type="text"
                        placeholder="Search projects..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        autoFocus
                      />
                      {searchQuery && (
                        <X size={14} className="pdt-search-clear" onClick={(e) => { e.stopPropagation(); setSearchQuery(''); }} />
                      )}
                    </div>
                    <div className="pdt-dropdown-options">
                      {filteredProjects.length === 0 ? (
                        <div className="pdt-dropdown-empty">No projects found</div>
                      ) : (
                        filteredProjects.map((project, index) => (
                          <div
                            key={index}
                            className={`pdt-dropdown-option ${selectedProject === project.project_name ? 'active' : ''}`}
                            onClick={() => {
                              setSelectedProject(project.project_name);
                              setDropdownOpen(false);
                              setSearchQuery('');
                            }}
                          >
                            <span className="pdt-option-name">{project.project_name}</span>
                            <span className="pdt-option-hours">{formatTime(project.total_hours)}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Period Dropdown */}
          <div className="pdt-filter-group">
            <label><Calendar size={14} /> Period</label>
            <select value={period} onChange={e => setPeriod(e.target.value)} className="pdt-filter-select">
              {PERIOD_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>

          {/* Custom Date Range */}
          {period === 'custom' && (
            <>
              <div className="pdt-filter-group">
                <label>From</label>
                <input type="date" className="pdt-filter-date" value={customStart} onChange={e => setCustomStart(e.target.value)} />
              </div>
              <div className="pdt-filter-group">
                <label>To</label>
                <input type="date" className="pdt-filter-date" value={customEnd} onChange={e => setCustomEnd(e.target.value)} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Loading State - Skeleton Shimmer */}
      {loading && (
        <>
          <div className="pdt-summary-cards">
            {[0, 1, 2, 3].map(i => (
              <div className="pdt-summary-card pdt-skeleton-card" key={i}>
                <div className="pdt-skeleton-icon pdt-shimmer"></div>
                <div className="pdt-summary-content">
                  <div className="pdt-skeleton-value pdt-shimmer"></div>
                  <div className="pdt-skeleton-label pdt-shimmer"></div>
                </div>
              </div>
            ))}
          </div>
          <div className="pdt-chart-card">
            <div className="pdt-chart-header">
              <div className="pdt-skeleton-title pdt-shimmer"></div>
            </div>
            <div className="pdt-skeleton-chart pdt-shimmer"></div>
          </div>
        </>
      )}

      {/* Summary Cards */}
      {summary && !loading && (
        <div className="pdt-summary-cards">
          <div className="pdt-summary-card">
            <div className="pdt-summary-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
              <Calendar size={20} color="white" />
            </div>
            <div className="pdt-summary-content">
              <div className="pdt-summary-value">{summary.total_days}</div>
              <div className="pdt-summary-label">Days Active</div>
            </div>
          </div>
          <div className="pdt-summary-card">
            <div className="pdt-summary-icon" style={{ background: 'linear-gradient(135deg, #0ea5e9, #0284c7)' }}>
              <Clock size={20} color="white" />
            </div>
            <div className="pdt-summary-content">
              <div className="pdt-summary-value">{formatTime(summary.total_hours)}</div>
              <div className="pdt-summary-label">Range Hours</div>
            </div>
          </div>
          <div className="pdt-summary-card">
            <div className="pdt-summary-icon" style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
              <TrendingUp size={20} color="white" />
            </div>
            <div className="pdt-summary-content">
              <div className="pdt-summary-value">{formatTime(summary.overall_hours)}</div>
              <div className="pdt-summary-label">Overall Hours</div>
            </div>
          </div>
          <div className="pdt-summary-card">
            <div className="pdt-summary-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' }}>
              <span style={{ fontSize: '18px', fontWeight: 'bold', color: 'white' }}>₹</span>
            </div>
            <div className="pdt-summary-content">
              <div className="pdt-summary-value">{summary.total_cost ? `₹${summary.total_cost.toLocaleString()}` : '₹0'}</div>
              <div className="pdt-summary-label">Total Cost</div>
            </div>
          </div>
          <div className="pdt-summary-card">
            <div className="pdt-summary-icon" style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}>
              <span style={{ fontSize: '18px', fontWeight: 'bold', color: 'white' }}>₹</span>
            </div>
            <div className="pdt-summary-content">
              <div className="pdt-summary-value">{summary.resource_cost ? `₹${summary.resource_cost.toLocaleString()}` : '₹0'}</div>
              <div className="pdt-summary-label">Resource Cost</div>
            </div>
          </div>
        </div>
      )}

      {/* Developer Chips (below summary cards) */}
      {!loading && filteredProjectData && filteredProjectData.developers.length > 0 && (
        <div className="pdt-developers-row">
          <span className="pdt-developers-label"><Users size={14} /> Resources ({filteredProjectData.developers.length}):</span>
          <div className="pdt-developers-chips">
            {filteredProjectData.developers.map((dev, index) => (
              <span key={index} className="pdt-developer-chip" style={{ borderLeft: `3px solid ${COLORS[index % COLORS.length]}` }}>
                {dev.developer_name || dev.developer_id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Charts Section */}
      {!loading && filteredProjectData && (
        <div className="pdt-charts-container">
          {/* Developer Contribution - Split View */}
          {filteredProjectData.developers.length > 1 && (
            <div className="pdt-chart-card">
              <div className="pdt-chart-header">
                <h3><Users size={20} /> Resource Contribution</h3>
                <div className="pdt-chart-legend">
                  {pieChartData.map((entry, index) => (
                    <span key={index} className="pdt-legend-item">
                      <span className="pdt-legend-dot" style={{ background: entry.color }}></span>
                      {entry.name}
                    </span>
                  ))}
                </div>
              </div>
              <div className="pdt-split-container">
                <div className="pdt-split-half">
                  <div className="pdt-pie-wrapper">
                    <ResponsiveContainer width="100%" height={280}>
                      <PieChart>
                        <Pie
                          data={pieChartData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={85}
                          paddingAngle={3}
                          dataKey="value"
                          label={({ name, percentage }) => `${name} (${percentage}%)`}
                          labelLine={true}
                        >
                          {pieChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomPieTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="pdt-split-half">
                  <div className="pdt-dev-list">
                    {filteredProjectData.developers.map((dev, index) => (
                      <div key={index} className="pdt-dev-item">
                        <div className="pdt-dev-info">
                          <span className="pdt-dev-dot" style={{ backgroundColor: COLORS[index % COLORS.length] }}></span>
                          <span className="pdt-dev-name">{dev.developer_name || dev.developer_id}</span>
                        </div>
                        <div className="pdt-dev-stats">
                          <div className="pdt-dev-time">{formatTime(dev.total_hours)}</div>
                          <div className="pdt-dev-pct">{dev.percentage}%</div>
                        </div>
                        <div className="pdt-dev-bar">
                          <div
                            className="pdt-dev-bar-fill"
                            style={{ width: `${dev.percentage}%`, backgroundColor: COLORS[index % COLORS.length] }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Hours Trend Chart */}
          <div className="pdt-chart-card">
            <div className="pdt-chart-header">
              <h3><TrendingUp size={20} /> {isYearPeriod ? 'Monthly Hours Trend' : 'Daily Hours Trend'}</h3>
              {filteredProjectData.developers.length > 0 && (
                <div className="pdt-chart-legend">
                  <span className="pdt-legend-item">
                    <span className="pdt-legend-dot" style={{ background: '#667eea' }}></span>
                    Total Hours
                  </span>
                  {summary && (
                    <span className="pdt-legend-item">
                      <span className="pdt-legend-line"></span>
                      {avgLabel}
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className={chartData.length > 31 ? 'pdt-chart-scroll' : ''}>
              <div style={{ width: chartData.length > 31 ? chartData.length * 40 : '100%', height: 420 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 20, right: 80, left: 20, bottom: 60 }}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#667eea" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#667eea" stopOpacity={0.05}/>
                      </linearGradient>
                    </defs>
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
                      tickFormatter={(value) => `${value}h`}
                      domain={[0, 'auto']}
                      label={{ value: 'Hours', angle: -90, position: 'insideLeft',
                               style: { fill: '#667eea', fontSize: 12 } }}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload || !payload.length) return null;
                        const data = payload[0]?.payload;
                        if (!data) return null;
                        return (
                          <div className="pdt-tooltip">
                            <p className="pdt-tooltip-name">{data.fullDate}</p>
                            <p className="pdt-tooltip-value">Total: <strong>{formatTime(data.total)}</strong></p>
                          </div>
                        );
                      }}
                    />
                    {summary && (
                      <ReferenceLine
                        y={avgValue}
                        stroke="#667eea"
                        strokeDasharray="6 4"
                        strokeWidth={1.5}
                        label={{
                          value: avgLabel,
                          position: 'right',
                          style: { fill: '#667eea', fontSize: 11, fontWeight: 600 }
                        }}
                      />
                    )}
                    <Area
                      type="monotone"
                      dataKey="total"
                      stroke="#667eea"
                      fillOpacity={1}
                      fill="url(#colorTotal)"
                      strokeWidth={2}
                      dot={{ r: 5, fill: '#667eea', stroke: '#fff', strokeWidth: 2 }}
                      activeDot={{ r: 7 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No Project Selected */}
      {!loading && !selectedProject && !loadingProjects && (
        <div className="pdt-no-data">
          <FolderOpen size={64} color="#d1d5db" />
          <h3>Select a Project</h3>
          <p>Choose a project from the dropdown above to view resource time breakdown</p>
        </div>
      )}

      {/* No Data */}
      {!loading && selectedProject && filteredProjectData && filteredProjectData.developers.length === 0 && (
        <div className="pdt-no-data">
          <FolderOpen size={64} color="#d1d5db" />
          <h3>No Data Available</h3>
          <p>No resource data found for this project in the selected date range.</p>
        </div>
      )}
    </div>
  );
}

export default ProjectDeveloperTime;
