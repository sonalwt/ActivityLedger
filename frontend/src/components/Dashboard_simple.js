// Simple fallback Dashboard that works with your existing system
import React, { useState, useEffect } from 'react';
import { Clock, Activity, RefreshCw, User, AlertCircle } from 'lucide-react';
import ActivityChart from './ActivityChart';
import ActivityTable from './ActivityTable';

const Dashboard = () => {
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [totalTime, setTotalTime] = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  const API_BASE = 'https://api-timesheet.firsteconomy.com';

  useEffect(() => {
    fetchActivityData();
  }, []);

  const fetchActivityData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      
      // Try new API first
      let response = await fetch(`${API_BASE}/developers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('New API works:', data);
        
        if (data.developers && data.developers.length > 0) {
          const developer = data.developers[0];
          
          // Get activity data for the developer
          const activityResponse = await fetch(
            `${API_BASE}/activity-data/${developer.id}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            }
          );
          
          if (activityResponse.ok) {
            const activityResult = await activityResponse.json();
            setActivityData(activityResult.data || []);
            setTotalTime(activityResult.total_time || 0);
            setLastUpdated(new Date());
          }
        }
      } else {
        // Fallback to old API
        console.log('Trying fallback API...');
        response = await fetch(`${API_BASE}/activity-data`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          setActivityData(data.data || []);
          setTotalTime(data.total_time || 0);
          setLastUpdated(new Date());
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      }
    } catch (error) {
      console.error('Error fetching activity data:', error);
      setError(`Failed to load activity data: ${error.message}`);
    }
    setLoading(false);
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
            <User className="text-blue-600" />
            Personal Dashboard
          </h1>
          
          <div className="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-700">
            Local Mode
          </div>
        </div>

        <button
          onClick={fetchActivityData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg border border-blue-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle size={20} className="text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-red-800 font-medium">Error</h4>
            <p className="text-red-700 text-sm">{error}</p>
            <p className="text-red-600 text-xs mt-1">
              Make sure your backend is running and ActivityWatch is started
            </p>
          </div>
        </div>
      )}

      {/* User Info */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <User size={20} className="text-blue-600" />
          Your Activity - Ankita-TechTeam
        </h3>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-800 text-sm">
            ✅ <strong>Local Mode Active:</strong> Showing only your activity data
          </p>
          <p className="text-blue-700 text-xs mt-1">
            Environment: Local | Developer: Ankita-TechTeam
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <RefreshCw size={64} className="mx-auto text-blue-600 mb-6 animate-spin" />
          <h3 className="text-xl font-semibold text-gray-700 mb-4">Loading Your Activity Data...</h3>
          <p className="text-gray-600">
            Connecting to ActivityWatch and loading your timesheet data...
          </p>
        </div>
      )}

      {/* Activity Data */}
      {!loading && activityData.length > 0 && (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Time Today</p>
                  <p className="text-2xl font-bold text-blue-600">{formatTime(totalTime)}</p>
                </div>
                <Clock className="h-8 w-8 text-blue-600" />
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Activities</p>
                  <p className="text-2xl font-bold text-green-600">{activityData.length}</p>
                </div>
                <Activity className="h-8 w-8 text-green-600" />
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Last Updated</p>
                  <p className="text-sm text-gray-700">
                    {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Never'}
                  </p>
                </div>
                <RefreshCw className="h-8 w-8 text-orange-600" />
              </div>
            </div>
          </div>

          {/* Charts and Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Activity Distribution</h3>
              <ActivityChart data={activityData} />
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Top Activities</h3>
              <ActivityTable data={activityData.slice(0, 10)} formatTime={formatTime} />
            </div>
          </div>
        </div>
      )}

      {/* No Data State */}
      {!loading && activityData.length === 0 && !error && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <Activity size={64} className="mx-auto text-gray-400 mb-6" />
          <h3 className="text-xl font-semibold text-gray-700 mb-4">No Activity Data Found</h3>
          <p className="text-gray-600 mb-6">
            Make sure ActivityWatch is running and tracking your activity.
          </p>
          <button
            onClick={fetchActivityData}
            className="px-6 py-3 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
