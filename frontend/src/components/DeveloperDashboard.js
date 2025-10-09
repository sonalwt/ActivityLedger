import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DatePicker from 'react-datepicker';
import { format, startOfDay, endOfDay } from 'date-fns';
import 'react-datepicker/dist/react-datepicker.css';

function DeveloperDashboard({ developer }) {
  const [activityData, setActivityData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(startOfDay(new Date()));
  const [endDate, setEndDate] = useState(endOfDay(new Date()));
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const fetchActivityData = async () => {
    if (!developer) return;
    setLoading(true);
    try {
      const developerId = developer.id || developer.developer_id;

      const res = await axios.get(`${API_BASE}/activity-data/${developerId}`, {
        params: { start_date: startDate.toISOString(), end_date: endDate.toISOString() }
      });

      setActivityData(res.data.data || []);
      setCategoryBreakdown(res.data.category_breakdown || null);

    } catch (error) {
      console.error("Error fetching activity data:", error);
      setActivityData([]);
      setCategoryBreakdown(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivityData();
  }, [startDate, endDate, developer]);

  return (
    <div>
      <h2>{developer?.name || 'Developer'} Dashboard</h2>
      <div>
        <DatePicker selected={startDate} onChange={setStartDate} selectsStart startDate={startDate} endDate={endDate} />
        <DatePicker selected={endDate} onChange={setEndDate} selectsEnd startDate={startDate} endDate={endDate} minDate={startDate} />
      </div>

      {loading && <p>Loading...</p>}

      {!loading && (
        <div>
          <h3>Activity Data</h3>
          <pre>{JSON.stringify(activityData, null, 2)}</pre>

          <h3>Category Breakdown</h3>
          <pre>{JSON.stringify(categoryBreakdown, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default DeveloperDashboard;
