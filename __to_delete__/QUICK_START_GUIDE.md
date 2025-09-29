# 🚀 Multi-Developer Timesheet System - Quick Start Guide

## 🎯 Overview

Transform your single-user timesheet into a **centralized team productivity portal** that automatically collects ActivityWatch data from multiple developer machines.

## 📋 What You'll Build

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer 1   │    │   Developer 2   │    │   Developer N   │
│  ActivityWatch  │    │  ActivityWatch  │    │  ActivityWatch  │
│   + Sync Tool   │    │   + Sync Tool   │    │   + Sync Tool   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ Automatic Sync       │ Automatic Sync       │
          │ Every 30 min         │ Every 30 min         │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     AWS EC2 Server      │
                    │                         │
                    │  📊 Team Dashboard      │
                    │  📈 Productivity Metrics│
                    │  📋 Individual Reports  │
                    │  🎯 Project Tracking    │
                    └─────────────────────────┘
```

## 🏗️ Architecture Components

### Server Side (AWS EC2)
- **FastAPI Backend**: Multi-developer API endpoints
- **PostgreSQL Database**: Centralized activity storage
- **React Frontend**: Team dashboard and individual views
- **Nginx**: Reverse proxy and SSL termination

### Client Side (Developer Machines)
- **ActivityWatch**: Local activity tracking (existing)
- **Sync Client**: Python script that sends data to server
- **Automatic Service**: Runs continuously in background

## 🚀 Deployment Steps

### Phase 1: Server Deployment (30-45 minutes)

#### 1.1 Launch AWS EC2 Instance
```bash
# Instance Requirements:
- AMI: Ubuntu 22.04 LTS
- Instance Type: t3.medium (2 vCPU, 4GB RAM)
- Storage: 30GB SSD
- Security Group: Ports 22, 80, 443, 8000
```

#### 1.2 Install Dependencies
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install everything
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nodejs npm postgresql postgresql-contrib nginx git -y

# Install PM2 for process management
sudo npm install -g pm2
```

#### 1.3 Setup Database
```bash
# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE timesheet;
CREATE USER timesheet_user WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE timesheet TO timesheet_user;
\\q
```

#### 1.4 Deploy Application
```bash
# Clone your project
sudo mkdir -p /var/www/timesheet
sudo chown ubuntu:ubuntu /var/www/timesheet
cd /var/www/timesheet
git clone your-repo-url .

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt

# Create production .env
cp ../.env .env
nano .env  # Update with your database credentials
```

#### 1.5 Run Database Migration
```bash
# Add multi-developer support to existing database
cd /var/www/timesheet
python database_migration.py
```

#### 1.6 Update Backend Code
```python
# Add to backend/main.py
from multi_developer_api import router as multi_dev_router
app.include_router(multi_dev_router, prefix="/api/v1", tags=["multi-developer"])
```

```python
# Add to backend/models.py (copy from developer_model_addition.py)
class Developer(Base):
    __tablename__ = "developers"
    # ... (full model code)
```

#### 1.7 Build and Deploy Frontend
```bash
cd /var/www/timesheet/frontend
npm install
npm run build
```

#### 1.8 Configure Nginx
```bash
# Create site configuration
sudo nano /etc/nginx/sites-available/timesheet
```

Use the nginx configuration from `DEPLOYMENT_GUIDE.md`, then:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/timesheet /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

#### 1.9 Start Backend with PM2
```bash
# Create startup script
nano /var/www/timesheet/start_backend.sh
chmod +x /var/www/timesheet/start_backend.sh

# Start with PM2
pm2 start start_backend.sh --name "timesheet-backend"
pm2 save
pm2 startup ubuntu  # Follow instructions
```

### Phase 2: Developer Registration (5 minutes)

#### 2.1 Register Developers
```bash
# For each developer, create registration
curl -X POST https://your-domain.com/api/v1/register-developer \
  -H "Admin-Token: timesheet-admin-2025-secure-token" \
  -H "Content-Type: application/json" \
  -d '{
    "developer_id": "john_doe", 
    "name": "John Doe",
    "email": "john@company.com"
  }'

# Response will include API token for the developer
```

#### 2.2 List All Developers
```bash
# Verify registration
curl -H "Admin-Token: timesheet-admin-2025-secure-token" \
  https://your-domain.com/api/v1/developers
```

### Phase 3: Client Installation (10 minutes per developer)

#### 3.1 Download Client Files
Send each developer the `/client_sync/` folder with:
- `activitywatch_sync.py`
- `requirements.txt`
- `.env.template`
- `setup.bat` / `setup.sh`
- `README.md`

#### 3.2 Developer Setup Process
```bash
# Windows: Double-click setup.bat
# Linux/Mac: ./setup.sh

# Edit .env file with provided credentials
SERVER_URL=https://your-domain.com/api/v1
DEVELOPER_ID=john_doe
API_TOKEN=xyz123abc456...

# Test connection
python activitywatch_sync.py --test

# Start continuous sync
python activitywatch_sync.py --continuous
```

#### 3.3 Install as Service (Optional)
For automated startup, developers can install as a system service using the instructions in the client README.

## 🎨 Frontend Enhancements

### Add Team Dashboard
```javascript
// Create src/components/TeamDashboard.js
// Copy the TeamDashboard component from the guide

// Update src/App.js to include team route
<Route path="/team" element={<TeamDashboard />} />
```

