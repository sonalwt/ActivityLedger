# PostgreSQL Setup Guide

Since you already have a PostgreSQL database, here's how to configure the timesheet application to use it.

## 1. Environment Configuration

Create a `.env` file in the root directory with your PostgreSQL connection details:

```env
# PostgreSQL Database Configuration
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database_name

# JWT Authentication Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ActivityWatch Configuration
ACTIVITYWATCH_HOST=http://localhost:5600
```

### Example configurations:

**Local PostgreSQL:**
```env
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/timesheet
```

**Remote PostgreSQL:**
```env
DATABASE_URL=postgresql://user:password@your-server.com:5432/timesheet_db
```

**With SSL (recommended for production):**
```env
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
```

## 2. Database Setup

Run the PostgreSQL setup script to create the necessary tables:

```bash
# Navigate to backend directory
cd backend

# Run the PostgreSQL setup script
python setup_postgres.py
```

This script will:
- ✅ Test your database connection
- ✅ Create the required tables (`users`, `activity_records`)
- ✅ Create a test admin user (if no users exist)
- ✅ Verify everything is working

## 3. Tables Created

The setup will create these tables in your PostgreSQL database:

### `users` table:
- `id` (Primary Key)
- `username` (Unique)
- `email` (Unique)
- `hashed_password`
- `created_at`

### `activity_records` table:
- `id` (Primary Key)
- `user_id` (Foreign Key to users)
- `application_name`
- `window_title`
- `url` (for browser activities)
- `category` (browser, development, productivity, etc.)
- `duration` (in seconds)
- `timestamp`
- `created_at`

## 4. Verify Setup

After running the setup script, you should see:

```
✅ Connected to PostgreSQL: PostgreSQL 15.x...
✅ Tables created successfully!
✅ Test user created: admin (ID: 1)
🎉 Database setup completed successfully!
```

## 5. Start the Application

```bash
# Start backend (from root directory)
python run_backend.py

# Start frontend (in another terminal)
cd frontend
npm start
```

## 6. Login

Use the test credentials created during setup:
- **Username:** `admin`
- **Password:** `admin123`

Or create a new account using the registration page.

## Troubleshooting

### Connection Issues

**Error: "could not connect to server"**
- Ensure PostgreSQL is running
- Check host, port, username, and password in DATABASE_URL
- Verify firewall settings

**Error: "database does not exist"**
- Create the database first: `createdb your_database_name`
- Or use an existing database name in DATABASE_URL

**Error: "authentication failed"**
- Check username and password in DATABASE_URL
- Ensure the user has proper permissions

### Permission Issues

**Error: "permission denied"**
- Grant necessary permissions to your user:
```sql
GRANT CREATE, CONNECT ON DATABASE your_database TO your_user;
GRANT CREATE ON SCHEMA public TO your_user;
```

### SSL Issues

**Error: "SSL connection required"**
- Add `?sslmode=require` to your DATABASE_URL
- Or use `?sslmode=disable` for local development (not recommended for production)

## Database Migration

If you have existing data in your PostgreSQL database, the setup script will:
- ✅ Preserve existing data
- ✅ Only create missing tables
- ✅ Not modify existing tables

## Production Considerations

For production deployment:

1. **Use strong credentials:**
   ```env
   SECRET_KEY=very-long-random-string-at-least-32-characters
   ```

2. **Enable SSL:**
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
   ```

3. **Use connection pooling:**
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/db?pool_size=20&max_overflow=10
   ```

4. **Set proper environment:**
   ```env
   ENVIRONMENT=production
   ```

## Backup Recommendations

Regular backups of your timesheet data:

```bash
# Backup
pg_dump your_database_name > timesheet_backup.sql

# Restore
psql your_database_name < timesheet_backup.sql
```








