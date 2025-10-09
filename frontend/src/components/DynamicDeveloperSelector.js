import React, { useEffect, useState } from "react";
import axios from "axios";

function Dashboard() {
  const [activities, setActivities] = useState([]);

  const fetchActivities = async () => {
    try {
      const res = await axios.get("http://localhost:8000/activities");
      setActivities(res.data);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div>
      <button onClick={fetchActivities}>View Dashboard</button>

      <table border="1" cellPadding="5">
        <thead>
          <tr>
            <th>Developer ID</th>
            <th>Activity Details</th>
            <th>Category</th>
            <th>Start Time</th>
            <th>End Time</th>
          </tr>
        </thead>
        <tbody>
          {activities.map((rec, index) => (
            <tr key={index}>
              <td>{rec.developer_id}</td>
              <td>
                {Object.entries(rec.activity_data).map(([k, v]) => (
                  <div key={k}>
                    <strong>{k}:</strong> {v}
                  </div>
                ))}
              </td>
              <td>{rec.category}</td>
              <td>{rec.start_time}</td>
              <td>{rec.end_time}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Dashboard;
