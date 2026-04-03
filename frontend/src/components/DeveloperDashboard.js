// DeveloperDashboard.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format, startOfDay, endOfDay, subDays } from 'date-fns';
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

  const [startDate, setStartDate] = useState(startOfDay(subDays(new Date(), 6)));
  const [endDate, setEndDate] = useState(endOfDay(new Date()));

  const [totalTime, setTotalTime] = useState(0); // <-- REAL WORK HOURS
  const [trackedTime, setTrackedTime] = useState(0); // <-- TOTAL TRACKED SECONDS (for productivity calculation)
  const [lastUpdated, setLastUpdated] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState({});
  const [topActivities, setTopActivities] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [groupedActivities, setGroupedActivities] = useState({});

  const API_BASE = process.env.REACT_APP_API_URL || '';

  // Convert JS date to UTC ISO string for backend query
  // JS Date already knows local timezone, toISOString() converts to UTC correctly
  const toIST = (d) => {
    return d.toISOString().split(".")[0] + "Z";
  };

  useEffect(() => {
    if (developer) {
      setStartDate(startOfDay(subDays(new Date(), 6)));
      setEndDate(endOfDay(new Date()));
    }
  }, [developer]);

  // ---------------- FETCH DATA ----------------
  const fetchActivityData = async () => {
    if (!developer) return;

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
        { params: { start_date: startStr, end_date: endStr } }
      );

      // --------------------------------------------------
      // 🔥 FIXED: Use REAL WORK HOURS (first → last activity)
      // --------------------------------------------------
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

      setTotalTime(totalSeconds); // <-- REAL WORK HOURS SET HERE
      setTrackedTime(catData.total_tracked_seconds || 0); // <-- TRACKED TIME FOR PRODUCTIVITY
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

  useEffect(() => {
    fetchActivityData();
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

    // Example: "3.2h"
    if (display.endsWith("h")) {
      const hours = parseFloat(display.replace("h", ""));
      const h = Math.floor(hours);
      const m = Math.round((hours - h) * 60);
      return `${h}h ${m}m`;
    }

    // Example: "5.0m"
    if (display.endsWith("m")) {
      const minutes = parseFloat(display.replace("m", ""));
      const m = Math.floor(minutes);
      const s = Math.round((minutes - m) * 60);
      return `${m}m ${s}s`;
    }

    // Example: "45s"
    if (display.endsWith("s")) {
      return display.replace("s", "s");
    }
  }

  // fallback to seconds
  return formatTime(seconds);
};



  const IDE_NAMES = ['visual studio code', 'code', 'cursor', 'pycharm', 'intellij'];

  const formatActivityTitle = (title, projectName, filePath) => {
    // Derive file name from file_path if available
    const fileName = filePath ? filePath.split(/[/\\]/).pop() : '';

    if (!title || !title.trim()) {
      // No title — use file name, then project name
      return fileName || projectName || 'Unknown';
    }
    // If title is just an IDE name, show "IDE - fileName" or "IDE - projectName"
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

  // ---------------- PRODUCTIVITY ----------------
  const calculateProductivity = () => {
    // Use trackedTime (sum of activity durations) as denominator
    const totalSec = trackedTime || totalTime;

    // Productive = productive + server + browser (all 100%)
    const productiveSec =
      (categoryBreakdown.productive?.duration || 0) +
      (categoryBreakdown.server?.duration || 0) +
      (categoryBreakdown.browser?.duration || 0);

    // Only show productivity if > 2 hours of total activity
    const minActiveSeconds = 2 * 3600;
    const score = totalSec > minActiveSeconds
      ? Math.min(100, Math.round((productiveSec / totalSec) * 100))
      : 0;

    const categoryList = Object.entries(categoryBreakdown).map(([name, d]) => ({
      name,
      time: d.duration_hours,
      percentage: d.percentage,
    }));

    return { score, categories: categoryList.filter((c) => c.time > 0) };
  };

  
  const productivity = calculateProductivity();

  // ---------------- PIE CHART ----------------
  const pieData = {
    labels: productivity.categories.map((c) => c.name),
    datasets: [
      {
        data: productivity.categories.map((c) => c.time),
        backgroundColor: [
          "#10b981",
          "#3b82f6",
          "#6366f1",
          "#f59e0b",
          "#ef4444",
          "#8b5cf6",
        ],
      },
    ],
  };

  const formatActivityDate = (value) => {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d.getTime())) return "";
  return format(d, "dd MMM yyyy");
};

  // ---------------- UI ----------------
  return (
    <div className="developer-dashboard">

      {/* HEADER */}
      <div className="dev-dashboard-header">
        {onBack && (
          <button onClick={onBack} className="back-button">
            <ArrowLeft size={16} /> Back
          </button>
        )}

        <h1>{developer ? `${developer.name}'s Dashboard` : "Dashboard"}</h1>

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

      {/* STATS */}
      <div className="stats-grid">
        <div className="stat-card">
          <Clock size={32} />
          <h3>Total Time</h3>
          <p>{formatTime(totalTime)}</p> {/* REAL WORK HOURS DISPLAY */}
        </div>

        <div className="stat-card">
          <Activity size={32} />
          <h3>Work Activity</h3>
          <p>{productivity.score}%</p>
        </div>

        <div className="stat-card">
          <RefreshCw size={32} />
          <h3>Last Updated</h3>
          <p>{lastUpdated ? format(lastUpdated, "MMM d, yyyy HH:mm") : "Never"}</p>
        </div>
      </div>

      {/* PIE CHART */}
      {!loading && productivity.categories.length > 0 && (
        <div className="category-pie-chart">
          <h3>Category Breakdown</h3>

          <div className="chart-flex-wrapper">
            <div className="chart-big">
              <Pie data={pieData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>

            <div className="chart-legend">
              {productivity.categories.map((cat, i) => (
                <div key={i} className="legend-item">
                  <span className="legend-color" style={{ background: pieData.datasets[0].backgroundColor[i] }} />
                  <span>{cat.name}</span>
                  <span>{cat.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CATEGORY DETAILS */}
      {!loading && productivity.categories.length > 0 && (
        <div className="category-details">
          <h3>Category Details</h3>

          <div className="category-tabs">
            <div className="tab-headers">
              {productivity.categories.map((cat, i) => (
                <button
                  key={i}
                  className={`tab-header ${selectedTab === i ? "active" : ""}`}
                  onClick={() => setSelectedTab(i)}
                >
                  <span>{cat.name}</span>
                  <span>{cat.percentage.toFixed(1)}%</span>
                </button>
              ))}
            </div>

            <div className="tab-content">
              {(groupedActivities[productivity.categories[selectedTab].name] || []).length > 0 ? (
                <div className="category-activity-list">
                  <h4>Activities in this category</h4>

                  <div className="activity-scroll">
                    {(groupedActivities[productivity.categories[selectedTab].name] || [])
                      .sort((a, b) => b.duration - a.duration)
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
                              {act.project_name && <span> • {act.project_name}</span>}
                              {act.activity_count > 1 && <span> • {act.activity_count} times</span>}
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
                    <span className={`category-badge category-${act.category}`}>{act.category}</span>
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
