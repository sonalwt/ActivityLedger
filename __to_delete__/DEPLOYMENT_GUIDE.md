# 🚀 AWS EC2 Deployment Guide - Multi-Developer Timesheet Portal

## 🎯 Overview

This guide will help you deploy your timesheet application to AWS EC2 and set up a system to collect ActivityWatch data from multiple developer machines into a centralized portal.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer 1   │    │   Developer 2   │    │   Developer N   │
│  (Local AW)     │    │  (Local AW)     │    │  (Local AW)     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │AW Data Sync │ │    │ │AW Data Sync │ │    │ │AW Data Sync │ │
│ │   Script    │ │    │ │   Script    │ │    │ │   Script    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTPS POST           │ HTTPS POST           │ HTTPS POST
          │ (Activity Data)      │ (Activity Data)      │ (Activity Data)
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AWS EC2 Instance                         │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   React App     │  │  FastAPI Backend│  │  PostgreSQL     │ │
│  │  (Port 3000)    │  │   (Port 8000)   │  │   Database      │ │
│  │                 │  │                 │  │                 │ │
│  │ Team Dashboard  │◄─┤ Multi-Dev API   │◄─┤ Activity Data   │ │
│  │ Developer Views │  │ Authentication  │  │ Developer Info  │ │
│  │ Analytics       │  │ Data Processing │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Domain Name   │
                        │  (Optional)     │
                        │ SSL Certificate │
                        └─────────────────┘
```

## 📋 Prerequisites

### AWS Account Setup
1. **AWS Account**: Active AWS account with EC2 access
2. **Key Pair**: Create an EC2 key pair for SSH access
3. **Security Group**: Configure security group for web traffic
4. **Domain** (Optional): Domain name for custom URL

### Local Requirements
- Node.js 16+ and npm
- Python 3.8+
- Git
- SSH client

## 🛠️ Step 1: Launch and Configure EC2 Instance

### 1.1 Launch EC2 Instance
```bash
# Instance Configuration:
- AMI: Ubuntu 22.04 LTS
- Instance Type: t3.medium (2 vCPU, 4GB RAM minimum)
- Storage: 30GB gp3 SSD
- Security Group: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API)
```

### 1.2 Configure Security Group
```bash
# Inbound Rules:
Type            Protocol    Port Range    Source
SSH             TCP         22           Your IP
HTTP            TCP         80           0.0.0.0/0
HTTPS           TCP         443          0.0.0.0/0
Custom TCP      TCP         8000         0.0.0.0/0  # FastAPI Backend
Custom TCP      TCP         3000         0.0.0.0/0  # React Dev (temporary)
Custom TCP      TCP         5432         Your IP    # PostgreSQL (for admin)
```

### 1.3 Connect to Instance
```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Update system
sudo apt update && sudo apt upgrade -y
```

## 🔧 Step 2: Install Required Software

### 2.1 Install Node.js
```bash
# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

### 2.2 Install Python and Dependencies
```bash
# Python 3.10 is usually pre-installed on Ubuntu 22.04
sudo apt install python3-pip python3-venv python3-dev -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Nginx (reverse proxy)
sudo apt install nginx -y

# Install PM2 for process management
sudo npm install -g pm2

# Install Git
sudo apt install git -y
```

### 2.3 Configure PostgreSQL
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE timesheet;
CREATE USER timesheet_user WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE timesheet TO timesheet_user;
\\q

# Test connection
psql -h localhost -U timesheet_user -d timesheet
```

## 📁 Step 3: Deploy Application

### 3.1 Clone and Setup Backend
```bash
# Create app directory
sudo mkdir -p /var/www/timesheet
sudo chown ubuntu:ubuntu /var/www/timesheet
cd /var/www/timesheet

# Clone repository
git clone your-repo-url .

# Setup Python virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r ../requirements.txt

# Create production environment file
cp ../.env.example .env

# Edit .env file
nano .env
```

### 3.2 Production Environment Configuration
```env
# Production .env file
DATABASE_URL=postgresql://timesheet_user:secure_password_123@localhost:5432/timesheet
SECRET_KEY=your-super-long-secret-key-for-production-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ActivityWatch - Not used in production (receiving data from remote systems)
ACTIVITYWATCH_HOST=http://localhost:5600

# Admin settings
ADMIN_TOKEN=your-admin-token-for-developer-registration

# CORS settings for production
FRONTEND_URL=https://your-domain.com  # or http://your-ec2-ip:3000
```

### 3.3 Setup Frontend
```bash
# Navigate to frontend
cd /var/www/timesheet/frontend

# Install dependencies
npm install

# Create production build
npm run build

