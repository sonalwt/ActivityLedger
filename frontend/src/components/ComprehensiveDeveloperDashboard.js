// Comprehensive Developer Dashboard - Shows everything in one view
import React, { useState, useEffect } from 'react';
import { 
  Activity, Clock, TrendingUp, Briefcase, Calendar, BarChart2, 
  ArrowLeft, RefreshCw, Monitor, Code, Database, Globe, FileText,
  CheckCircle, AlertCircle
} from 'lucide-react';
import { format } from 'date-fns';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

const ComprehensiveDeveloperDashboard = ({ developer, onBack }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [startDate, setStartDate] = useState(new Date(new Date().setDate(new Date().getDate() - 7)));
  const [endDate, setEndDate] = useState(new Date());
  
  // All data states
  const [productivityData, setProductivityData] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [activityData, setActivityData] = useState([]);
  
  const API_BASE = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

  useEffect(() => {
    fetchAllData();
  }, [developer, startDate, endDate]);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      
      const params = new URLSearchParams({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });

      // Fetch all data in parallel
      const [productivityRes, projectRes, activityRes] = await Promise.all([
        fetch(`${API_BASE}/api/developer/${developer.developer_id || developer.id}/productivity-hours?${params}`, { headers }),
        fetch(`${API_BASE}/api/developer/${developer.developer_id || developer.id}/project-breakdown?${params}`, { headers }),
        fetch(`${API_BASE}/activity-data/${developer.id}?${params}`, { headers })
      ]);

      if (!productivityRes.ok || !projectRes.ok || !activityRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [productivity, projects, activities] = await Promise.all([
        productivityRes.json(),
        projectRes.json(),
        activityRes.json()
      ]);

      setProductivityData(productivity);
      setProjectData(projects);
      setActivityData(activities.data || []);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getAppIcon = (appName) => {
    const app = appName?.toLowerCase() || '';
    if (app.includes('code') || app.includes('visual studio') || app.includes('cursor')) return <Code className="w-4 h-4" />;
    if (app.includes('chrome') || app.includes('firefox') || app.includes('browser')) return <Globe className="w-4 h-4" />;
    if (app.includes('database') || app.includes('mysql') || app.includes('postgres')) return <Database className="w-4 h-4" />;
    if (app.includes('word') || app.includes('docs') || app.includes('excel')) return <FileText className="w-4 h-4" />;
    return <Monitor className="w-4 h-4" />;
  };

  const getProjectColor = (index) => {
    const colors = [
      'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500',
      'bg-pink-500', 'bg-teal-500', 'bg-indigo-500', 'bg-red-500'
    ];
    return colors[index % colors.length];
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">Loading Dashboard...</h3>
          <p className="text-gray-500 mt-1">Fetching productivity metrics and project data</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
            <p className="text-red-800">Error loading dashboard: {error}</p>
          </div>
          <button
            onClick={fetchAllData}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const { overall_stats, daily_productivity, top_applications } = productivityData || {};
  const { projects, summary } = projectData || {};

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          {onBack && (
            <button
              onClick={onBack}
              className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
          )}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{developer.name}'s Complete Dashboard</h1>
            <p className="text-gray-500 mt-1">Comprehensive productivity and project analysis</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg shadow-sm">
            <Calendar className="w-4 h-4 text-gray-400" />
            <DatePicker
              selected={startDate}
              onChange={setStartDate}
              selectsStart
              startDate={startDate}
              endDate={endDate}
              className="text-sm border-0 focus:ring-0"
              dateFormat="MMM d, yyyy"
            />
            <span className="text-gray-400">to</span>
            <DatePicker
              selected={endDate}
              onChange={setEndDate}
              selectsEnd
              startDate={startDate}
              endDate={endDate}
              minDate={startDate}
              className="text-sm border-0 focus:ring-0"
              dateFormat="MMM d, yyyy"
            />
          </div>
          <button
            onClick={fetchAllData}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Hours</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{overall_stats?.total_work_hours || 0}h</p>
              <p className="text-xs text-gray-500 mt-1">Last 7 days</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Productivity</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{overall_stats?.productivity_percentage || 0}%</p>
              <p className="text-xs text-gray-500 mt-1">{overall_stats?.total_productive_hours || 0}h productive</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Projects</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">{summary?.total_projects || 0}</p>
              <p className="text-xs text-gray-500 mt-1">Active projects</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Briefcase className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Daily Average</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">{overall_stats?.average_daily_hours || 0}h</p>
              <p className="text-xs text-gray-500 mt-1">Per working day</p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <BarChart2 className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Projects and Daily Productivity */}
        <div className="lg:col-span-1 space-y-6">
          {/* Project Breakdown */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-purple-600" />
              Project Distribution
            </h3>
            <div className="space-y-3">
              {projects?.slice(0, 5).map((project, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{project.project_name}</span>
                    <span className="text-sm text-gray-500">{project.total_hours}h</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${getProjectColor(index)} h-2 rounded-full transition-all duration-300`}
                      style={{ width: `${project.percentage}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-500">{project.days_worked} days</span>
                    <span className="text-xs font-medium text-gray-600">{project.percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Daily Productivity Trend */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Daily Productivity
            </h3>
            <div className="space-y-3">
              {daily_productivity?.slice(0, 7).map((day, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">
                      {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </span>
                    <span className="text-sm text-gray-600">{day.total_hours}h</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        day.productivity_percentage >= 80 ? 'bg-green-500' :
                        day.productivity_percentage >= 60 ? 'bg-yellow-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${day.productivity_percentage}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {day.productive_hours}h productive ({day.productivity_percentage}%)
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column - Top Applications and Activities */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top Applications */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Monitor className="w-5 h-5 text-indigo-600" />
              Top Applications
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {top_applications?.slice(0, 10).map((app, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    {getAppIcon(app.application)}
                    <div>
                      <p className="text-sm font-medium text-gray-900">{app.application}</p>
                      <p className="text-xs text-gray-500">{app.category}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{app.hours}h</p>
                    <div className="flex items-center gap-1">
                      {app.is_productive ? (
                        <CheckCircle className="w-3 h-3 text-green-500" />
                      ) : (
                        <AlertCircle className="w-3 h-3 text-gray-400" />
                      )}
                      <span className="text-xs text-gray-500">{app.usage_count} uses</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activities by Project */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-600" />
              Recent Activities by Project
            </h3>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {projects?.map((project, projectIndex) => {
                const projectActivities = activityData.filter(a => a.project_name === project.project_name).slice(0, 5);
                if (projectActivities.length === 0) return null;
                
                return (
                  <div key={projectIndex} className="border-l-4 pl-4" style={{ borderColor: getProjectColor(projectIndex).replace('bg-', '#').replace('500', '') }}>
                    <h4 className="font-medium text-gray-900 mb-2">{project.project_name}</h4>
                    <div className="space-y-2">
                      {projectActivities.map((activity, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            {getAppIcon(activity.application_name)}
                            <span className="text-gray-700">{(activity.window_title || activity.file_path?.split(/[/\\]/).pop() || 'Unknown')?.slice(0, 50)}...</span>
                          </div>
                          <span className="text-gray-500">{(activity.duration / 3600).toFixed(1)}h</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Activity Log */}
      <div className="mt-6 bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-gray-600" />
          Detailed Activity Log
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Application</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Activity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {activityData.slice(0, 20).map((activity, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      activity.project_name ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {activity.project_name || 'Unassigned'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center gap-2">
                      {getAppIcon(activity.application_name)}
                      {activity.application_name}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-md truncate">
                    {activity.window_title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {(activity.duration / 3600).toFixed(2)}h
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ComprehensiveDeveloperDashboard;
