const API_BASE = `${window.location.origin}/api`;
let yieldChart = null;

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function normalizePriorityClass(priority) {
    const normalized = String(priority || '').toLowerCase();
    return ['high', 'medium', 'low'].includes(normalized) ? normalized : 'low';
}

function showMessage(elementId, message, type = 'error') {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (!message) {
        element.className = 'inline-message';
        element.textContent = '';
        return;
    }

    element.className = `inline-message ${type}`;
    element.textContent = message;
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, options);
    let data = {};
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        data = await response.json();
    }

    if (!response.ok) {
        const message = data?.error?.message || `Request failed with status ${response.status}`;
        throw new Error(message);
    }

    return data;
}

function renderLoading(elementId, text = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="alert-item low"><div class="alert-message">${text}</div></div>`;
    }
}

async function fetchDashboard() {
    try {
        const data = await apiRequest('/dashboard');
        document.getElementById('soilMoisture').textContent = `${data.soil_moisture}%`;
        document.getElementById('temperature').textContent = `${data.temperature}°C`;
        document.getElementById('npkLevels').textContent = `N:${data.npk_levels.n} P:${data.npk_levels.p} K:${data.npk_levels.k}`;
        document.getElementById('cropHealth').textContent = `${data.crop_health}%`;
    } catch (error) {
        showMessage('globalMessage', error.message, 'error');
    }
}

function statusClassForField(status) {
    if (['Healthy', 'Excellent', 'Optimal'].includes(status)) return 'status-optimal';
    if (status === 'Needs Water') return 'status-warning';
    return 'status-normal';
}

async function fetchFields() {
    const fieldsGrid = document.getElementById('fieldsGrid');
    const fieldSelect = document.getElementById('fieldSelect');
    fieldsGrid.innerHTML = '<div class="field-card">Loading fields...</div>';
    try {
        const fields = await apiRequest('/fields');
        fieldSelect.innerHTML = '<option value="">Choose a field...</option>';
        fieldsGrid.innerHTML = '';

        fields.forEach((field) => {
            fieldSelect.insertAdjacentHTML('beforeend', `<option value="${field.id}">${escapeHtml(field.name)}</option>`);
            fieldsGrid.insertAdjacentHTML('beforeend', `
                <div class="field-card">
                    <div class="field-name">${escapeHtml(field.name)}</div>
                    <div class="field-info">
                        <span class="field-info-label">📏 Area:</span>
                        <span>${escapeHtml(field.area)} hectares</span>
                    </div>
                    <div class="field-info">
                        <span class="field-info-label">💧 Moisture:</span>
                        <span>${escapeHtml(field.moisture)}%</span>
                    </div>
                    <div class="field-info">
                        <span class="field-info-label">🌡️ Temp:</span>
                        <span>${escapeHtml(field.temperature)}°C</span>
                    </div>
                    <div class="status-badge ${statusClassForField(field.status)}" style="margin-top: 10px;">${escapeHtml(field.status)}</div>
                </div>
            `);
        });
    } catch (error) {
        fieldsGrid.innerHTML = '';
        showMessage('globalMessage', error.message, 'error');
    }
}

async function fetchCropYieldForecast() {
    const canvas = document.getElementById('yieldChart');
    if (typeof window.Chart === 'undefined') {
        showMessage('globalMessage', 'Chart library failed to load. Forecast chart is temporarily unavailable.', 'error');
        return;
    }
    const ctx = canvas.getContext('2d');
    try {
        const data = await apiRequest('/crop-yield-forecast');
        const labels = [];
        const datasets = [];
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c'];
        let colorIndex = 0;

        for (const [field, forecast] of Object.entries(data)) {
            if (labels.length === 0) labels.push(...forecast.dates);
            datasets.push({
                label: field,
                data: forecast.yields,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: `${colors[colorIndex % colors.length]}20`,
                tension: 0.4,
                fill: true
            });
            colorIndex += 1;
        }

        if (yieldChart) yieldChart.destroy();

        yieldChart = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: true, position: 'top' } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Yield (kg/hectare)' }
                    }
                }
            }
        });
    } catch (error) {
        showMessage('globalMessage', error.message, 'error');
    }
}

async function fetchAlerts() {
    const container = document.getElementById('alertsContainer');
    renderLoading('alertsContainer', 'Loading alerts...');
    try {
        const alerts = await apiRequest('/alerts');
        if (!alerts.length) {
            container.innerHTML = '<div class="alert-item low"><div class="alert-message">✓ All systems normal</div></div>';
            return;
        }

        container.innerHTML = '';
        alerts.forEach((alert) => {
            container.insertAdjacentHTML('beforeend', `
                <div class="alert-item ${normalizePriorityClass(alert.priority)}">
                    <div class="alert-message">⚠️ ${escapeHtml(alert.message)}</div>
                    <div class="alert-recommendation">Recommended: ${escapeHtml(alert.recommendation)}</div>
                </div>
            `);
        });
    } catch (error) {
        container.innerHTML = '';
        showMessage('globalMessage', error.message, 'error');
    }
}

async function fetchWeather() {
    const container = document.getElementById('weatherForecast');
    container.innerHTML = '<div class="weather-day">Loading weather...</div>';
    try {
        const weather = await apiRequest('/weather');
        container.innerHTML = '';
        weather.forEach((day) => {
            const weatherDate = new Date(`${day.date}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            container.insertAdjacentHTML('beforeend', `
                <div class="weather-day">
                    <div class="weather-date">${escapeHtml(weatherDate)}</div>
                    <div class="weather-condition">${escapeHtml(day.condition)}</div>
                    <div class="weather-temp">${escapeHtml(day.min_temp)}°C - ${escapeHtml(day.max_temp)}°C</div>
                    <div class="weather-condition">Humidity: ${escapeHtml(day.humidity)}%</div>
                </div>
            `);
        });
    } catch (error) {
        container.innerHTML = '';
        showMessage('globalMessage', error.message, 'error');
    }
}

