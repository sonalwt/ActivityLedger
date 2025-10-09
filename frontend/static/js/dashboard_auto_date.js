// dashboard_auto_date.js
// Enhanced dashboard that automatically shows the latest date with data

let currentDeveloperId = null;
let categoryChart = null;
let trendChart = null;
let productivityRingChart = null;

// Color palette for categories
const categoryColors = {
    'Project': '#6366f1',
    'Cloud': '#8b5cf6',
    'Development': '#3b82f6',
    'Browsing': '#f59e0b',
    'Communication': '#10b981',
    'File Management': '#ef4444',
    'Other': '#6b7280'
};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDateSelector();
    loadDevelopers();
    setupEventListeners();
});

// Initialize date selector - ENHANCED VERSION
async function initializeDateSelector() {
    const dateSelector = document.getElementById('dateSelector');
    const today = new Date().toISOString().split('T')[0];
    dateSelector.max = today;
    
    // Try to find the latest date with data
    try {
        const response = await fetch('/api/latest-data-date');
        if (response.ok) {
            const data = await response.json();
            if (data.latest_date) {
                dateSelector.value = data.latest_date;
                console.log('Set date to latest data:', data.latest_date);
                
                // Show a notification if date is not today
                if (data.latest_date !== today) {
                    showDateNotification(data.latest_date);
                }
                return;
            }
        }
    } catch (error) {
        console.error('Error fetching latest date:', error);
    }
    
    // Fallback to today's date
    dateSelector.value = today;
}

// Show notification about date
function showDateNotification(date) {
    const notification = document.createElement('div');
    notification.className = 'date-notification';
    notification.innerHTML = `
        <i class="fas fa-info-circle"></i>
        <span>Showing data for ${date} (latest available)</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add CSS for notification
    const style = document.createElement('style');
    style.textContent = `
        .date-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #3b82f6;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
            z-index: 1000;
        }
        .date-notification button {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            margin-left: 10px;
        }
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => notification.remove(), 5000);
}

// Load developers list
async function loadDevelopers() {
    try {
        const response = await fetch('/api/developers');
        if (!response.ok) throw new Error('Failed to load developers');
        
        const developers = await response.json();
        const selector = document.getElementById('developerSelector');
        
        developers.forEach(dev => {
            const option = document.createElement('option');
            option.value = dev.id;
            option.textContent = dev.name;
            selector.appendChild(option);
        });
        
        // Auto-select first developer
        if (developers.length > 0) {
            selector.value = developers[0].id;
            currentDeveloperId = developers[0].id;
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error loading developers:', error);
        showError('Failed to load developers list');
    }
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('developerSelector').addEventListener('change', function(e) {
        currentDeveloperId = e.target.value;
        if (currentDeveloperId) {
            loadDashboardData();
        }
    });
    
    document.getElementById('dateSelector').addEventListener('change', function() {
        if (currentDeveloperId) {
            loadDashboardData();
        }
    });
}

// Load dashboard data
async function loadDashboardData() {
    if (!currentDeveloperId) return;
    
    showLoading(true);
    
    try {
        const date = document.getElementById('dateSelector').value;
        const response = await fetch(`/api/dashboard/${currentDeveloperId}?date=${date}`);
        
        if (!response.ok) throw new Error('Failed to load dashboard data');
        
        const data = await response.json();
        
        // Check if data is empty
        if (data.total_duration === 0) {
            // Try to find a date with data
            const dateResponse = await fetch(`/api/developer-dates/${currentDeveloperId}`);
            if (dateResponse.ok) {
                const dates = await dateResponse.json();
                if (dates.available_dates && dates.available_dates.length > 0) {
                    // Switch to the latest date with data
                    document.getElementById('dateSelector').value = dates.available_dates[0];
                    showDateNotification(`No data for selected date. Switched to ${dates.available_dates[0]}`);
                    loadDashboardData();
                    return;
                }
            }
        }
        
        updateDashboard(data);
        
        // Load weekly trend
        loadWeeklyTrend();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data');
    } finally {
        showLoading(false);
    }
}

// Update dashboard with data
function updateDashboard(data) {
    // Update metrics with better formatting
    const productivityScore = data.productivity_score || 0;
    const totalMinutes = data.total_duration || 0;
    const totalHours = (totalMinutes / 60).toFixed(1);
    
    document.getElementById('productivityScore').textContent = productivityScore.toFixed(1);
    
    // Show hours and minutes
    const hours = Math.floor(totalMinutes / 60);
    const minutes = Math.floor(totalMinutes % 60);
    if (hours > 0) {
        document.getElementById('totalTime').innerHTML = `${hours}h ${minutes}m`;
    } else {
        document.getElementById('totalTime').innerHTML = `${minutes}`;
    }
    
    // Update productivity ring
    updateProductivityRing(productivityScore);
    
    // Update top category
    if (data.chart_data && data.chart_data.categories && data.chart_data.categories.length > 0) {
        document.getElementById('topCategory').textContent = data.chart_data.categories[0];
        document.getElementById('topCategoryTime').textContent = `${data.chart_data.data[0].toFixed(0)} mins`;
    } else {
        document.getElementById('topCategory').textContent = 'No activity';
        document.getElementById('topCategoryTime').textContent = '0 mins';
    }
    
    // Update category chart
    if (data.chart_data) {
        updateCategoryChart(data.chart_data);
        updateCategoryDetails(data.chart_data);
    }
}

// [Rest of the functions remain the same as original dashboard.js]
// ... updateProductivityRing, getProductivityColor, updateCategoryChart, etc.

// Update productivity ring chart
function updateProductivityRing(score) {
    const ctx = document.getElementById('productivityRing').getContext('2d');
    
    if (productivityRingChart) {
        productivityRingChart.destroy();
    }
    
    productivityRingChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [getProductivityColor(score), '#e5e7eb'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        }
    });
}

