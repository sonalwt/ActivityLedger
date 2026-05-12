# ActivityLedger — AWS Production Deployment Guide

**Application:** ActivityLedger (Employee Activity Tracking System)
**Company:** FirstEconomy
**Target AWS Region:** `ap-south-1` (Mumbai)
**Date:** May 2026

---

## Table of Contents

1. [What is RDS? (Quick Answer)](#1-what-is-rds)
2. [Architecture Overview](#2-architecture-overview)
3. [Architecture Diagram](#3-architecture-diagram)
4. [AWS Services Used — With Reason](#4-aws-services-used)
5. [Database Strategy](#5-database-strategy)
6. [Network & VPC Design](#6-network--vpc-design)
7. [Backend Container Setup (ECS Fargate)](#7-backend-container-setup)
8. [Frontend Setup (S3 + CloudFront)](#8-frontend-setup)
9. [CI/CD Pipeline (GitHub Actions)](#9-cicd-pipeline)
10. [Secrets Management](#10-secrets-management)
11. [Monitoring & Alerts](#11-monitoring--alerts)
12. [Security](#12-security)
13. [Agent Distribution to Employees](#13-agent-distribution)
14. [Cost Estimates](#14-cost-estimates)
15. [Code Changes Required Before Deploying](#15-code-changes-required)
16. [Step-by-Step Deployment Guide](#16-step-by-step-deployment-guide)
17. [Post-Deployment Checklist](#17-post-deployment-checklist)

---

## 1. What is RDS?

**RDS (Relational Database Service) is not a different database — it IS PostgreSQL, managed by AWS.**

You are currently running PostgreSQL inside a Docker container. RDS gives you the exact same PostgreSQL 15 database, same SQL, same queries, zero code changes — but AWS handles everything operational:

| What you do today (Docker container) | What AWS does with RDS |
|--------------------------------------|------------------------|
| Run `docker-compose up` manually | Auto-starts, auto-restarts |
| Manual `pg_dump` for backups | Automated daily backups |
| Single container, no failover | Multi-AZ: auto-failover in 2 minutes |
| Patch PostgreSQL yourself | AWS handles version patches |
| Data lost if Docker volume deleted | 7-day point-in-time recovery |
| No performance monitoring | Built-in Performance Insights |

**Only change in your code is the connection string:**
```
# Today (Docker):
postgresql://postgres:asdf1234@localhost:5432/timesheet

# On AWS (RDS):
postgresql://activityledger_user:PASS@rds-endpoint.ap-south-1.rds.amazonaws.com:5432/timesheet
```

Same database. Same data. Same queries. AWS just runs it for you.

---

## 2. Architecture Overview

| Component | AWS Service | Monthly Cost (10 devs) |
|-----------|-------------|------------------------|
| Backend API | ECS Fargate (2 containers) | ~$31 |
| Database | RDS PostgreSQL 15 (managed) | ~$55 |
| DB Connection Pool | RDS Proxy | ~$22 |
| Frontend (React app) | S3 + CloudFront | ~$1 |
| Load Balancer | ALB + WAF | ~$25 |
| Networking | NAT Gateway + VPC Endpoints | ~$50 |
| Secrets storage | Secrets Manager | ~$1.20 |
| Monitoring | CloudWatch | ~$8 |
| DNS + SSL certificate | Route 53 + ACM (free SSL) | ~$1 |
| **Total** | | **~$194/month** |

---

## 3. Architecture Diagram

```
                              INTERNET
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
     Employee Machines                          Admin Users
  (Windows / Mac / Linux agents)        https://timesheet.firsteconomy.com
  POST /api/v1/activitywatch/webhook              (React SPA)
  every 5 minutes                                     │
              │                                       │
              ▼                                       ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    Route 53 (DNS)                            │
   │  api-timesheet.firsteconomy.com  →  ALB                     │
   │  timesheet.firsteconomy.com      →  CloudFront              │
   └──────────────────────────────────────────────────────────────┘
              │                                       │
              ▼                                       ▼
   ┌─────────────────────┐              ┌─────────────────────────┐
   │  Application Load   │              │   CloudFront CDN         │
   │  Balancer (ALB)     │              │   Origin: S3 bucket      │
   │  + WAF (firewall)   │              │   - index.html: no-cache │
   │                     │              │   - static/*: 1yr cache  │
   │  Port 80 → HTTPS    │              │   - handles React Router │
   │  Port 443 → Backend │              └──────────┬──────────────┘
   └────────┬────────────┘                         │
            │                           ┌──────────▼──────────────┐
            │                           │  S3 Bucket (private)     │
            │                           │  activityledger-frontend │
            │                           │  /index.html            │
            │                           │  /static/js/*.js        │
            │                           └─────────────────────────┘
            ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                   VPC: 10.0.0.0/16  (ap-south-1)                │
  │                                                                  │
  │  PUBLIC SUBNETS — ALB + NAT Gateway live here                   │
  │  10.0.1.0/24 (AZ: ap-south-1a)  10.0.2.0/24 (AZ: ap-south-1b) │
  │                           │                                     │
  │  PRIVATE SUBNETS — ECS containers live here                     │
  │  10.0.11.0/24 (AZ: a)    10.0.12.0/24 (AZ: b)                 │
  │  │                                                              │
  │  │  ┌─────────────── ECS Fargate Cluster ──────────────────┐   │
  │  │  │                                                       │   │
  │  │  │  ┌────────────────────┐  ┌────────────────────────┐  │   │
  │  │  │  │  Backend Service   │  │  Cleanup Service        │  │   │
  │  │  │  │  Min:2  Max:6      │  │  Always exactly 1       │  │   │
  │  │  │  │  0.5 vCPU / 1 GB  │  │  0.25 vCPU / 512 MB    │  │   │
  │  │  │  │  Port: 8000        │  │  Runs cleanup every 6h  │  │   │
  │  │  │  └─────────┬──────────┘  └──────────┬─────────────┘  │   │
  │  │  └────────────┼───────────────────────┼────────────────┘   │
  │  │               │                       │                     │
  │  │               ▼                       ▼                     │
  │  │  ┌────────────────────────────────────────────────────┐    │
  │  │  │  RDS Proxy (connection pooler · Port 5432)         │    │
  │  │  │  Manages DB connections so DB is not overwhelmed   │    │
  │  │  └──────────────────────────┬─────────────────────────┘    │
  │  │                             │                               │
  │  PRIVATE DB SUBNETS — RDS only (most secure)                  │
  │  10.0.21.0/24 (AZ: a)   10.0.22.0/24 (AZ: b)                │
  │  │  ┌──────────────────────────▼─────────────────────────┐    │
  │  │  │  RDS PostgreSQL 15  (same DB you use today)        │    │
  │  │  │  db.t4g.medium (2 vCPU, 4 GB RAM)                 │    │
  │  │  │  Multi-AZ: Primary + automatic standby             │    │
  │  │  │  Storage: 20 GB SSD, grows automatically to 100 GB │    │
  │  │  │  Backups: 7-day automated + monthly snapshots      │    │
  │  │  └────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
   ┌──────────────┐   ┌───────────────────┐  ┌──────────────────────┐
   │  ECR          │   │  Secrets Manager  │  │  S3 Buckets          │
   │  (Docker      │   │  Stores:          │  │  - frontend-prod     │
   │  image repo)  │   │  - DATABASE_URL   │  │  - agent-dist (pvt)  │
   │               │   │  - SECRET_KEY     │  └──────────────────────┘
   └──────────────┘   │  - MASTER_SECRET  │
                       └───────────────────┘
            │                    │
            ▼                    ▼
   ┌──────────────┐   ┌───────────────────┐
   │  GitHub       │   │  CloudWatch       │
   │  Actions      │   │  Logs + Alarms    │
   │  (CI/CD)      │   │  + Dashboard      │
   └──────────────┘   └───────────────────┘
```

---

## 4. AWS Services Used

### ECS Fargate (for running backend containers)
**Why not a plain EC2 server?** EC2 requires you to log in and patch the OS, manage Docker yourself, and handle crashes. Fargate is serverless containers — you say "run this Docker image with 0.5 CPU and 1 GB RAM" and AWS handles everything. No SSH needed day-to-day.

**Why not Lambda?** The backend has a background cleanup task that runs every 6 hours inside the app. Lambda has a 15-minute limit and doesn't keep running. Not suitable.

### ALB — Application Load Balancer
Receives HTTPS traffic from agents and admin users, routes to backend containers. Handles SSL termination (HTTPS). Has WAF (firewall) built in to block attacks.

**Why not API Gateway?** API Gateway costs $3.50 per million requests. With 10 agents posting every 5 minutes, ALB is much cheaper (~$18/month flat).

### S3 + CloudFront (for React frontend)
The React app is just static files (HTML, JS, CSS) after `npm run build`. No need to run a server for it. S3 stores the files, CloudFront serves them from edge locations near your employees (Mumbai, Chennai, Hyderabad) for fast loading.

**Important:** The frontend `Dockerfile` currently tries to copy a file called `nginx.conf` that **does not exist** in your repository. This would cause the Docker build to fail. S3 + CloudFront avoids this problem entirely.

### RDS Proxy (connection pool manager)
Your backend uses SQLAlchemy with `pool_size=10, max_overflow=20` = 30 connections per container. If 6 containers are running (auto-scaled), that's 180 connections to PostgreSQL. RDS PostgreSQL on the recommended instance only handles ~85 connections safely. RDS Proxy sits in the middle and multiplexes 180 app connections into ~20 real database connections.

### GitHub Actions (CI/CD)
When you push code to the `main` branch, GitHub Actions automatically:
1. Builds the Docker image
2. Pushes it to ECR (AWS container registry)
3. Deploys it to ECS (zero downtime)
4. Builds the React app and uploads to S3

**Why not AWS CodePipeline?** CodePipeline is more complex to set up and your code is already on GitHub.

---

## 5. Database Strategy

### Stay with PostgreSQL — just use RDS to host it

**Do NOT switch to Aurora PostgreSQL.** Aurora minimum cost in Mumbai is ~$85/month (writer + reader). Your data volumes don't need it:

| Scale | Records/day | DB size after 2 years |
|-------|-------------|----------------------|
| 10 developers | ~4,000 | ~1.2 GB |
| 50 developers | ~20,000 | ~6.2 GB |
| 100 developers | ~40,000 | ~12.5 GB |

Aurora makes sense at 1+ TB of data. You will not reach that for many years.

### Recommended: RDS PostgreSQL 15 on `db.t4g.medium`

- 2 vCPU, 4 GB RAM
- Graviton2 processor — 20% cheaper than equivalent t3 instance
- Handles your peak write load: ~60 INSERTs/minute for 50 developers
- **Monthly cost: ~$55/month (Multi-AZ)**

### Multi-AZ: YES

Your database runs on two servers (Primary + Standby in different data centers). If the primary fails, AWS automatically switches to the standby in ~2 minutes with no data loss. Your agents buffer data locally and retry, so a 2-minute outage is invisible to them.

### Do NOT add table partitioning yet

Your `activity_records` table already has the right indexes:
- `idx_dev_timestamp (developer_id, timestamp)` — makes dashboard date-range queries fast
- `idx_activity_dedup` — prevents duplicate records

These indexes are sufficient. Add partitioning only when the table exceeds **20 GB** or queries consistently take more than 2 seconds. At current growth, this is 3–5 years away for 50 developers.

### Storage

```
Type: gp3 SSD (20% cheaper than gp2, same performance)
Starting size: 20 GB
Auto-scaling: enabled, grows automatically up to 100 GB
Backups:
  - Automated: 7-day retention, runs 1:00–2:00 AM IST
  - Monthly snapshot: kept for 12 months
Encryption: AES-256 (on by default)
```

---

## 6. Network & VPC Design

### Subnet Layout

```
VPC: 10.0.0.0/16  (ap-south-1)

PUBLIC (ALB + NAT Gateway live here — accessible from internet):
  10.0.1.0/24   ap-south-1a
  10.0.2.0/24   ap-south-1b

PRIVATE APP (ECS containers live here — NOT accessible from internet):
  10.0.11.0/24  ap-south-1a
  10.0.12.0/24  ap-south-1b

PRIVATE DB (RDS only — most locked down):
  10.0.21.0/24  ap-south-1a
  10.0.22.0/24  ap-south-1b
```

### Security Groups (Firewall Rules)

**ALB (load balancer):**
```
Allow IN:  HTTPS (443) from anywhere  ← agents and admin users
           HTTP  (80)  from anywhere  ← redirect to HTTPS only
Allow OUT: Port 8000 to backend containers only
```

**Backend containers:**
```
Allow IN:  Port 8000 from ALB only   ← no direct internet access
Allow OUT: Port 5432 to RDS Proxy    ← database access
           Port 443  to internet     ← ECR image pull, Secrets Manager
```

**RDS Proxy:**
```
Allow IN:  Port 5432 from backend containers only
Allow OUT: Port 5432 to RDS
```

**RDS PostgreSQL:**
```
Allow IN:  Port 5432 from RDS Proxy only  ← database NEVER directly accessible
Allow OUT: nothing
```

### Save Money: VPC Endpoints

Without VPC Endpoints, your containers download Docker images from ECR through a NAT Gateway, which charges for data transfer (~$35/month). Create VPC Endpoints for these 4 services so traffic stays within AWS network and bypasses NAT:

| Service | Endpoint | Saves |
|---------|----------|-------|
| ECR API | `com.amazonaws.ap-south-1.ecr.api` | ~$5/month |
| ECR Docker | `com.amazonaws.ap-south-1.ecr.dkr` | ~$15/month |
| Secrets Manager | `com.amazonaws.ap-south-1.secretsmanager` | ~$3/month |
| CloudWatch Logs | `com.amazonaws.ap-south-1.logs` | ~$5/month |

Cost: ~$28/month for 4 endpoints. Saves ~$25/month in NAT data transfer.

---

## 7. Backend Container Setup

### Docker Image Repository (ECR)

```
Repository name: activityledger/backend
Region: ap-south-1
Keep last 10 images, delete untagged images after 1 day
```

### ECS Cluster

```
Name: activityledger-prod
Type: Fargate (no servers to manage)
Container Insights: ON (detailed metrics in CloudWatch)
```

### Service 1 — Backend API

```
Task size: 0.5 vCPU, 1 GB RAM
Container: activityledger/backend:latest
Port: 8000

Secrets loaded automatically at startup from Secrets Manager:
  DATABASE_URL   → your RDS connection string
  SECRET_KEY     → JWT signing key
  MASTER_SECRET  → agent webhook auth secret

Environment variables:
  ENVIRONMENT=production
  ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=30

Running instances:
  Minimum: 2 (one in each availability zone for reliability)
  Maximum: 6 (auto-scales up when traffic increases)

Auto-scaling rules:
  Scale UP when:  CPU > 60% for 3 minutes → add 2 more containers
  Scale DOWN when: CPU < 25% for 10 minutes → remove 1 container
  Also scale UP when: > 150 requests per container per minute

Deployment: Zero downtime
  New containers start BEFORE old ones stop (Min healthy = 100%)
```

### Service 2 — Cleanup Scheduler (Important)

**Problem found in your code:** The cleanup task in `cleanup_idle_api.py` starts on EVERY backend container. With 2+ containers running, the same DELETE query runs simultaneously — risk of deadlocks.

**Fix:** Run cleanup as a separate service with exactly 1 instance (singleton).

```
Task size: 0.25 vCPU, 512 MB RAM
Container: activityledger/backend:latest (same image)
Command: ["python", "run_cleanup.py"]
Environment: CLEANUP_ONLY=true
Running instances: Always exactly 1
No auto-scaling
```

### Health Check

The current `/api/v1/health` endpoint returns success without testing the database. Improve it:

```python
@router.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))  # will fail if DB is down
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
```

ALB checks this endpoint every 30 seconds. If it fails 3 times, the container is replaced.

---

## 8. Frontend Setup

### Build the React App

```bash
cd frontend
REACT_APP_API_URL=https://api-timesheet.firsteconomy.com npm run build
```

This creates a `build/` folder with static HTML/JS/CSS files.

### Upload to S3

```bash
# Create S3 bucket (one time)
aws s3 mb s3://activityledger-frontend-prod --region ap-south-1

# Upload index.html with no-cache (so users always get latest version)
aws s3 sync ./build s3://activityledger-frontend-prod \
  --delete --cache-control "no-cache" --exclude "static/*"

# Upload static assets with 1-year cache (filenames are content-hashed, safe to cache)
aws s3 sync ./build/static s3://activityledger-frontend-prod/static \
  --cache-control "public, max-age=31536000, immutable"
```

### CloudFront Configuration

```
Origin: Your S3 bucket (private — users cannot access S3 directly)
Domain: timesheet.firsteconomy.com
SSL certificate: ACM certificate in us-east-1 (IMPORTANT: must be us-east-1 for CloudFront)
Force HTTPS: Yes

Cache rules:
  /index.html   → Cache for 0 seconds (always fresh)
  /static/*     → Cache for 1 year (files are uniquely named per build)

Custom error rule:
  When S3 returns 403 (file not found) → serve /index.html with HTTP 200
  WHY: When user goes to https://timesheet.firsteconomy.com/dashboard directly,
       S3 says "no such file". This rule makes CloudFront serve index.html instead,
       then React Router handles the /dashboard route. Without this, direct links break.
```

---

## 9. CI/CD Pipeline

### How It Works

Every time you push code to the `main` branch on GitHub, this happens automatically:

```
1. GitHub Actions starts (triggered by push to main)
      ↓
2. Build Docker image for backend
      ↓
3. Push image to ECR (AWS container registry)
      ↓
4. Tell ECS to deploy the new image (zero downtime rolling update)
      ↓
5. Build React frontend (npm run build)
      ↓
6. Upload new files to S3
      ↓
7. CloudFront serves the new index.html immediately
```

Total time: ~12–15 minutes. No downtime. Old containers only stop after new ones are healthy.

### Setup GitHub Actions OIDC (One-time, Secure)

Instead of storing AWS access keys in GitHub (security risk), use OIDC — GitHub proves its identity to AWS and gets temporary credentials per deployment:

```bash
# Run once in your AWS account:
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

Then create an IAM role that trusts GitHub Actions for your specific repository only.

### GitHub Secrets to Configure

In your GitHub repository → Settings → Secrets:
```
AWS_ACCOUNT_ID     → your 12-digit AWS account number
AWS_REGION         → ap-south-1
REACT_APP_API_URL  → https://api-timesheet.firsteconomy.com
```

---

## 10. Secrets Management

### Problems Found in Current Code

| File | Problem |
|------|---------|
| `agent_mac/install_mac.sh` | `SECRET="TimesheetMaster2025258c362c"` hardcoded — anyone who gets this file gets the master secret |
| `agent/install.bat` | Same hardcoded master secret |
| `backend/database.py` | `postgresql://postgres:asdf1234@localhost:5432/timesheet` hardcoded as fallback — default password exposed |
| `docker-compose.yml` | `POSTGRES_PASSWORD: asdf1234` in plaintext |

### Fix: Use AWS Secrets Manager

Create two secrets:

**Secret 1: `activityledger/prod/database`**
```json
{
  "url": "postgresql://activityledger_user:YOUR_STRONG_PASSWORD@rds-proxy-endpoint:5432/timesheet"
}
```

**Secret 2: `activityledger/prod/app`**
```json
{
  "SECRET_KEY": "generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\"",
  "MASTER_SECRET": "new-value-NOT-the-current-hardcoded-one",
  "ALGORITHM": "HS256",
  "ACCESS_TOKEN_EXPIRE_MINUTES": "30"
}
```

These are injected into ECS containers as environment variables at startup. They never appear in code, logs, or Docker images.

### MASTER_SECRET Annual Rotation

The token your agents use is year-scoped:
```python
token_input = f"{developer_id}:{master_secret}:{current_year}"
```

**Each January:**
1. Generate new `MASTER_SECRET` in Secrets Manager
2. Deploy ECS (containers pick up new secret in ~5 minutes)
3. Upload updated agent installers to S3 with new secret
4. Send employees new install link

**To avoid disruption:** Support both current-year and previous-year tokens for 3 months, giving employees time to reinstall the agent.

---

## 11. Monitoring & Alerts

### Log Storage (CloudWatch)

```
/ecs/activityledger-backend    Keep 30 days
/ecs/activityledger-cleanup    Keep 30 days
/rds/activityledger/slowquery  Keep 14 days  (queries > 1 second)
```

Enable slow query logging in RDS parameter group:
```
log_min_duration_statement = 1000
```

### Alerts to Set Up

**P0 — Immediate action (webhook down = agents cannot send data):**
```
Alarm: ALB HealthyHostCount < 1
Action: SMS + Email immediately
```

**P1 — High priority:**
```
Alarm: ALB 5XX errors > 5 in 5 minutes  →  Email
Alarm: ALB response time P95 > 3 seconds for 5 min  →  Email
```

**P2 — Warning:**
```
Alarm: RDS connections > 70  →  Email  (approaching limit of ~85)
Alarm: RDS free storage < 5 GB  →  Email
Alarm: RDS CPU > 80% for 10 minutes  →  Email
```

**P3 — Watch:**
```
Alarm: ECS memory > 85% for 15 minutes  →  Email  (possible memory leak)
```

### Detect When an Agent Stops Working

Add this to the webhook handler after a successful sync:
```python
import boto3
cloudwatch = boto3.client('cloudwatch', region_name='ap-south-1')
cloudwatch.put_metric_data(
    Namespace='ActivityLedger/Agents',
    MetricData=[{
        'MetricName': 'WebhookReceived',
        'Dimensions': [{'Name': 'DeveloperID', 'Value': developer_id}],
        'Value': 1, 'Unit': 'Count'
    }]
)
```

Create an alarm: if a developer sends 0 webhooks in 45 minutes during business hours (9am–7pm IST), alert admin: *"Agent may be down for: [developer name]"*

### Dashboard

Create a CloudWatch dashboard `activityledger-prod` with:
- Requests per minute to `/api/v1/activitywatch/webhook`
- Backend error rate (5XX)
- Response time P50/P95
- ECS running task count
- RDS CPU and connections
- RDS free storage (7-day trend)

---

## 12. Security

### WAF (Firewall) Rules

Attach to the ALB:

```
AWS Managed Rules (auto-updated by AWS):
  ✓ AWSManagedRulesCommonRuleSet       — blocks OWASP Top 10 attacks
  ✓ AWSManagedRulesSQLiRuleSet         — blocks SQL injection
  ✓ AWSManagedRulesKnownBadInputsRuleSet — blocks Log4j, shellshock

Your Custom Rules:
  Block IP if it sends > 200 requests to /api/v1/activitywatch/webhook in 5 minutes
  (Legitimate agents send 1 request per 5 minutes. 200/5min = buggy agent loop)

  Block IP if it sends > 30 requests to /api/admin/* in 1 minute
  (Protects admin endpoints from scraping)
```

### SSL Certificates (Free via ACM)

```
Certificate 1 — ap-south-1 region (for ALB):
  api-timesheet.firsteconomy.com
  Validate via Route 53 DNS (automatic)

Certificate 2 — us-east-1 region (for CloudFront — MUST be us-east-1):
  timesheet.firsteconomy.com
  Validate via Route 53 DNS (automatic)
```

### Force HTTPS

ALB rule: all HTTP (port 80) requests → permanent redirect to HTTPS. No unencrypted traffic ever reaches your containers.

### Other Security Steps

- **Fix CORS:** `main.py` currently allows `http://localhost:3000` in production. Remove it. Only allow `https://timesheet.firsteconomy.com`
- **Enable CloudTrail:** Logs all AWS API calls (~$2/month). Required for security audits.
- **Enable GuardDuty:** Detects compromised credentials automatically (~$4/month, zero config).
- **Block public access** on all S3 buckets.

---

## 13. Agent Distribution

### Problem with Current Approach

The `MASTER_SECRET` is hardcoded inside the installer scripts. If you put these on GitHub Releases (which are public), anyone can download the installer and extract your master secret.

### Solution: Private S3 Bucket + Pre-signed Links

**S3 bucket structure:**
```
Bucket: activityledger-agent-dist  (PRIVATE — no public access)

/windows/v1.0.0/
  ActivityLedgerAgent.exe
  install.bat

/mac/v1.0.0/
  install_mac.sh
  ActivityLedgerAgent_mac

/linux/v1.0.0/
  ActivityLedgerAgent_linux
  install_linux.sh
```

**Onboarding a new employee:**
1. Admin opens ActivityLedger admin panel
2. Clicks "Generate Install Link" for the employee
3. Backend creates a pre-signed S3 URL (expires in 48 hours):
   ```bash
   aws s3 presign s3://activityledger-agent-dist/mac/v1.0.0/install_mac.sh --expires-in 172800
   ```
4. Admin emails the link to the employee
5. Employee downloads and runs the installer
6. Link automatically expires — cannot be shared or reused

---

## 14. Cost Estimates

### 10 Employees (Current Scale)

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate — Backend (2 containers) | ~$25 |
| ECS Fargate — Cleanup (1 container) | ~$6 |
| RDS PostgreSQL Multi-AZ | ~$55 |
| RDS Proxy | ~$22 |
| ALB | ~$18 |
| WAF | ~$7 |
| CloudFront + S3 | ~$1 |
| S3 Agent files | ~$0.50 |
| ECR (Docker images) | ~$0.50 |
| Secrets Manager | ~$1.20 |
| NAT Gateway | ~$35 |
| VPC Endpoints (saves NAT cost) | ~$28 |
| Route 53 | ~$1 |
| CloudWatch | ~$8 |
| SSL Certificates (ACM) | **FREE** |
| **TOTAL** | **~$208/month** |

**Save money at launch:** Skip Multi-AZ initially → saves ~$28/month → **~$180/month**. Add Multi-AZ after a few months when you trust the setup.

**Save more:** Buy RDS 1-year reserved instance → cuts RDS from $55 to ~$33/month.

### 50 Employees

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate — Backend (3–4 containers avg) | ~$50 |
| RDS db.t4g.large Multi-AZ (upgrade needed) | ~$120 |
| Everything else similar | ~$130 |
| **TOTAL** | **~$300/month** |

---

## 15. Code Changes Required

Fix these issues **before deploying**. Some will break the deployment if not fixed.

### BLOCKING — Must Fix First

**Fix 1: Frontend API calls use relative URLs (will break on CloudFront)**

File: `frontend/src/contexts/AuthContext.js`

The current code calls `/token`, `/users/me`, `/register` as relative URLs. When the frontend is served from CloudFront (`https://timesheet.firsteconomy.com`), these calls go to `https://timesheet.firsteconomy.com/token` — which returns 404 because the API is on a different domain.

```javascript
// Add this near the top of AuthContext.js:
const API_URL = process.env.REACT_APP_API_URL || '';

// Change all API calls from relative to absolute:
// BEFORE: axios.post('/token', ...)
// AFTER:  axios.post(`${API_URL}/token`, ...)

// BEFORE: axios.get('/users/me', ...)
// AFTER:  axios.get(`${API_URL}/users/me`, ...)
```

**Fix 2: nginx.conf is missing (Docker build will fail)**

File: `frontend/Dockerfile` line 19 — `COPY nginx.conf /etc/nginx/conf.d/default.conf`

This file does not exist in the repository. Using S3 + CloudFront avoids this problem (no nginx needed). But if you ever want to run the frontend Docker container, create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Important Security Fixes

**Fix 3: Remove hardcoded database password fallback**

File: `backend/database.py` (around line 18)

```python
# BEFORE (dangerous — uses wrong hardcoded DB if env var missing):
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:asdf1234@localhost:5432/timesheet")

# AFTER (fail immediately if not configured — safer):
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
```

**Fix 4: Cleanup task runs on all containers**

File: `backend/main.py`

```python
# Add this guard so cleanup only runs on the dedicated cleanup container:
if not os.getenv("CLEANUP_ONLY"):
    @app.on_event("startup")
    async def startup_cleanup():
        asyncio.create_task(daily_cleanup_loop())
```

**Fix 5: Remove localhost from production CORS**

File: `backend/main.py`

```python
# Remove http://localhost:3000 from production allowed_origins
# Only keep: ["https://timesheet.firsteconomy.com"]
```

**Fix 6: Remove hardcoded MASTER_SECRET from agent installers**

Files: `agent_mac/install_mac.sh`, `agent/install.bat`

Before uploading to S3, replace `TimesheetMaster2025258c362c` with the new rotated value from Secrets Manager. Do not use the old hardcoded value in production.

---

## 16. Step-by-Step Deployment Guide

Work through phases in order. Most waiting time is for AWS to provision resources.

---

### PHASE 1 — Foundation
*Estimated time: 2 hours*

**Step 1: Create VPC**

Go to AWS Console → VPC → Create VPC → Select "VPC and more"

Settings:
```
Name: activityledger-prod
IPv4 CIDR: 10.0.0.0/16
Number of AZs: 2
Public subnets: 2
Private subnets: 2 (you will add 2 more DB subnets manually after)
NAT Gateway: 1 per AZ
Enable DNS hostnames: YES
Enable DNS resolution: YES
```

After creation, manually add 2 more private subnets for the database:
```
10.0.21.0/24  ap-south-1a  (DB subnet)
10.0.22.0/24  ap-south-1b  (DB subnet)
```

**Step 2: Create Security Groups**

Create these 4 security groups (rules defined in Section 6):
- `activityledger-alb-sg`
- `activityledger-backend-sg`
- `activityledger-rdsproxy-sg`
- `activityledger-rds-sg`

**Step 3: Request SSL Certificates (do this early — DNS validation takes a few minutes)**

```bash
# Certificate for ALB — in ap-south-1:
aws acm request-certificate \
  --domain-name api-timesheet.firsteconomy.com \
  --validation-method DNS \
  --region ap-south-1

# Certificate for CloudFront — MUST be in us-east-1:
aws acm request-certificate \
  --domain-name timesheet.firsteconomy.com \
  --validation-method DNS \
  --region us-east-1
```

Go to ACM console → click each certificate → add the DNS validation CNAME records to Route 53. They validate within a few minutes.

**Step 4: Create Secrets**

```bash
# Generate a secure SECRET_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Create database secret (put placeholder URL, update after RDS is ready)
aws secretsmanager create-secret \
  --name activityledger/prod/database \
  --region ap-south-1 \
  --secret-string '{"url":"PLACEHOLDER"}'

# Create app secret (replace values with your generated ones)
aws secretsmanager create-secret \
  --name activityledger/prod/app \
  --region ap-south-1 \
  --secret-string '{
    "SECRET_KEY":"YOUR_GENERATED_64_CHAR_HEX",
    "MASTER_SECRET":"YOUR_NEW_ROTATED_SECRET",
    "ALGORITHM":"HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES":"30"
  }'
```

---

### PHASE 2 — Database
*Estimated time: 30 minutes (15 min waiting for RDS)*

**Step 5: Create RDS Subnet Group**

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name activityledger-db \
  --db-subnet-group-description "ActivityLedger DB subnets" \
  --subnet-ids subnet-DB_AZ_A subnet-DB_AZ_B
```

**Step 6: Create RDS PostgreSQL**

```bash
aws rds create-db-instance \
  --db-instance-identifier activityledger-prod \
  --db-instance-class db.t4g.medium \
  --engine postgres \
  --engine-version "15.8" \
  --master-username activityledger_user \
  --master-user-password "YOUR_STRONG_PASSWORD_HERE" \
  --db-name timesheet \
  --vpc-security-group-ids sg-RDS_SG_ID \
  --db-subnet-group-name activityledger-db \
  --multi-az \
  --storage-type gp3 \
  --allocated-storage 20 \
  --max-allocated-storage 100 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --preferred-backup-window "20:30-21:30" \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

Wait ~15 minutes for status to become "Available".

**Step 7: Update Secrets Manager with RDS endpoint**

```bash
# Get the RDS endpoint:
aws rds describe-db-instances \
  --db-instance-identifier activityledger-prod \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

# Update the secret:
aws secretsmanager update-secret \
  --secret-id activityledger/prod/database \
  --secret-string '{"url":"postgresql://activityledger_user:YOUR_PASSWORD@RDS_ENDPOINT:5432/timesheet"}'
```

**Step 8: Create RDS Proxy**

Go to AWS Console → RDS → Proxies → Create proxy

```
Proxy name: activityledger-proxy
Database: activityledger-prod
Secret: activityledger/prod/database
Subnets: Select the 2 private app subnets (10.0.11.x and 10.0.12.x)
Security group: activityledger-rdsproxy-sg
```

Wait ~5 minutes. Note the proxy endpoint — update Secrets Manager to use the proxy endpoint instead of the direct RDS endpoint.

---

### PHASE 3 — Build & Push Docker Image
*Estimated time: 20 minutes*

**Step 9: Apply code fixes from Section 15 first**

Fix `AuthContext.js`, `database.py`, `main.py` before building.

**Step 10: Create ECR and push image**

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name activityledger/backend \
  --region ap-south-1

# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS \
  --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

# Build and push
cd backend
docker build -t activityledger/backend:latest .
docker tag activityledger/backend:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/activityledger/backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/activityledger/backend:latest
```

---

### PHASE 4 — ECS (Backend Containers)
*Estimated time: 1.5 hours*

**Step 11: Create IAM Roles**

Go to AWS Console → IAM → Roles → Create role

**Role 1: `activityledger-ecs-execution-role`**
- Trusted entity: ECS Tasks
- Attach policy: `AmazonECSTaskExecutionRolePolicy`

**Role 2: `activityledger-ecs-task-role`**
- Trusted entity: ECS Tasks
- Create inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:ap-south-1:YOUR_ACCOUNT:secret:activityledger/prod/*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:ap-south-1:YOUR_ACCOUNT:log-group:/ecs/activityledger-*"
    }
  ]
}
```

**Step 12: Create ECS Cluster**

```bash
aws ecs create-cluster \
  --cluster-name activityledger-prod \
  --settings name=containerInsights,value=enabled
```

**Step 13: Create Application Load Balancer**

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name activityledger-alb \
  --subnets subnet-PUBLIC_AZ_A subnet-PUBLIC_AZ_B \
  --security-groups sg-ALB_SG_ID \
  --scheme internet-facing \
  --type application

# Create target group (tells ALB where to send requests)
aws elbv2 create-target-group \
  --name activityledger-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id YOUR_VPC_ID \
  --target-type ip \
  --health-check-path /api/v1/health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3
```

Create ALB Listeners (use Console — easier):
- Listener 1: HTTP :80 → Redirect to HTTPS :443
- Listener 2: HTTPS :443 → Forward to `activityledger-backend-tg` (attach ACM cert)

**Step 14: Create ECS Task Definitions**

Use AWS Console → ECS → Task Definitions → Create

For **Backend task definition:**
```
Family: activityledger-backend
CPU: 0.5 vCPU
Memory: 1 GB
Task role: activityledger-ecs-task-role
Execution role: activityledger-ecs-execution-role

Container:
  Name: backend
  Image: YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/activityledger/backend:latest
  Port: 8000

  Secrets (from Secrets Manager):
    DATABASE_URL  → activityledger/prod/database:url::
    SECRET_KEY    → activityledger/prod/app:SECRET_KEY::
    MASTER_SECRET → activityledger/prod/app:MASTER_SECRET::

  Environment:
    ENVIRONMENT=production
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30

  Log configuration:
    Driver: awslogs
    Group: /ecs/activityledger-backend
    Region: ap-south-1
    Stream prefix: ecs
```

For **Cleanup task definition:**
```
Family: activityledger-cleanup
CPU: 0.25 vCPU
Memory: 512 MB
Same roles as backend

Container:
  Name: cleanup
  Image: same image as backend
  Command: ["python", "run_cleanup.py"]

  Environment:
    CLEANUP_ONLY=true
    DATABASE_URL from Secrets Manager (same as backend)
```

**Step 15: Create ECS Services**

```bash
# Backend service (2 containers)
aws ecs create-service \
  --cluster activityledger-prod \
  --service-name activityledger-backend-service \
  --task-definition activityledger-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-PRIVATE_APP_A, subnet-PRIVATE_APP_B],
    securityGroups=[sg-BACKEND_SG_ID],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,
    containerName=backend,containerPort=8000" \
  --deployment-configuration "minimumHealthyPercent=100,maximumPercent=200"

# Cleanup service (1 container)
aws ecs create-service \
  --cluster activityledger-prod \
  --service-name activityledger-cleanup-service \
  --task-definition activityledger-cleanup:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-PRIVATE_APP_A, subnet-PRIVATE_APP_B],
    securityGroups=[sg-BACKEND_SG_ID],
    assignPublicIp=DISABLED
  }" \
  --deployment-configuration "minimumHealthyPercent=0,maximumPercent=100"
```

**Verify:** Wait 2–3 minutes, then check:
```bash
aws ecs describe-services \
  --cluster activityledger-prod \
  --services activityledger-backend-service \
  --query 'services[0].runningCount'
# Should output: 2
```

---

### PHASE 5 — Frontend
*Estimated time: 30 minutes*

**Step 16: Apply Fix 1 from Section 15** (relative API paths in AuthContext.js)

**Step 17: Create S3 bucket and upload frontend**

```bash
# Create bucket
aws s3 mb s3://activityledger-frontend-prod --region ap-south-1

# Block all public access
aws s3api put-public-access-block \
  --bucket activityledger-frontend-prod \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Build React app
cd frontend
REACT_APP_API_URL=https://api-timesheet.firsteconomy.com npm run build

# Upload (index.html = no cache, static files = 1 year cache)
aws s3 sync ./build s3://activityledger-frontend-prod \
  --delete --cache-control "no-cache" --exclude "static/*"
aws s3 sync ./build/static s3://activityledger-frontend-prod/static \
  --cache-control "public, max-age=31536000, immutable"
```

**Step 18: Create CloudFront Distribution**

Go to AWS Console → CloudFront → Create distribution

```
Origin domain: activityledger-frontend-prod.s3.ap-south-1.amazonaws.com
Origin access: Create new OAC (Origin Access Control)
Alternate domain name: timesheet.firsteconomy.com
SSL certificate: Select the us-east-1 certificate for timesheet.firsteconomy.com
Viewer protocol: Redirect HTTP to HTTPS
Compress objects: Yes

Custom error pages → Add:
  HTTP error code: 403
  Customize error response: Yes
  Response page path: /index.html
  HTTP response code: 200
```

**Step 19: Update Route 53 DNS**

Go to Route 53 → Hosted zones → firsteconomy.com

Add two A records (ALIAS type — no IP address needed):
```
api-timesheet.firsteconomy.com  →  Alias to ALB DNS name
timesheet.firsteconomy.com      →  Alias to CloudFront domain name
```

---

### PHASE 6 — CI/CD and Monitoring
*Estimated time: 1.5 hours*

**Step 20: Set up GitHub Actions**

Create file `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: ap-south-1
  ECR_REPOSITORY: activityledger/backend
  ECS_CLUSTER: activityledger-prod
  ECS_SERVICE: activityledger-backend-service

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/activityledger-github-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG ./backend
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment
          aws ecs wait services-stable \
            --cluster $ECS_CLUSTER \
            --services $ECS_SERVICE

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/activityledger-github-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Build React app
        working-directory: frontend
        env:
          REACT_APP_API_URL: ${{ secrets.REACT_APP_API_URL }}
        run: |
          npm ci
          npm run build

      - name: Upload to S3 and invalidate CloudFront
        run: |
          aws s3 sync ./frontend/build s3://activityledger-frontend-prod \
            --delete --cache-control "no-cache" --exclude "static/*"
          aws s3 sync ./frontend/build/static s3://activityledger-frontend-prod/static \
            --cache-control "public, max-age=31536000, immutable"
          aws cloudfront create-invalidation \
            --distribution-id YOUR_CLOUDFRONT_DISTRIBUTION_ID \
            --paths "/index.html"
```

**Step 21: Create SNS Alert Topic**

```bash
aws sns create-topic --name activityledger-alerts --region ap-south-1

aws sns subscribe \
  --topic-arn arn:aws:sns:ap-south-1:YOUR_ACCOUNT:activityledger-alerts \
  --protocol email \
  --notification-endpoint your-team@firsteconomy.com
```

Check your email and confirm the subscription.

**Step 22: Create CloudWatch Alarms**

Go to CloudWatch → Alarms → Create alarm for each alarm in Section 11.

**Step 23: Enable Security Services**

```bash
# Enable CloudTrail (audit log of all AWS API calls)
aws cloudtrail create-trail \
  --name activityledger-audit \
  --s3-bucket-name activityledger-cloudtrail-logs \
  --is-multi-region-trail

# Enable GuardDuty (threat detection)
aws guardduty create-detector --enable
```

---

### PHASE 7 — Agent Distribution
*Estimated time: 30 minutes*

**Step 24: Create agent distribution bucket**

```bash
aws s3 mb s3://activityledger-agent-dist --region ap-south-1
# Block all public access (same as frontend bucket)
```

**Step 25: Update agent installer scripts**

In `agent_mac/install_mac.sh` and `agent/install.bat`:
- Replace `SERVER_URL` with `https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook`
- Replace `MASTER_SECRET` with the new value from Secrets Manager (NOT the old hardcoded value)

**Step 26: Upload agent packages**

```bash
aws s3 cp agent_mac/install_mac.sh s3://activityledger-agent-dist/mac/v1.0.0/install_mac.sh
aws s3 cp agent/dist/ActivityLedgerAgent.exe s3://activityledger-agent-dist/windows/v1.0.0/
aws s3 cp agent_linux/ActivityLedgerAgent s3://activityledger-agent-dist/linux/v1.0.0/
aws s3 cp agent_linux/install_linux.sh s3://activityledger-agent-dist/linux/v1.0.0/
```

**Step 27: End-to-end test**

Install the agent on one test machine. Watch CloudWatch Logs:
```
Log group: /ecs/activityledger-backend
Filter: "Received ActivityWatch webhook"
```

You should see the log entry within 5 minutes of the agent starting.

---

## 17. Post-Deployment Checklist

Run through this after completing all phases:

```
[ ] curl https://api-timesheet.firsteconomy.com/api/v1/health
    Expected: {"status":"healthy","timestamp":"..."}

[ ] Open https://timesheet.firsteconomy.com in browser
    Expected: React login page loads

[ ] Login to admin dashboard with existing credentials
    Expected: Dashboard loads, existing data visible

[ ] Check HTTP redirect:
    curl -I http://api-timesheet.firsteconomy.com
    Expected: 301 redirect to https://

[ ] Test direct URL access (React Router):
    Navigate to https://timesheet.firsteconomy.com/dashboard directly
    Expected: Dashboard loads (not 404)

[ ] Check ECS containers are running:
    AWS Console → ECS → activityledger-prod → activityledger-backend-service
    Expected: Running count = 2

[ ] Check RDS is connected:
    AWS Console → RDS → activityledger-prod → Monitoring
    Expected: DatabaseConnections > 0

[ ] Check all CloudWatch alarms are green (OK state)

[ ] Install agent on test machine, wait 5 minutes
    Check CloudWatch Logs → /ecs/activityledger-backend
    Expected: "Received ActivityWatch webhook from [developer_id]"

[ ] Verify activity data appears in developer dashboard after 5 minutes

[ ] Push a test commit to main branch
    Expected: GitHub Actions workflow starts and completes successfully
```

---

*Document created: May 2026*
*Region: ap-south-1 (Mumbai)*
*For questions about this deployment, refer to the architecture diagrams and service descriptions above.*
