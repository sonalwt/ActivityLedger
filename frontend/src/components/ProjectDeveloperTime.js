// ProjectDeveloperTime.js - Project-wise Developer Time Spent View with Charts
import React, { useState, useEffect, useRef } from 'react';
import { format, startOfDay, endOfDay, subMonths, startOfMonth } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Calendar, Users, Clock, ChevronDown, ArrowLeft, FolderOpen, TrendingUp, Search, X } from 'lucide-react';
import { toast } from 'react-toastify';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import './ProjectDeveloperTime.css';

function ProjectDeveloperTime({ onBack }) {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [projectData, setProjectData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const [startDate, setStartDate] = useState(startOfDay(startOfMonth(subMonths(new Date(), 2)))); // 2 months back (e.g. Dec 1 if current is Feb)
  const [endDate, setEndDate] = useState(endOfDay(new Date()));

  const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

  // Color palette for developers
  const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];

  // Convert JS date to UTC ISO string for backend query
  const toIST = (d) => {
    return d.toISOString().split(".")[0] + "Z";
  };

  // Fetch all unique projects (no date filter - show ALL projects)
  // NOTE: Backend filters to only show projects where at least one developer spent >10 minutes
  const fetchProjects = async () => {
    setLoadingProjects(true);
    try {
      const token = localStorage.getItem('token');

      // Fetch ALL projects without date filter
      // Backend automatically filters: only projects where any developer spent >10 minutes
      const response = await fetch(
        `${API_BASE}/api/all-projects`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Backend handles all filtering (2h threshold + pattern-based validation)
        const filteredProjects = (data.projects || []).filter(p =>
          p.project_name && p.project_name.trim() !== ''
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
  };

  // Fetch project developer time data
  const fetchProjectData = async (projectName) => {
    if (!projectName) {
      setProjectData(null);
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const startStr = toIST(startDate);
      const endStr = toIST(endDate);

      const response = await fetch(
        `${API_BASE}/api/project/${encodeURIComponent(projectName)}/developers-time?start_date=${startStr}&end_date=${endStr}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setProjectData(data);
      } else {
        throw new Error('Failed to fetch project data');
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to fetch project developer data');
    } finally {
      setLoading(false);
    }
  };

  // Load projects on mount only (no date dependency - show ALL projects)
  useEffect(() => {
    fetchProjects();
  }, []);

  // Load project data when selection changes
  useEffect(() => {
    fetchProjectData(selectedProject);
  }, [selectedProject, startDate, endDate]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filtered projects based on search
  const filteredProjects = projects.filter(p =>
    p.project_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Format time display
  const formatTime = (hours) => {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  // Prepare chart data for date-wise breakdown
  const getDatewiseChartData = () => {
    if (!projectData?.datewise_breakdown) return [];

    return Object.entries(projectData.datewise_breakdown)
      .sort(([a], [b]) => new Date(a) - new Date(b))
      .map(([dateStr, devData]) => {
        const entry = {
          date: format(new Date(dateStr), 'MMM d'),
          fullDate: format(new Date(dateStr), 'EEE, MMM d'),
          total: 0
        };

        devData.forEach(d => {
          const devName = (d.developer_name || d.developer_id).split(' ')[0];
          entry[devName] = parseFloat(d.hours.toFixed(2));
          entry.total += d.hours;
        });

        entry.total = parseFloat(entry.total.toFixed(2));
        return entry;
      });
  };

  // Prepare pie chart data for developer contribution
  const getPieChartData = () => {
    if (!projectData?.developers) return [];

    return projectData.developers.map((dev, index) => ({
      name: dev.developer_name || dev.developer_id,
      value: parseFloat(dev.total_hours.toFixed(2)),
      percentage: dev.percentage,
      color: COLORS[index % COLORS.length]
    }));
  };

  // Custom tooltip for pie chart
  const CustomPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="tooltip-name">{data.name}</p>
          <p>Time: {formatTime(data.value)}</p>
          <p>Contribution: {data.percentage}%</p>
        </div>
      );
    }
    return null;
  };

  const dateChartData = getDatewiseChartData();
  const pieChartData = getPieChartData();

  return (
    <div className="project-developer-time">
      {/* Header */}
      <div className="pdt-header">
        {onBack && (
          <button onClick={onBack} className="back-button">
            <ArrowLeft size={16} /> Back
          </button>
        )}

        <h1>
          <FolderOpen size={28} color="#4f46e5" />
          Project Time Analysis
        </h1>

        <div className="date-picker-wrapper">
          <Calendar size={20} />
          <DatePicker
            selected={startDate}
            onChange={setStartDate}
            selectsStart
            startDate={startDate}
            endDate={endDate}
            dateFormat="MMM d, yyyy"
          />
          <span>to</span>
          <DatePicker
            selected={endDate}
            onChange={setEndDate}
            selectsEnd
            startDate={startDate}
            endDate={endDate}
            minDate={startDate}
            dateFormat="MMM d, yyyy"
          />
        </div>
      </div>

      {/* Project Selection Row */}
      <div className="project-info-row">
        {/* Project Dropdown */}
        <div className="project-select-wrapper">
          <label className="field-label">
            <FolderOpen size={16} />
            Project
          </label>
          <div className="project-dropdown-wrapper" ref={dropdownRef}>
            {loadingProjects ? (
              <div className="dropdown-loading">Loading...</div>
            ) : (
              <>
                <div
                  className={`project-dropdown-trigger ${dropdownOpen ? 'open' : ''}`}
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                >
                  <span className={selectedProject ? 'selected-text' : 'placeholder-text'}>
                    {selectedProject || '-- Select Project --'}
                  </span>
                  <ChevronDown className={`dropdown-chevron ${dropdownOpen ? 'rotated' : ''}`} size={18} />
                </div>
                {dropdownOpen && (
                  <div className="project-dropdown-menu">
                    <div className="dropdown-search-box">
                      <Search size={16} className="search-icon" />
                      <input
                        type="text"
                        placeholder="Search projects..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="dropdown-search-input"
                        autoFocus
                      />
                      {searchQuery && (
                        <X
                          size={16}
                          className="search-clear"
                          onClick={(e) => { e.stopPropagation(); setSearchQuery(''); }}
                        />
                      )}
                    </div>
                    <div className="dropdown-options-list">
                      {filteredProjects.length === 0 ? (
                        <div className="dropdown-no-results">No projects found</div>
                      ) : (
                        filteredProjects.map((project, index) => (
                          <div
                            key={index}
                            className={`dropdown-option ${selectedProject === project.project_name ? 'active' : ''}`}
                            onClick={() => {
                              setSelectedProject(project.project_name);
                              setDropdownOpen(false);
                              setSearchQuery('');
                            }}
                          >
                            <span className="option-name">{project.project_name}</span>
                            <span className="option-hours">{formatTime(project.total_hours)}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Developers */}
        {projectData && (
          <>
            <div className="info-field developers-field">
              <label className="field-label">
                <Users size={16} />
                Resources
              </label>
              <div className="developers-chips">
                {projectData.developers.map((dev, index) => (
                  <span key={index} className="developer-chip">
                    {dev.developer_name || dev.developer_id}
                  </span>
                ))}
              </div>
            </div>

            {/* Days Active */}
            <div className="info-field">
              <label className="field-label">
                <Calendar size={16} />
                Days Active
              </label>
              <div className="field-value">{projectData.summary.total_days}</div>
            </div>

            {/* Range Hours */}
            <div className="info-field">
              <label className="field-label">
                <Clock size={16} />
                Range Hours
              </label>
              <div className="field-value highlight">{formatTime(projectData.summary.total_hours)}</div>
            </div>

            {/* Overall Hours */}
            <div className="info-field">
              <label className="field-label">
                <Clock size={16} />
                Overall Hours
              </label>
              <div className="field-value overall">{formatTime(projectData.summary.overall_hours)}</div>
            </div>
          </>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-container">
          <div className="spinner loading-spinner"></div>
          <p>Loading project data...</p>
        </div>
      )}

      {/* Project Data Display */}
      {!loading && projectData && (
        <>
          {/* Charts Section */}
          <div className="charts-container">
            {/* Developer Contribution Section - Split View */}
            {projectData.developers.length > 1 && (
              <div className="chart-card pie-chart-card split-view">
                <div className="split-container">
                  {/* Left Half - Contribution Pie Chart */}
                  <div className="split-half">
                    <h3>
                      <Users size={20} />
                      Resource Contribution
                    </h3>
                    <div className="pie-chart-wrapper">
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
                    {/* Legend */}
                    <div className="pie-legend">
                      {pieChartData.map((entry, index) => (
                        <div key={index} className="legend-item">
                          <span className="legend-color" style={{ backgroundColor: entry.color }}></span>
                          <span className="legend-name">{entry.name}</span>
                          <span className="legend-value">{formatTime(entry.value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Right Half - Developer Time Breakdown */}
                  <div className="split-half">
                    <h3>
                      <Clock size={20} />
                      Resource Time Breakdown
                    </h3>
                    <div className="developer-time-list">
                      {projectData.developers.map((dev, index) => (
                        <div key={index} className="developer-time-item">
                          <div className="dev-info">
                            <span
                              className="dev-color-dot"
                              style={{ backgroundColor: COLORS[index % COLORS.length] }}
                            ></span>
                            <span className="dev-name">{dev.developer_name || dev.developer_id}</span>
                          </div>
                          <div className="dev-stats">
                            <div className="dev-time">{formatTime(dev.total_hours)}</div>
                            <div className="dev-percentage">{dev.percentage}%</div>
                          </div>
                          <div className="dev-progress-bar">
                            <div
                              className="dev-progress-fill"
                              style={{
                                width: `${dev.percentage}%`,
                                backgroundColor: COLORS[index % COLORS.length]
                              }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Area Chart for Trend */}
            <div className="chart-card area-chart-card">
              <h3>
                <TrendingUp size={20} />
                Hours Trend Over Time
              </h3>
              <div className="area-chart-wrapper">
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={dateChartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      tickFormatter={(value) => `${value}h`}
                    />
                    <Tooltip
                      formatter={(value) => [formatTime(value), 'Total Hours']}
                      labelFormatter={(label) => dateChartData.find(d => d.date === label)?.fullDate || label}
                    />
                    <Area
                      type="monotone"
                      dataKey="total"
                      stroke="#0ea5e9"
                      fillOpacity={1}
                      fill="url(#colorTotal)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}

      {/* No Project Selected */}
      {!loading && !selectedProject && !loadingProjects && (
        <div className="no-selection">
          <FolderOpen size={64} color="#d1d5db" />
          <h3>Select a Project</h3>
          <p>Choose a project from the dropdown above to view resource time breakdown</p>
        </div>
      )}

      {/* No Data */}
      {!loading && selectedProject && projectData && projectData.developers.length === 0 && (
        <div className="no-data">
          <p>No resource data found for this project in the selected date range.</p>
        </div>
      )}
    </div>
  );
}

export default ProjectDeveloperTime;