// Get color based on productivity score
function getProductivityColor(score) {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#3b82f6';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
}

// Update category distribution chart
function updateCategoryChart(chartData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    const colors = chartData.categories.map(cat => categoryColors[cat] || '#6b7280');
    
    categoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.categories,
            datasets: [{
                label: 'Time (minutes)',
                data: chartData.data,
                backgroundColor: colors.map(color => color + '20'),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toFixed(1)} minutes`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        borderDash: [5, 5]
                    },
                    ticks: {
                        callback: function(value) {
                            return value + ' min';
                        }
                    }
                }
            }
        }
    });
}

// Load weekly productivity trend
async function loadWeeklyTrend() {
    try {
        const response = await fetch(`/api/productivity/${currentDeveloperId}/weekly`);
        if (!response.ok) throw new Error('Failed to load weekly trend');
        
        const data = await response.json();
        updateTrendChart(data);
    } catch (error) {
        console.error('Error loading weekly trend:', error);
    }
}

// Update weekly trend chart
function updateTrendChart(data) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    if (trendChart) {
        trendChart.destroy();
    }
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Productivity Score',
                data: data.scores,
                borderColor: '#6366f1',
                backgroundColor: '#6366f120',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: '#6366f1',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Score: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        borderDash: [5, 5]
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Update category details section
function updateCategoryDetails(chartData) {
    const detailsContainer = document.getElementById('categoryDetails');
    detailsContainer.innerHTML = '';
    
    if (!chartData.details || Object.keys(chartData.details).length === 0) {
        detailsContainer.innerHTML = '<p class="no-data">No activity details available</p>';
        return;
    }
    
    Object.entries(chartData.details).forEach(([category, items]) => {
        if (items.length === 0) return;
        
        const card = createCategoryDetailCard(category, items);
        detailsContainer.appendChild(card);
    });
}

// Create category detail card
function createCategoryDetailCard(category, items) {
    const card = document.createElement('div');
    card.className = 'category-detail-card';
    
    const categoryTitle = category.replace(/_/g, ' ');
    const totalTime = items.reduce((sum, item) => sum + item.duration, 0);
    
    card.innerHTML = `
        <div class="category-detail-header">
            <span class="category-detail-title category-${category}">${categoryTitle}</span>
            <span class="category-detail-total">${(totalTime / 60).toFixed(1)} mins total</span>
        </div>
        <div class="detail-items">
            ${items.map(item => `
                <div class="detail-item">
                    <span class="detail-item-name" title="${item.name}">${item.name}</span>
                    <span class="detail-item-duration">${(item.duration / 60).toFixed(1)} min</span>
                </div>
            `).join('')}
        </div>
    `;
    
    return card;
}

// Refresh dashboard
function refreshDashboard() {
    loadDashboardData();
}

// Show/hide loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.add('show');
    } else {
        overlay.classList.remove('show');
    }
}

// Show error message
function showError(message) {
    // Better error display
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    const style = document.createElement('style');
    style.textContent = `
        .error-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
            z-index: 1000;
        }
        .error-notification button {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            margin-left: 10px;
        }
    `;
    if (!document.querySelector('.error-notification')) {
        document.head.appendChild(style);
    }
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 5000);
}