# The build files are now in 'build' directory
```

## 🌐 Step 4: Configure Nginx Reverse Proxy

### 4.1 Create Nginx Configuration
```bash
# Create site configuration
sudo nano /etc/nginx/sites-available/timesheet
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your EC2 public IP

    # Frontend - serve React build files
    location / {
        root /var/www/timesheet/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # Backend API - proxy to FastAPI
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Direct backend access (optional, for API documentation)
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4.2 Enable Site
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/timesheet /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔄 Step 5: Setup Process Management with PM2

### 5.1 Create Backend Start Script
```bash
# Create startup script
nano /var/www/timesheet/start_backend.sh
```

```bash
#!/bin/bash
cd /var/www/timesheet/backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

```bash
# Make executable
chmod +x /var/www/timesheet/start_backend.sh
```

### 5.2 Setup PM2
```bash
# Start backend with PM2
cd /var/www/timesheet
pm2 start start_backend.sh --name "timesheet-backend"

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup ubuntu
# Follow the instructions provided by PM2

# Check status
pm2 status
pm2 logs timesheet-backend
```

## 🔐 Step 6: SSL Certificate (Optional but Recommended)

### 6.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 6.2 Get SSL Certificate
```bash
# Replace with your domain
sudo certbot --nginx -d your-domain.com

# Follow the prompts to set up automatic renewal
sudo certbot renew --dry-run
```

## 👥 Step 7: Setup Multi-Developer System

### 7.1 Add Multi-Developer API Routes

Create new file: `/var/www/timesheet/backend/multi_developer_api.py`

```python
# Use the content from the AWS_DEPLOYMENT_GUIDE.md file we created earlier
# This includes endpoints for:
# - /receive-activity-data
# - /register-developer  
# - /developers
# - /developer-summary/{developer_id}
# - /team-dashboard
```

### 7.2 Update Main FastAPI App
```python
# Add to main.py
from multi_developer_api import router as multi_dev_router

app.include_router(multi_dev_router, prefix="/api/v1", tags=["multi-developer"])
```

### 7.3 Database Migration
```bash
# Update database schema
cd /var/www/timesheet/backend
source venv/bin/activate

# Create migration script
nano add_developer_support.py
```

```python
from database import engine
from sqlalchemy import text

# Add developer table and update activity_records
with engine.connect() as conn:
    # Create developers table
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS developers (
            id SERIAL PRIMARY KEY,
            developer_id VARCHAR UNIQUE,
            name VARCHAR,
            email VARCHAR,
            active BOOLEAN DEFAULT TRUE,
            api_token VARCHAR UNIQUE,
            created_at TIMESTAMP DEFAULT NOW(),
            last_sync TIMESTAMP
        )
    '''))
    
    # Add developer_id column to activity_records
    conn.execute(text('''
        ALTER TABLE activity_records 
        ADD COLUMN IF NOT EXISTS developer_id VARCHAR
    '''))
    
    # Create index
    conn.execute(text('''
        CREATE INDEX IF NOT EXISTS idx_activity_records_developer_id 
        ON activity_records(developer_id)
    '''))
    
    conn.commit()
    print("Database migration completed successfully!")
```

```bash
# Run migration
python add_developer_support.py

# Restart backend
pm2 restart timesheet-backend
```

## 💻 Step 8: Developer Machine Setup

### 8.1 Create ActivityWatch Sync Script

Create this script on each developer's machine:

```python
# save as: sync_activitywatch.py
import requests
import json
from datetime import datetime, timedelta, timezone
import time
import os
from dotenv import load_dotenv
import schedule
import logging

load_dotenv()

# Configuration
SERVER_URL = "https://your-timesheet-server.com/api/v1"  # Your EC2 URL
DEVELOPER_ID = os.getenv("DEVELOPER_ID", "dev001")  # Unique ID for this developer
API_TOKEN = os.getenv("API_TOKEN", "your-api-token")  # Token from server registration
ACTIVITYWATCH_HOST = "http://localhost:5600"

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActivityWatchSyncer:
    def __init__(self):
        self.aw_api_url = f"{ACTIVITYWATCH_HOST}/api/0"
        self.server_url = SERVER_URL
        self.headers = {
            "Developer-ID": DEVELOPER_ID,
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def get_local_activity_data(self, start_time, end_time):
        """Get activity data from local ActivityWatch"""
        try:
            # Get buckets
            buckets_response = requests.get(f"{self.aw_api_url}/buckets/")
            buckets_response.raise_for_status()
            buckets = buckets_response.json()
            
            activities = []
            
            for bucket_name, bucket_info in buckets.items():
                if 'afk' in bucket_name.lower():
                    continue
                
                # Get events from this bucket
                params = {
                    'start': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'end': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'limit': 5000
                }
                
                events_response = requests.get(
                    f"{self.aw_api_url}/buckets/{bucket_name}/events",
                    params=params
                )
                events_response.raise_for_status()
                events = events_response.json()
                
                for event in events:
                    data = event.get('data', {})
                    duration = event.get('duration', 0)
                    
                    if duration < 5:  # Skip very short activities
                        continue
                    
                    activity = {
                        "application_name": data.get('app', data.get('application', 'Unknown')),
                        "window_title": data.get('title', ''),
                        "duration": duration,
                        "timestamp": event.get('timestamp', ''),
                        "bucket_name": bucket_name,
                        "developer_id": DEVELOPER_ID
                    }
                    
                    activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting local ActivityWatch data: {e}")
            return []
    
    def send_to_server(self, activities):
        """Send activities to central server"""
        if not activities:
            logger.info("No activities to send")
            return True
        
        payload = {
            "developer_id": DEVELOPER_ID,
            "activities": activities,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/receive-activity-data",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Successfully sent {len(activities)} activities to server")
            logger.info(f"Server response: {result.get('message', 'No message')}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending data to server: {e}")
            return False
    
    def sync_recent_data(self, hours_back=1):
        """Sync recent activity data"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        logger.info(f"Syncing data from {start_time} to {end_time}")
        
        # Get local data
        activities = self.get_local_activity_data(start_time, end_time)
        
        if activities:
            # Send to server
            success = self.send_to_server(activities)
            return success
        else:
            logger.info("No activities found to sync")
            return True
    
    def test_connection(self):
        """Test connection to both ActivityWatch and server"""
        # Test ActivityWatch
        try:
            aw_response = requests.get(f"{self.aw_api_url}/buckets/", timeout=5)
            aw_status = aw_response.status_code == 200
            logger.info(f"ActivityWatch connection: {'✓' if aw_status else '✗'}")
        except:
            aw_status = False
            logger.error("ActivityWatch connection: ✗")
        
        # Test server
        try:
            server_response = requests.get(f"{self.server_url}/health", timeout=5)
            server_status = server_response.status_code == 200
            logger.info(f"Server connection: {'✓' if server_status else '✗'}")
        except:
            server_status = False
            logger.error("Server connection: ✗")
        
        return aw_status and server_status

def main():
    syncer = ActivityWatchSyncer()
    
    # Test connections
    if not syncer.test_connection():
        logger.error("Connection test failed. Please check configuration.")
        return
    
    # Schedule regular syncing
    schedule.every(30).minutes.do(lambda: syncer.sync_recent_data(1))
    schedule.every().hour.do(lambda: syncer.sync_recent_data(2))
    
    # Initial sync
    syncer.sync_recent_data(24)  # Sync last 24 hours
    
    logger.info("ActivityWatch Syncer started. Running every 30 minutes...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
```

### 8.2 Developer Machine Environment
```bash
# Create .env file on developer machine
DEVELOPER_ID=dev001  # Unique identifier for this developer
API_TOKEN=your-api-token-from-server-registration
```

### 8.3 Install and Run Sync Script
```bash
# Install dependencies
pip install requests python-dotenv schedule

# Run the sync script
python sync_activitywatch.py

# Or run as a service (Windows)
# Use Task Scheduler to run the script on startup

# Or run as a service (Linux/Mac)
# Create systemd service or use cron
```

## 🎨 Step 9: Update Frontend for Multi-Developer Support

### 9.1 Add Team Dashboard Components

Create new React components for team management:

```javascript
// src/components/TeamDashboard.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TeamDashboard = () => {
    const [teamData, setTeamData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [dateRange, setDateRange] = useState({
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0]
    });

    const fetchTeamData = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/v1/team-dashboard', {
                params: dateRange
            });
            setTeamData(response.data.team_data || []);
        } catch (error) {
            console.error('Error fetching team data:', error);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchTeamData();
    }, [dateRange]);

    return (
        <div className="team-dashboard">
            <h2>Team Productivity Dashboard</h2>
            
            <div className="date-controls">
                <input
                    type="date"
                    value={dateRange.start_date}
                    onChange={(e) => setDateRange({...dateRange, start_date: e.target.value})}
                />
                <input
                    type="date"
                    value={dateRange.end_date}
                    onChange={(e) => setDateRange({...dateRange, end_date: e.target.value})}
                />
                <button onClick={fetchTeamData}>Update</button>
            </div>

            {loading ? (
                <p>Loading team data...</p>
            ) : (
                <div className="developers-grid">
                    {teamData.map(developer => (
                        <DeveloperCard 
                            key={developer.developer_id} 
                            developer={developer} 
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

const DeveloperCard = ({ developer }) => {
    const { name, summary, last_sync } = developer;
    
    return (
        <div className="developer-card">
            <h3>{name}</h3>
            <div className="stats">
                <p>Total Time: {summary?.total_time_formatted || '0h'}</p>
                <p>Activities: {summary?.total_activities || 0}</p>
                <p>Last Sync: {last_sync ? new Date(last_sync).toLocaleString() : 'Never'}</p>
            </div>
            
            <div className="categories">
                {summary?.categories && Object.entries(summary.categories).map(([category, data]) => (
                    <div key={category} className="category">
                        <span>{category}: </span>
                        <span>{(data.duration / 3600).toFixed(1)}h</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TeamDashboard;
```

### 9.2 Update Main App Routes

```javascript
// src/App.js - Add team route
import TeamDashboard from './components/TeamDashboard';

// Add to your routes:
<Route path="/team" element={<TeamDashboard />} />
```

## 🔧 Step 10: Testing and Monitoring

### 10.1 Test the System
```bash
# Test server health
curl https://your-domain.com/api/v1/health

# Test developer registration (replace with actual admin token)
curl -X POST https://your-domain.com/api/v1/register-developer \
  -H "Admin-Token: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev001",
    "name": "John Doe",
    "email": "john@company.com"
  }'

# Test activity data reception
curl -X POST https://your-domain.com/api/v1/receive-activity-data \
  -H "Developer-ID: dev001" \
  -H "Authorization: Bearer your-api-token" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "dev001",
    "activities": [...],
    "timestamp": "2025-01-01T00:00:00Z"
  }'
```

### 10.2 Setup Monitoring
```bash
# Monitor logs
pm2 logs timesheet-backend

# Monitor system resources
htop

# Monitor Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Monitor PostgreSQL
sudo -u postgres psql -d timesheet -c "SELECT COUNT(*) FROM activity_records;"
```

## 🔒 Step 11: Security and Backup

### 11.1 Security Hardening
```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Secure PostgreSQL
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Ensure only local connections are allowed

# Regular security updates
sudo apt update && sudo apt upgrade -y
```

### 11.2 Setup Automated Backups
```bash
# Create backup script
sudo nano /usr/local/bin/backup_timesheet.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/timesheet"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="timesheet"
DB_USER="timesheet_user"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Application backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz -C /var/www timesheet

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable and schedule
sudo chmod +x /usr/local/bin/backup_timesheet.sh

# Add to crontab (daily backup at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup_timesheet.sh
```

## 📊 Step 12: Going Live Checklist

### 12.1 Pre-Launch Checklist
- [ ] EC2 instance properly configured and secured
- [ ] PostgreSQL database set up with proper user permissions
- [ ] Nginx reverse proxy configured and running
- [ ] SSL certificate installed (if using custom domain)
- [ ] PM2 process management configured
- [ ] Backend API endpoints tested
- [ ] Frontend builds and serves correctly
- [ ] Multi-developer API endpoints working
- [ ] Developer sync scripts tested on at least one machine
- [ ] Database backups configured
- [ ] Monitoring and logging in place

### 12.2 Post-Launch Tasks
1. **Register all developers** using the `/register-developer` endpoint
2. **Distribute API tokens** to all developers securely
3. **Install sync scripts** on all developer machines
4. **Test data flow** from at least one developer machine
5. **Monitor logs** for first 24-48 hours
6. **Verify data accuracy** by comparing local AW data with server data
7. **Train team** on using the new centralized dashboard

## 🎯 Benefits After Deployment

### For Management
- **Centralized View**: See all developers' productivity in one dashboard
- **Real-time Insights**: Up-to-date activity data every 30 minutes
- **Team Analytics**: Compare productivity across team members
- **Project Tracking**: Understand time allocation across projects

### For Developers
- **No Manual Tracking**: Automatic time tracking with ActivityWatch
- **Privacy Maintained**: Raw data stays on local machines, only processed metrics sent
- **Personal Analytics**: Individual productivity insights
- **No Disruption**: Works silently in the background

### Technical Benefits
- **Scalable**: Easily add new developers
- **Secure**: Token-based authentication and HTTPS
- **Reliable**: PM2 process management and automated backups
- **Cost-effective**: Single EC2 instance can handle 10-20 developers

## 🔧 Troubleshooting Common Issues

### Backend Not Starting
```bash
# Check logs
pm2 logs timesheet-backend

# Check database connection
cd /var/www/timesheet/backend
source venv/bin/activate
python -c "from database import engine; print('DB connection:', engine.connect())"
```

### Frontend Not Loading
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx configuration
sudo nginx -t

# Rebuild frontend
cd /var/www/timesheet/frontend
npm run build
```

### Developer Sync Issues
```bash
# On developer machine, check:
# 1. ActivityWatch is running (localhost:5600)
# 2. Network connectivity to server
# 3. Correct API token and developer ID
# 4. Check sync script logs
```

This comprehensive guide will help you deploy a fully functional multi-developer timesheet system that automatically collects ActivityWatch data from team members' machines into a centralized productivity dashboard on AWS EC2.
