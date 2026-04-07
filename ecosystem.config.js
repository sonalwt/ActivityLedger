module.exports = {
  apps: [
    {
      name: "activityledger-backend",
      cwd: "/var/www/html/ActivityLedger/backend",
      script: "/var/www/html/ActivityLedger/venv/bin/uvicorn",
      args: "main:app --host 127.0.0.1 --port 8090 --workers 2",
      interpreter: "none",
      env: {
        PATH: "/var/www/html/ActivityLedger/venv/bin:" + process.env.PATH,
      },
      env_file: "/var/www/html/ActivityLedger/backend/.env.production",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: "activityledger-frontend",
      cwd: "/var/www/html/ActivityLedger/frontend",
      script: "node_modules/.bin/serve",
      args: "-s build -l 3000",
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
    },
  ],
};