### Update Navigation
```javascript
// Add team link to your navigation
<NavLink to="/team">Team Dashboard</NavLink>
```

## 📊 Testing the Complete System

### 1. Server Health Check
```bash
curl https://your-domain.com/api/v1/health
# Should return: {"status": "healthy"}
```

### 2. Test Client Connection
```bash
# On developer machine
python activitywatch_sync.py --test
# Should show all green checkmarks
```

### 3. Manual Data Sync
```bash
# Sync last 2 hours of data
python activitywatch_sync.py --sync-hours 2
```

### 4. Verify Team Dashboard
Visit `https://your-domain.com/team` and verify:
- All developers appear
- Activity data is being received
- Productivity metrics are calculated
- Last sync times are recent

## 📈 Expected Results

### Individual Developer Experience
- **Zero friction**: ActivityWatch runs as usual
- **Automatic sync**: Data uploads every 30 minutes
- **Privacy maintained**: Only activity metadata is sent
- **No performance impact**: Lightweight background process

### Management Dashboard
- **Real-time insights**: See what the team is working on
- **Productivity metrics**: Understand focus time and patterns
- **Project tracking**: See time allocation across projects
- **Team comparison**: Compare productivity patterns

### Data Flow Timeline
- **Minute 0**: Developer starts working
- **Minute 0-30**: ActivityWatch tracks locally
- **Minute 30**: Sync client sends data to server
- **Minute 30+**: Data appears in team dashboard
- **Continuous**: Process repeats every 30 minutes

## 🔧 Customization Options

### Sync Frequency
```env
# More frequent (every 15 minutes)
SYNC_INTERVAL_MINUTES=15

# Less frequent (every hour)
SYNC_INTERVAL_MINUTES=60
```

### Activity Categorization
Edit `multi_developer_api.py` to customize:
- Application categories
- Productivity weights
- Project extraction rules

### Dashboard Features
- Add project-specific views
- Create custom productivity reports
- Add team goals and targets
- Implement time tracking alerts

## 🚨 Security Considerations

### Server Security
- Use HTTPS with valid SSL certificate
- Regular security updates: `sudo apt update && sudo apt upgrade`
- Firewall configuration with UFW
- Database access restricted to localhost
- Regular automated backups

### Client Security
- API tokens are unique per developer
- All communication encrypted with HTTPS
- No file contents ever transmitted
- Local ActivityWatch data remains private

## 📊 Monitoring and Maintenance

### Server Monitoring
```bash
# Check service status
pm2 status
sudo systemctl status nginx postgresql

# View logs
pm2 logs timesheet-backend
sudo tail -f /var/log/nginx/access.log

# Database health
sudo -u postgres psql -d timesheet -c "SELECT COUNT(*) FROM activity_records;"
```

### Client Monitoring
```bash
# View sync logs on developer machine
tail -f activitywatch_sync.log

# Check sync status
python activitywatch_sync.py --test
```

## 🎯 Success Metrics

After deployment, you should see:

### Technical Metrics
- **Server uptime**: 99.9%+
- **Sync success rate**: 95%+
- **Data latency**: <60 minutes
- **Client connectivity**: All developers online

### Business Metrics
- **Team productivity visibility**: Real-time insights
- **Project time allocation**: Accurate tracking
- **Focus time analysis**: Deep work patterns
- **Distraction identification**: Improvement opportunities

## 🆘 Troubleshooting Quick Reference

### Server Issues
| Problem | Solution |
|---------|----------|
| Backend won't start | Check database connection in .env |
| Frontend not loading | Rebuild with `npm run build` |
| SSL certificate error | Run `sudo certbot --nginx` |
| Database connection failed | Check PostgreSQL service status |

### Client Issues
| Problem | Solution |
|---------|----------|
| Can't connect to ActivityWatch | Ensure AW is running on port 5600 |
| Server connection failed | Check SERVER_URL and internet |
| Authentication failed | Verify DEVELOPER_ID and API_TOKEN |
| No data to sync | Use computer normally for 30+ minutes |

## 🎉 Completion Checklist

### Server Setup
- [ ] EC2 instance launched and configured
- [ ] PostgreSQL database created and migrated
- [ ] Backend deployed and running with PM2
- [ ] Frontend built and served by Nginx
- [ ] SSL certificate installed (if using domain)
- [ ] API endpoints tested and responding

### Team Onboarding
- [ ] All developers registered in system
- [ ] API tokens distributed securely
- [ ] Sync clients installed on all machines
- [ ] Connection tests passed for all developers
- [ ] First successful data sync completed

### Dashboard Verification
- [ ] Team dashboard loads and shows data
- [ ] Individual developer views working
- [ ] Productivity calculations accurate
- [ ] Real-time sync status visible
- [ ] Project tracking functioning

### Production Readiness
- [ ] Automated backups configured
- [ ] Monitoring and alerting set up
- [ ] Documentation shared with team
- [ ] Service installation completed
- [ ] Security hardening applied

---

**🎊 Congratulations!** You now have a fully functional multi-developer productivity tracking system that automatically collects ActivityWatch data from your entire team into a centralized dashboard.

Your team members can work normally while their productivity data is automatically synced every 30 minutes to provide real-time insights into team productivity, project allocation, and work patterns.
