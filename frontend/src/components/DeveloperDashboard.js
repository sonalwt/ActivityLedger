// DeveloperDashboard.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format, startOfDay, endOfDay, subDays, startOfWeek, endOfWeek, startOfMonth, endOfMonth, subWeeks, subMonths } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Calendar, RefreshCw, Activity, Clock, ArrowLeft } from 'lucide-react';
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
  const [topActivities, setTopActivities] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [groupedActivities, setGroupedActivities] = useState({});

  const [quickRange, setQuickRange] = useState("this_week");

  const API_BASE = process.env.REACT_APP_API_URL || '';

  const toIST = (d) => {
    return d.toISOString().split(".")[0] + "Z";
  };

  // Week starts on Monday (weekStartsOn: 1)
  const applyQuickRange = (range) => {
    setQuickRange(range);
    const now = new Date();
    const weekOpts = { weekStartsOn: 1 };
    switch (range) {
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
    }
  }, [developer]);

  // Fetch data when developer or dates change
  useEffect(() => {
    if (!developer) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const developerId =
          developer.id ||
          developer.developer_id ||
          developer.username ||
          developer.name;

        const startStr = toIST(startDate);
        const endStr = toIST(endDate);

        const { data: catData } = await axios.get(
          `${API_BASE}/api/activity-categories/${developerId}`,
          {
            params: { start_date: startStr, end_date: endStr },
          }
        );

        const totalSeconds = catData.actual_work_seconds || 0;
        const grouped = catData.activities_by_category || {};
        const stats = catData.statistics || {};

        // Build category breakdown
        const breakdown = {};
        Object.entries(stats).forEach(([cat, d]) => {
          breakdown[cat] = {
            count: d.count,
            duration: d.duration,
            duration_hours: d.duration_hours,
            percentage: d.percentage,
          };
        });

        // Top 5 activities
        const list = [];
        Object.entries(catData.top_activities_by_category || {}).forEach(([cat, items]) => {
          items.forEach((a) => list.push({ ...a, category: cat }));
        });
        const top5 = list.sort((a, b) => b.duration - a.duration).slice(0, 5);

        // Flat list
        const flat = [];
        Object.entries(grouped).forEach(([cat, items]) => {
          items.forEach((a) => flat.push({ ...a, category: cat }));
        });

        setTotalTime(totalSeconds);
        setTrackedTime(catData.total_tracked_seconds || 0);
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
      if (display.endsWith("s")) {
        return display;
      }
    }
    return formatTime(seconds);
  };

  const IDE_NAMES = ['visual studio code', 'code', 'cursor', 'pycharm', 'intellij'];

  const formatActivityTitle = (title, projectName, filePath) => {
    const fileName = filePath ? filePath.split(/[/\\]/).pop() : '';

    if (!title || !title.trim()) {
      return fileName || projectName || 'Unknown';
    }
    if (IDE_NAMES.includes(title.trim().toLowerCase())) {
      const detail = fileName || projectName;
      return detail ? `${title.trim()} - ${detail}` : title;
    }
    return title
      .replace(/ - Google Chrome$/, '')
      .replace(/ - Mozilla Firefox$/, '')
      .replace(/ - Microsoft Edge$/, '')
      .replace(/ - Visual Studio Code$/, '')
      .replace(/ – .*$/, '')
      .trim()
      .slice(0, 120);
  };

  const formatActivityDate = (value) => {
    if (!value) return "";
    const d = new Date(value);
    if (isNaN(d.getTime())) return "";
    return format(d, "dd MMM yyyy");
  };

  // ---------------- PRODUCTIVITY ----------------
  const getProductivity = () => {
    const DAILY_TARGET_SEC = 8 * 3600; // 8-hour working day target
    const productiveSec =
      (categoryBreakdown.coding?.duration || 0) +
      (categoryBreakdown.server?.duration || 0) +
      (categoryBreakdown.browser?.duration || 0);

    // Count weekdays (Mon-Fri) in selected date range
    let workingDays = 0;
    const d = new Date(startDate);
    const rangeEnd = new Date(endDate);
    while (d <= rangeEnd) {
      const day = d.getDay();
      if (day !== 0 && day !== 6) workingDays++;
      d.setDate(d.getDate() + 1);
    }
    workingDays = Math.max(workingDays, 1);

    const targetSec = workingDays * DAILY_TARGET_SEC;
    const totalSec = trackedTime || totalTime;
    const minActiveSeconds = 2 * 3600;
    const score = totalSec > minActiveSeconds
      ? Math.min(100, Math.round((productiveSec / targetSec) * 100))
      : 0;

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
    datasets: [
      {
        data: productivity.categories.map((c) => c.time),
        backgroundColor: PIE_COLORS,
      },
    ],
  };

  // ---------------- UI ----------------
  return (
    <div className="developer-dashboard">

      {/* HEADER */}
      <div className="dev-dashboard-header">
        <h1>{developer ? `${developer.name}'s Dashboard` : "Dashboard"}</h1>

        <div className="date-picker-wrapper">
          <select
            className="quick-range-select"
            value={quickRange}
            onChange={(e) => applyQuickRange(e.target.value)}
          >
            <option value="this_week">Current Week</option>
            <option value="last_week">Last Week</option>
            <option value="this_month">Current Month</option>
            <option value="last_month">Last Month</option>
          </select>
          <Calendar size={20} />
          <DatePicker
            selected={startDate}
            onChange={(date) => { setStartDate(date); setQuickRange("custom"); }}
            selectsStart
            startDate={startDate}
            endDate={endDate}
            dateFormat="MMM d, yyyy"
          />
          <span>to</span>
          <DatePicker
            selected={endDate}
            onChange={(date) => { setEndDate(date); setQuickRange("custom"); }}
            selectsEnd
            startDate={startDate}
            endDate={endDate}
            minDate={startDate}
            dateFormat="MMM d, yyyy"
          />
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
                      const index = elements[0].index;
                      setSelectedTab(index);
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
                <div
                  key={i}
                  className="legend-item"
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedTab(i);
                    document.getElementById('category-details-section')?.scrollIntoView({ behavior: 'smooth' });
                  }}
                >
                  <span className="legend-color" style={{ background: pieData.datasets[0].backgroundColor[i] }} />
                  <span>{cat.displayName}</span>
                  <span>{cat.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CATEGORY DETAILS */}
      {!loading && productivity.categories.length > 0 && (
        <div id="category-details-section" className="category-details">
          <h3>Category Details</h3>

          <div className="category-tabs">
            <div className="tab-headers">
              {productivity.categories.map((cat, i) => (
                <button
                  key={i}
                  className={`tab-header ${selectedTab === i ? "active" : ""}`}
                  onClick={() => setSelectedTab(i)}
                >
                  <span>{cat.displayName}</span>
                  <span>{cat.percentage.toFixed(1)}%</span>
                </button>
              ))}
            </div>

            <div className="tab-content">
              {(groupedActivities[productivity.categories[selectedTab]?.name] || []).length > 0 ? (
                <div className="category-activity-list">
                  <h4>Activities in this category</h4>

                  <div className="activity-scroll">
                    {(groupedActivities[productivity.categories[selectedTab]?.name] || [])
                      .slice(0, 50)
                      .map((act, j) => (
                        <div key={j} className="category-activity-item">
                          <div className="activity-info">
                            <div className="activity-title">{formatActivityTitle(act.window_title, act.project_name, act.file_path)}</div>
                            {act.timestamp && (
                              <div className="activity-date">
                                {formatActivityDate(act.timestamp)}
                              </div>
                            )}
                            <div className="activity-meta">
                              <span>{act.application_name || "Unknown"}</span>
                              {act.project_name && <span> &bull; {act.project_name}</span>}
                              {act.activity_count > 1 && <span> &bull; {act.activity_count} times</span>}
                            </div>
                          </div>

                          <div className="activity-duration">
                            {formatDurationDisplay(
                                act.duration_display,
                                act.duration_hours ? act.duration_hours * 3600 : act.duration
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <p>No activity in this category.</p>
              )}
            </div>
          </div>
        </div>
      )}

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
                        {act.activity_count > 1 && (
                          <span className="activity-count">({act.activity_count}x)</span>
                        )}
                      </div>
                      {act.project_name && act.project_name !== "general" && (
                        <div className="activity-project">
                          <span className="project-badge">{act.project_name}</span>
                        </div>
                      )}
                    </div>
                  </td>

                  <td>
                    <span className={`category-badge category-${act.category}`}>{{ coding: "Coding", browser: "Browser", server: "Server", "non-work": "Non-Work" }[act.category] || act.category}</span>
                  </td>

                    <td>{formatDurationDisplay(act.duration_display, act.duration)}</td>

                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && activityData.length === 0 && (
        <div className="no-data">
          <p>No activity for selected range.</p>
        </div>
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
