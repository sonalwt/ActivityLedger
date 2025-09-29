@echo off
echo PostgreSQL Setup for Timesheet Application
echo ==========================================
echo.

echo This script will help you configure the timesheet application for PostgreSQL.
echo.

echo Step 1: Environment Configuration
echo ---------------------------------
if not exist .env (
    echo Creating .env file...
    echo # PostgreSQL Database Configuration > .env
    echo DATABASE_URL=postgresql://username:password@localhost:5432/timesheet >> .env
    echo. >> .env
    echo # JWT Authentication Settings >> .env
    echo SECRET_KEY=your-super-secret-key-change-this-in-production >> .env
    echo ALGORITHM=HS256 >> .env
    echo ACCESS_TOKEN_EXPIRE_MINUTES=30 >> .env
    echo. >> .env
    echo # ActivityWatch Configuration >> .env
    echo ACTIVITYWATCH_HOST=http://localhost:5600 >> .env
    echo.
    echo ✅ Created .env file
) else (
    echo .env file already exists
)

echo.
echo ⚠️  IMPORTANT: Edit the .env file with your PostgreSQL credentials:
echo    - Replace 'username' with your PostgreSQL username
echo    - Replace 'password' with your PostgreSQL password  
echo    - Replace 'timesheet' with your database name
echo.

set /p continue="Press Enter to continue after updating .env file..."

echo.
echo Step 2: Installing Python Dependencies
echo -------------------------------------
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Step 3: Database Setup
echo ---------------------
echo Setting up PostgreSQL tables...
cd backend
python setup_postgres.py
cd ..

echo.
echo Step 4: Frontend Setup
echo ---------------------
echo Installing frontend dependencies...
cd frontend
npm install
cd ..

echo.
echo ✅ Setup Complete!
echo.
echo To start the application:
echo 1. Backend:  run_backend.bat
echo 2. Frontend: run_frontend.bat
echo 3. Open:     http://localhost:3000
echo.
echo Default login: admin / admin123
echo.
pause
