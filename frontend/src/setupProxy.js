const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Get URLs from environment variables
  const API_URL = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';
  const AW_API_BASE_URL = process.env.REACT_APP_AW_API_URL || 'http://localhost:5600/api/0';
  
  // Extract base URL for ActivityWatch proxy (remove /api/0 part)
  const AW_BASE_URL = AW_API_BASE_URL.replace('/api/0', '');
  
  console.log(`🔧 Setting up proxies:`);
  console.log(`   Backend API: ${API_URL}`);
  console.log(`   ActivityWatch: ${AW_BASE_URL}`);
  
  // Proxy for your backend API (including auth)
  app.use(
    ['/token', '/auth', '/login', '/activity-data', '/activity-summary', '/top-window-titles', '/productivity-analysis', '/daily-hours', '/developers', '/register', '/users/me'],
    createProxyMiddleware({
      target: API_URL,
      changeOrigin: true,
    })
  );

  // Proxy for ActivityWatch API
  app.use(
    '/aw-api',
    createProxyMiddleware({
      target: AW_BASE_URL,
      changeOrigin: true,
      pathRewrite: {
        '^/aw-api': '/api/0',
      },
    })
  );
};