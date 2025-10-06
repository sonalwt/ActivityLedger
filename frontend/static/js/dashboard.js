// Dashboard JavaScript
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

// Initialize date selector with today's date
function initializeDateSelector() {
    const dateSelector = document.getElementById('dateSelector');
    const today = new Date().toISOString().split('T')[0];
    dateSelector.value = today;
    dateSelector.max = today;
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
            currentDeveloperId = developers[0].id;  // Keep as string
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
        currentDeveloperId = e.target.value;  // This is already a string
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
    // Update metrics
    document.getElementById('productivityScore').textContent = data.productivity_score.toFixed(1);
    document.getElementById('totalTime').textContent = data.total_duration.toFixed(0);
    
    // Update productivity ring
    updateProductivityRing(data.productivity_score);
    
    // Update top category
    if (data.chart_data.categories.length > 0) {
        document.getElementById('topCategory').textContent = data.chart_data.categories[0];
        document.getElementById('topCategoryTime').textContent = `${data.chart_data.data[0].toFixed(0)} mins`;
    } else {
        document.getElementById('topCategory').textContent = 'No activity';
        document.getElementById('topCategoryTime').textContent = '0 mins';
    }
    
    // Update category chart
    updateCategoryChart(data.chart_data);
    
    // Update category details
    updateCategoryDetails(data.chart_data);
}

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
    // You can implement a toast/notification system here
    alert(message);
}

// Format time duration
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

// Add real-time updates (optional)
// Auto-refresh every 5 minutes without confirmation
setInterval(() => {
    if (currentDeveloperId) {
        loadDashboardData();
    }
}, 300000); // Refresh every 5 minutes
