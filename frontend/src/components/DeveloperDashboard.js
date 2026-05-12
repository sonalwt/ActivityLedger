// DeveloperDashboard.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format, startOfDay, endOfDay, subDays, startOfWeek, endOfWeek, startOfMonth, endOfMonth, subWeeks, subMonths } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Calendar, RefreshCw, Activity, Clock, ArrowLeft, Radio, Moon } from 'lucide-react';
import './DeveloperDashboard.css';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

function DeveloperDashboard({ developer, onBack }) {
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);

  const [startDate, setStartDate] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [endDate, setEndDate] = useState(() => endOfDay(new Date()));

  const [totalTime, setTotalTime] = useState(0);
  const [trackedTime, setTrackedTime] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState({});
  const [backendProductivityPct, setBackendProductivityPct] = useState(null);
  const [activeDaysCount, setActiveDaysCount] = useState(0);
  const [topActivities, setTopActivities] = useState([]);
  const [selectedTab, setSelectedTab] = useState('live');
  const [groupedActivities, setGroupedActivities] = useState({});

  const [quickRange, setQuickRange] = useState("this_week");

  // Live tab state
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveElapsed, setLiveElapsed] = useState(0);
  const [liveCountdown, setLiveCountdown] = useState(30);
  const liveIntervalRef = useRef(null);
  const countdownRef = useRef(null);
  const elapsedRef = useRef(null);

  // Idle tab state
  const [idleData, setIdleData] = useState(null);
  const [idleLoading, setIdleLoading] = useState(false);
  const [expandedDays, setExpandedDays] = useState({});

  const API_BASE = process.env.REACT_APP_API_URL || '';

  const toIST = (d) => {
    return d.toISOString().split(".")[0] + "Z";
  };

  const getDeveloperId = () =>
    developer?.id || developer?.developer_id || developer?.username || developer?.name;

  // Week starts on Monday (weekStartsOn: 1)
  const applyQuickRange = (range) => {
    setQuickRange(range);
    const now = new Date();
    const weekOpts = { weekStartsOn: 1 };
    switch (range) {
      case "today":
        setStartDate(startOfDay(now));
        setEndDate(endOfDay(now));
        break;
      case "this_week":
        setStartDate(startOfWeek(now, weekOpts));
        setEndDate(endOfDay(now));
        break;
      case "last_week": {
        const lastW = subWeeks(now, 1);
        setStartDate(startOfWeek(lastW, weekOpts));
        setEndDate(endOfWeek(lastW, weekOpts));
        break;
      }
      case "this_month":
        setStartDate(startOfMonth(now));
        setEndDate(endOfDay(now));
        break;
      case "last_month": {
        const lastM = subMonths(now, 1);
        setStartDate(startOfMonth(lastM));
        setEndDate(endOfMonth(lastM));
        break;
      }
      default:
        break;
    }
  };

  // Reset dates when developer changes
  useEffect(() => {
    if (developer) {
      setQuickRange("this_week");
      applyQuickRange("this_week");
      setSelectedTab('live');
    }
  }, [developer]);

  // Fetch main activity data
  useEffect(() => {
    if (!developer) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const developerId = getDeveloperId();
        const startStr = toIST(startDate);
        const endStr = toIST(endDate);

        const { data: catData } = await axios.get(
          `${API_BASE}/api/activity-categories/${developerId}`,
          { params: { start_date: startStr, end_date: endStr } }
        );

        const totalSeconds = catData.total_tracked_seconds || catData.actual_work_seconds || 0;
        const grouped = catData.activities_by_category || {};
        const stats = catData.statistics || {};

        const breakdown = {};
        Object.entries(stats).forEach(([cat, d]) => {
          breakdown[cat] = {
            count: d.count,
            duration: d.duration,
            duration_hours: d.duration_hours,
            percentage: d.percentage,
          };
        });

        const list = [];
        Object.entries(catData.top_activities_by_category || {}).forEach(([cat, items]) => {
          items.forEach((a) => list.push({ ...a, category: cat }));
        });
        const top5 = list.sort((a, b) => b.duration - a.duration).slice(0, 5);

        const flat = [];
        Object.entries(grouped).forEach(([cat, items]) => {
          items.forEach((a) => flat.push({ ...a, category: cat }));
        });

        setTotalTime(totalSeconds);
        setTrackedTime(catData.total_tracked_seconds || 0);
        setBackendProductivityPct(catData.productivity_percentage ?? null);
        setActiveDaysCount(Object.keys(catData.daily_work_breakdown || {}).length || 1);
        setCategoryBreakdown(breakdown);
        setTopActivities(top5);
        setActivityData(flat);
        setGroupedActivities(grouped);
        setLastUpdated(new Date());
      } catch (err) {
        console.error(err);
        toast.error("Failed to fetch activity data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [developer, startDate, endDate]);

  // ---- LIVE TAB ----
  const fetchLiveStatus = async () => {
    if (!developer) return;
    setLiveLoading(true);
    try {
      const { data } = await axios.get(
        `${API_BASE}/api/developer/${getDeveloperId()}/live-status`,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      setLiveData(data);
      setLiveElapsed(data.current_activity?.elapsed_seconds || 0);
      setLiveCountdown(30);
    } catch (err) {
      console.error(err);
    } finally {
      setLiveLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTab !== 'live') {
      clearInterval(liveIntervalRef.current);
      clearInterval(countdownRef.current);
      clearInterval(elapsedRef.current);
      return;
    }
    fetchLiveStatus();
    liveIntervalRef.current = setInterval(fetchLiveStatus, 30000);
    countdownRef.current = setInterval(() => setLiveCountdown(c => Math.max(0, c - 1)), 1000);
    elapsedRef.current = setInterval(() => setLiveElapsed(e => e + 1), 1000);
    return () => {
      clearInterval(liveIntervalRef.current);
      clearInterval(countdownRef.current);
      clearInterval(elapsedRef.current);
    };
  }, [selectedTab, developer]);

  // ---- IDLE TAB ----
  const fetchIdleTime = async () => {
    if (!developer) return;
    setIdleLoading(true);
    try {
      const { data } = await axios.get(
        `${API_BASE}/api/developer/${getDeveloperId()}/idle-time`,
        {
          params: { start_date: toIST(startDate), end_date: toIST(endDate) },
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        }
      );
      setIdleData(data);
    } catch (err) {
      console.error(err);
      toast.error("Failed to fetch idle data.");
    } finally {
      setIdleLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTab !== 'idle') return;
    fetchIdleTime();
  }, [selectedTab, startDate, endDate, developer]);

  // ---------------- FORMATTERS ----------------
  const formatTime = (seconds) => {
    const s = Math.max(0, Math.floor(seconds || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m}m ${sec}s`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
  };

  const formatDurationDisplay = (display, seconds) => {
    if (typeof display === "string") {
      if (display.endsWith("h")) {
        const hours = parseFloat(display.replace("h", ""));
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        return `${h}h ${m}m`;
      }
      if (display.endsWith("m")) {
        const minutes = parseFloat(display.replace("m", ""));
        const m = Math.floor(minutes);
        const s = Math.round((minutes - m) * 60);
        return `${m}m ${s}s`;
      }
      if (display.endsWith("s")) return display;
    }
    return formatTime(seconds);
  };

  const IDE_NAMES = ['visual studio code', 'code', 'cursor', 'pycharm', 'intellij'];
  const GENERIC_PROJECTS = ['general', 'ide work', 'unknown', 'work', 'data', 'temp', 'tmp', 'src', 'app'];

  const formatActivityTitle = (title, projectName, filePath) => {
    const fileName = filePath ? filePath.split(/[/\\]/).pop() : '';
    const hasProject = projectName && !GENERIC_PROJECTS.includes(projectName.trim().toLowerCase());
    if (!title || !title.trim()) {
      return hasProject ? `${projectName} - ${fileName || 'Unknown'}` : fileName || 'Unknown';
    }
    if (IDE_NAMES.includes(title.trim().toLowerCase())) {
      if (hasProject) return fileName ? `${projectName} - ${fileName}` : projectName;
      return fileName ? `${title.trim()} - ${fileName}` : title;
    }
    const cleaned = title
      .replace(/ - Google Chrome$/, '')
      .replace(/ - Mozilla Firefox$/, '')
      .replace(/ - Microsoft Edge$/, '')
      .replace(/ - Visual Studio Code$/, '')
      .replace(/ – .*$/, '')
      .trim()
      .slice(0, 120);
    if (hasProject && !cleaned.toLowerCase().includes(projectName.toLowerCase())) {
      return `${projectName} - ${cleaned}`;
    }
    if (hasProject && cleaned.toLowerCase() === projectName.trim().toLowerCase() && fileName) {
      return `${projectName} - ${fileName}`;
    }
    return cleaned;
  };

  const formatActivityDate = (value) => {
    if (!value) return "";
    const d = new Date(value);
    if (isNaN(d.getTime())) return "";
    return format(d, "dd MMM yyyy, hh:mm a");
  };

  // ---------------- PRODUCTIVITY ----------------
  const getProductivity = () => {
    const score = backendProductivityPct !== null
      ? backendProductivityPct
      : (() => {
          const DAILY_TARGET_SEC = 8 * 3600;
          const productiveSec =
            (categoryBreakdown.coding?.duration || 0) +
            (categoryBreakdown.server?.duration || 0) +
            (categoryBreakdown.browser?.duration || 0);
          const daysWithData = Math.max(activeDaysCount || 1, 1);
          const targetSec = daysWithData * DAILY_TARGET_SEC;
          const totalSec = trackedTime || totalTime;
          const minActiveSeconds = 2 * 3600;
          return totalSec > minActiveSeconds
            ? Math.min(100, Math.round((productiveSec / targetSec) * 100))
            : 0;
        })();

    const displayNames = { coding: "Coding", browser: "Browser", server: "Server", "non-work": "Non-Work" };
    const categoryList = Object.entries(categoryBreakdown).map(([name, d]) => ({
      name,
      displayName: displayNames[name] || name,
      time: d.duration_hours,
      percentage: d.percentage,
    }));

    return { score, categories: categoryList.filter((c) => c.time > 0) };
  };

  const productivity = getProductivity();

  // ---------------- PIE CHART ----------------
  const PIE_COLORS = ["#10b981", "#3b82f6", "#6366f1", "#f59e0b", "#ef4444", "#8b5cf6"];
  const pieData = {
    labels: productivity.categories.map((c) => c.displayName),
    datasets: [{ data: productivity.categories.map((c) => c.time), backgroundColor: PIE_COLORS }],
  };

  // ---------------- LIVE TAB HELPERS ----------------
  const statusConfig = {
    online:  { color: '#10b981', bg: '#d1fae5', label: 'Online',  dot: true },
    afk:     { color: '#f59e0b', bg: '#fef3c7', label: 'AFK',     dot: false },
    offline: { color: '#6b7280', bg: '#f3f4f6', label: 'Offline', dot: false },
  };

  const categoryColors = { coding: '#10b981', browser: '#3b82f6', server: '#6366f1', 'non-work': '#ef4444' };

  // ---------------- UI ----------------
  return (
    <div className="developer-dashboard">

      {/* HEADER */}
      <div className="dev-dashboard-header">
        <h1>{developer ? `${developer.name}'s Dashboard` : "Dashboard"}</h1>
        <div className="date-picker-wrapper">
          <select className="quick-range-select" value={quickRange} onChange={(e) => applyQuickRange(e.target.value)}>
            <option value="today">Today</option>
            <option value="this_week">Current Week</option>
            <option value="last_week">Last Week</option>
            <option value="this_month">Current Month</option>
            <option value="last_month">Last Month</option>
          </select>
          <Calendar size={20} />
          <DatePicker selected={startDate} onChange={(date) => { setStartDate(date); setQuickRange("custom"); }} selectsStart startDate={startDate} endDate={endDate} dateFormat="MMM d, yyyy" />
          <span>to</span>
          <DatePicker selected={endDate} onChange={(date) => { setEndDate(date); setQuickRange("custom"); }} selectsEnd startDate={startDate} endDate={endDate} minDate={startDate} dateFormat="MMM d, yyyy" />
        </div>
      </div>

      {/* STATS */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}>
            <Clock size={20} color="white" />
          </div>
          <div className="stat-content">
            <p>{formatTime(totalTime)}</p>
            <h3>Total Time</h3>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
            <Activity size={20} color="white" />
          </div>
          <div className="stat-content">
            <p>{productivity.score}%</p>
            <h3>Work Activity</h3>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
            <RefreshCw size={20} color="white" />
          </div>
          <div className="stat-content">
            <p>{lastUpdated ? format(lastUpdated, "MMM d, yyyy HH:mm") : "Never"}</p>
            <h3>Last Updated</h3>
          </div>
        </div>
      </div>

      {/* PIE CHART */}
      {!loading && productivity.categories.length > 0 && (
        <div className="category-pie-chart">
          <h3>Category Breakdown</h3>
          <div className="chart-flex-wrapper">
            <div className="chart-big">
              <Pie
                data={pieData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  onClick: (event, elements) => {
                    if (elements.length > 0) {
                      const cat = productivity.categories[elements[0].index];
                      setSelectedTab(cat.name);
                      document.getElementById('category-details-section')?.scrollIntoView({ behavior: 'smooth' });
                    }
                  },
                  onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                  },
                }}
              />
            </div>
            <div className="chart-legend">
              {productivity.categories.map((cat, i) => (
                <div key={i} className="legend-item" style={{ cursor: 'pointer' }}
                  onClick={() => { setSelectedTab(cat.name); document.getElementById('category-details-section')?.scrollIntoView({ behavior: 'smooth' }); }}>
                  <span className="legend-color" style={{ background: pieData.datasets[0].backgroundColor[i] }} />
                  <span>{cat.displayName}</span>
                  <span>{cat.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TABS SECTION */}
      <div id="category-details-section" className="category-details">

        <div className="tab-headers">
          {/* Fixed tabs: Live + Idle */}
          <button className={`tab-header tab-live ${selectedTab === 'live' ? 'active' : ''}`} onClick={() => setSelectedTab('live')}>
            {liveData?.status === 'online' && <span className="live-pulse-dot" />}
            <Radio size={14} />
            <span>Live</span>
          </button>
          <button className={`tab-header tab-idle ${selectedTab === 'idle' ? 'active' : ''}`} onClick={() => setSelectedTab('idle')}>
            <Moon size={14} />
            <span>Idle Time</span>
          </button>

          {/* Divider */}
          {productivity.categories.length > 0 && <div className="tab-divider" />}

          {/* Category tabs */}
          {productivity.categories.map((cat) => (
            <button key={cat.name} className={`tab-header ${selectedTab === cat.name ? 'active' : ''}`} onClick={() => setSelectedTab(cat.name)}>
              <span>{cat.displayName}</span>
              <span>{cat.percentage.toFixed(1)}%</span>
            </button>
          ))}
        </div>

        {/* ---- LIVE TAB CONTENT ---- */}
        {selectedTab === 'live' && (
          <div className="tab-content live-tab-content">
            <div className="live-header-row">
              <h4>Real-Time Activity</h4>
              <div className="live-refresh-info">
                <span className="live-countdown">Refreshing in {liveCountdown}s</span>
                <button className="live-refresh-btn" onClick={fetchLiveStatus} disabled={liveLoading}>
                  <RefreshCw size={14} className={liveLoading ? 'spinning' : ''} />
                </button>
              </div>
            </div>

            {liveLoading && !liveData ? (
              <div className="live-loading"><div className="spinner" /><p>Loading live status...</p></div>
            ) : liveData ? (
              <>
                {/* Status Badge */}
                <div className="live-status-row">
                  {(() => {
                    const cfg = statusConfig[liveData.status] || statusConfig.offline;
                    return (
                      <span className="live-status-badge" style={{ color: cfg.color, background: cfg.bg }}>
                        {cfg.dot && <span className="live-pulse-dot" />}
                        {cfg.label}
                      </span>
                    );
                  })()}
                  <span className="live-last-updated">
                    Last synced: {liveData.last_updated ? format(new Date(liveData.last_updated), "hh:mm:ss a") : "—"}
                  </span>
                </div>

                {/* Current Activity Card */}
                {liveData.current_activity ? (
                  <div className="current-activity-card">
                    <div className="current-activity-header">
                      <span className="current-label">Currently on</span>
                      <span className="elapsed-timer">{formatTime(liveElapsed)}</span>
                    </div>
                    <div className="current-app-name">{liveData.current_activity.app}</div>
                    {liveData.current_activity.title && liveData.current_activity.title !== liveData.current_activity.app && (
                      <div className="current-title">{liveData.current_activity.title}</div>
                    )}
                    <div className="current-meta">
                      {liveData.current_activity.project && (
                        <span className="current-project-badge">{liveData.current_activity.project}</span>
                      )}
                      {liveData.current_activity.category && (
                        <span className="current-category-badge" style={{ background: categoryColors[liveData.current_activity.category] || '#6b7280' }}>
                          {{ coding: "Coding", browser: "Browser", server: "Server", "non-work": "Non-Work" }[liveData.current_activity.category] || liveData.current_activity.category}
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="no-current-activity">No recent activity in the last 15 minutes.</div>
                )}

                {/* Recent Activities */}
                {liveData.recent_activities?.length > 0 && (
                  <div className="recent-activities-section">
                    <h5>Last 15 Minutes</h5>
                    <div className="activity-scroll">
                      {liveData.recent_activities.map((act, i) => (
                        <div key={i} className="category-activity-item">
                          <div className="activity-info">
                            <div className="activity-title">{act.title || act.app}</div>
                            <div className="activity-meta">
                              <span>{act.app}</span>
                              {act.project && <span> &bull; {act.project}</span>}
                              <span> &bull; {formatActivityDate(act.timestamp)}</span>
                            </div>
                          </div>
                          <div className="activity-duration">{formatTime(act.duration)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="no-data-text">Could not load live status.</p>
            )}
          </div>
        )}

        {/* ---- IDLE TIME TAB CONTENT ---- */}
        {selectedTab === 'idle' && (
          <div className="tab-content idle-tab-content">
            <h4>Idle Time Breakdown</h4>

            {idleLoading ? (
              <div className="live-loading"><div className="spinner" /><p>Loading idle data...</p></div>
            ) : idleData ? (
              <>
                {/* Summary Cards */}
                <div className="idle-summary-grid">
                  <div className="idle-summary-card">
                    <div className="idle-summary-value">{formatTime(idleData.total_idle_seconds)}</div>
                    <div className="idle-summary-label">Total Idle Time</div>
                  </div>
                  <div className="idle-summary-card">
                    <div className="idle-summary-value" style={{ color: '#f59e0b' }}>{idleData.idle_percentage}%</div>
                    <div className="idle-summary-label">Idle %</div>
                  </div>
                  <div className="idle-summary-card">
                    <div className="idle-summary-value" style={{ color: '#10b981' }}>{formatTime(idleData.total_active_seconds)}</div>
                    <div className="idle-summary-label">Active Time</div>
                  </div>
                </div>

                {/* Per-Day Breakdown */}
                {idleData.idle_by_day?.length > 0 ? (
                  <div className="idle-days-list">
                    {idleData.idle_by_day.map((day) => (
                      <div key={day.date} className="idle-day-row">
                        <div className="idle-day-header" onClick={() => setExpandedDays(prev => ({ ...prev, [day.date]: !prev[day.date] }))}>
                          <span className="idle-day-date">{format(new Date(day.date), "dd MMM yyyy, EEE")}</span>
                          <div className="idle-day-stats">
                            <span className="idle-day-total">{formatTime(day.total_idle_seconds)}</span>
                            <span className="idle-day-count">{day.periods.length} period{day.periods.length !== 1 ? 's' : ''}</span>
                            <span className="idle-expand-arrow">{expandedDays[day.date] ? '▲' : '▼'}</span>
                          </div>
                        </div>
                        {expandedDays[day.date] && (
                          <div className="idle-periods-list">
                            {day.periods.map((p, i) => (
                              <div key={i} className="idle-period-item">
                                <span className="idle-period-time">{format(new Date(p.start), "hh:mm a")}</span>
                                <span className="idle-period-duration">{p.duration_display}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data-text">No idle periods recorded for this date range.</p>
                )}
              </>
            ) : (
              <p className="no-data-text">Could not load idle data.</p>
            )}
          </div>
        )}

        {/* ---- CATEGORY TAB CONTENT ---- */}
        {selectedTab !== 'live' && selectedTab !== 'idle' && !loading && (
          <div className="tab-content">
            {(groupedActivities[selectedTab] || []).length > 0 ? (
              <div className="category-activity-list">
                <h4>Activities in this category</h4>
                <div className="activity-scroll">
                  {(groupedActivities[selectedTab] || []).slice(0, 50).map((act, j) => (
                    <div key={j} className="category-activity-item">
                      <div className="activity-info">
                        <div className="activity-title">{formatActivityTitle(act.window_title, act.project_name, act.file_path)}</div>
                        {act.timestamp && <div className="activity-date">{formatActivityDate(act.timestamp)}</div>}
                        <div className="activity-meta">
                          <span>{act.application_name || "Unknown"}</span>
                          {act.project_name && <span> &bull; {act.project_name}</span>}
                          {act.file_path && act.file_path.split(/[/\\]/).pop() !== act.project_name && (
                            <span> &bull; {act.file_path.split(/[/\\]/).pop()}</span>
                          )}
                          {act.activity_count > 1 && <span> &bull; {act.activity_count} times</span>}
                        </div>
                      </div>
                      <div className="activity-duration">
                        {formatDurationDisplay(act.duration_display, act.duration_hours ? act.duration_hours * 3600 : act.duration)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p>No activity in this category.</p>
            )}
          </div>
        )}
      </div>

      {/* TOP 5 */}
      {!loading && (
        <div className="top-activities">
          <h3>Top 5 Time-Consuming Activities</h3>
          <table>
            <thead>
              <tr>
                <th>Activity Details</th>
                <th>Category</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {topActivities.map((act, i) => (
                <tr key={i}>
                  <td>
                    <div className="activity-details">
                      <div className="activity-title">
                        {formatActivityTitle(act.window_title, act.project_name, act.file_path) || "No title"}
                        {act.activity_count > 1 && <span className="activity-count">({act.activity_count}x)</span>}
                      </div>
                      {act.project_name && act.project_name !== "general" && (
                        <div className="activity-project"><span className="project-badge">{act.project_name}</span></div>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={`category-badge category-${act.category}`}>
                      {{ coding: "Coding", browser: "Browser", server: "Server", "non-work": "Non-Work" }[act.category] || act.category}
                    </span>
                  </td>
                  <td>{formatDurationDisplay(act.duration_display, act.duration)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && activityData.length === 0 && selectedTab !== 'live' && selectedTab !== 'idle' && (
        <div className="no-data"><p>No activity for selected range.</p></div>
      )}

      {loading && (
        <div className="loading-spinner-container">
          <div className="spinner loading-spinner"></div>
          <p>Loading activity data...</p>
        </div>
      )}
    </div>
  );
}

export default DeveloperDashboard;
