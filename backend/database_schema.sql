-- Sample table structure for activity_records
-- This is for reference if you need to create the table manually

CREATE TABLE IF NOT EXISTS activity_records (
    id SERIAL PRIMARY KEY,
    developer_id INTEGER NOT NULL,
    app VARCHAR(255),
    title TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration INTEGER DEFAULT 0,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_developer_id ON activity_records(developer_id);
CREATE INDEX idx_timestamp ON activity_records(timestamp);
CREATE INDEX idx_developer_timestamp ON activity_records(developer_id, timestamp);

-- Sample data insertion (for testing)
/*
INSERT INTO activity_records (developer_id, app, title, timestamp, duration) VALUES
(1, 'Code.exe', 'timesheet_new - Visual Studio Code', NOW() - INTERVAL '1 hour', 1800),
(1, 'chrome.exe', 'AWS EC2 Dashboard - Google Chrome', NOW() - INTERVAL '2 hours', 600),
(1, 'chrome.exe', 'GitHub - timesheet project - Google Chrome', NOW() - INTERVAL '3 hours', 900),
(1, 'slack.exe', 'Slack - Team Channel', NOW() - INTERVAL '4 hours', 300);
*/

-- Query to check activity distribution
/*
SELECT 
    developer_id,
    app,
    COUNT(*) as activity_count,
    SUM(duration) as total_duration,
    AVG(duration) as avg_duration
FROM activity_records
WHERE DATE(timestamp) = CURRENT_DATE
GROUP BY developer_id, app
ORDER BY developer_id, total_duration DESC;
*/

-- Query to get daily productivity summary
/*
SELECT 
    developer_id,
    DATE(timestamp) as activity_date,
    COUNT(DISTINCT app) as unique_apps,
    COUNT(*) as total_activities,
    SUM(duration) / 3600.0 as total_hours
FROM activity_records
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY developer_id, DATE(timestamp)
ORDER BY developer_id, activity_date DESC;
*/