function validateIrrigationInput(fieldId, duration, waterVolume) {
    if (!fieldId) return 'Please select a field';
    if (Number.isNaN(duration) || Number.isNaN(waterVolume)) {
        return 'Duration and water volume must be valid numbers';
    }
    if (!Number.isInteger(duration) || duration < 5 || duration > 120) {
        return 'Duration must be an integer between 5 and 120 minutes';
    }
    if (!Number.isFinite(waterVolume) || waterVolume < 100 || waterVolume > 5000) {
        return 'Water volume must be between 100 and 5000 liters';
    }
    return '';
}

async function startIrrigation() {
    showMessage('irrigationMessage', '');
    const fieldId = Number.parseInt(document.getElementById('fieldSelect').value, 10);
    const duration = Number.parseInt(document.getElementById('irrigationDuration').value, 10);
    const waterVolume = Number.parseFloat(document.getElementById('waterVolume').value);

    const validationError = validateIrrigationInput(fieldId, duration, waterVolume);
    if (validationError) {
        showMessage('irrigationMessage', validationError, 'error');
        return;
    }

    try {
        const result = await apiRequest('/irrigation/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field_id: fieldId,
                duration,
                water_volume: waterVolume
            })
        });

        showMessage(
            'irrigationMessage',
            `Irrigation started. Scheduled for ${new Date(result.scheduled_time).toLocaleTimeString()}.`,
            'success'
        );
        await Promise.all([fetchDashboard(), fetchFields(), fetchAlerts()]);
    } catch (error) {
        showMessage('irrigationMessage', error.message, 'error');
    }
}

async function initializePage() {
    showMessage('globalMessage', '');
    await Promise.all([
        fetchDashboard(),
        fetchFields(),
        fetchCropYieldForecast(),
        fetchAlerts(),
        fetchWeather()
    ]);

    setInterval(fetchDashboard, 30000);
    setInterval(fetchAlerts, 30000);
}

window.addEventListener('load', () => {
    const irrigationBtn = document.getElementById('startIrrigationBtn');
    irrigationBtn.addEventListener('click', startIrrigation);
    initializePage();
});
