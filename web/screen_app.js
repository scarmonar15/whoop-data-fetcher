// Jarvis Screen Dashboard JavaScript

// DOM Elements
const screenClock = document.getElementById('screenClock');
const screenDate = document.getElementById('screenDate');
const weatherTemp = document.getElementById('weatherTemp');
const weatherDesc = document.getElementById('weatherDesc');
const weatherIcon = document.getElementById('weatherIcon');

// WHOOP DOM
const screenRecovery = document.getElementById('screenRecovery');
const screenSleep = document.getElementById('screenSleep');
const screenHRV = document.getElementById('screenHRV');
const screenRHR = document.getElementById('screenRHR');

// Mock DOM containers
const agendaList = document.getElementById('agendaList');
const prioritiesList = document.getElementById('prioritiesList');
const commuteList = document.getElementById('commuteList');

// Water Tracker DOM
const waterCurrent = document.getElementById('waterCurrent');
const waterBarFill = document.getElementById('waterBarFill');

// Toast DOM
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

// Initial States
let habitsState = {
    protein: false,
    creatine: false,
    stretching: false,
    core: false
};

// 1. CLOCK & DATE UPDATE
function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    screenClock.textContent = `${hours}:${minutes}`;
    
    const options = { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' };
    screenDate.textContent = now.toLocaleDateString(undefined, options);
}

// 2. WEATHER (Rionegro)
async function fetchWeather() {
    try {
        const response = await fetch('/api/weather');
        if (!response.ok) throw new Error('Weather fetch failed');
        const data = await response.json();
        
        if (data && data.temperature !== undefined) {
            weatherTemp.textContent = `${Math.round(data.temperature)}°C`;
            const weatherCondition = mapWeatherCode(data.weathercode);
            weatherDesc.textContent = weatherCondition.desc;
            weatherIcon.setAttribute('data-lucide', weatherCondition.icon);
            lucide.createIcons();
        }
    } catch (err) {
        console.error('Error fetching weather:', err);
        weatherDesc.textContent = 'Weather Unavailable';
    }
}

function mapWeatherCode(code) {
    const mapping = {
        0: { desc: 'Clear sky', icon: 'sun' },
        1: { desc: 'Mainly clear', icon: 'cloud-sun' },
        2: { desc: 'Partly cloudy', icon: 'cloud-sun' },
        3: { desc: 'Overcast', icon: 'cloud' },
        45: { desc: 'Foggy', icon: 'cloud-drizzle' },
        48: { desc: 'Foggy', icon: 'cloud-drizzle' },
        51: { desc: 'Light drizzle', icon: 'cloud-drizzle' },
        53: { desc: 'Moderate drizzle', icon: 'cloud-drizzle' },
        55: { desc: 'Dense drizzle', icon: 'cloud-drizzle' },
        61: { desc: 'Slight rain', icon: 'cloud-rain' },
        63: { desc: 'Moderate rain', icon: 'cloud-rain' },
        65: { desc: 'Heavy rain', icon: 'cloud-rain' },
        80: { desc: 'Light showers', icon: 'cloud-rain' },
        81: { desc: 'Moderate showers', icon: 'cloud-rain' },
        82: { desc: 'Heavy showers', icon: 'cloud-rain' },
        95: { desc: 'Thunderstorm', icon: 'cloud-lightning' }
    };
    return mapping[code] || { desc: 'Cloudy', icon: 'cloud' };
}

// 3. MOCKED AGENDA (Calendar)
function loadMockAgenda() {
    const events = [
        { time: '09:00 AM', title: 'Daily Sync & Standup' },
        { time: '11:30 AM', title: 'Product Architecture Review' },
        { time: '03:00 PM', title: 'Design System & UI Alignment' }
    ];
    
    agendaList.innerHTML = events.map(e => `
        <div class="agenda-item">
            <div class="agenda-time">${e.time}</div>
            <div class="agenda-title">${e.title}</div>
        </div>
    `).join('');
}

// 4. MOCKED LINEAR PRIORITIES
function loadMockLinearPriorities() {
    const priorities = [
        { key: 'WHOOP-104', title: 'Configure persistent SQLite storage for dashboard analytics', priority: 'high' },
        { key: 'WHOOP-108', title: 'Optimize public metrics API endpoint averages calculation', priority: 'medium' },
        { key: 'WHOOP-111', title: 'Implement daily automated sync background job', priority: 'high' }
    ];
    
    prioritiesList.innerHTML = priorities.map(p => `
        <div class="priority-item">
            <div class="priority-meta">
                <span class="priority-key">${p.key}</span>
                <span class="priority-level">${p.priority}</span>
            </div>
            <div class="priority-title">${p.title}</div>
        </div>
    `).join('');
}

// 5. MOCKED COMMUTES & TRAFFIC (Rionegro)
function loadMockCommuteTraffic() {
    const commutes = [
        { name: 'Mall Indiana', desc: 'Via Las Palmas', time: '24 min', status: 'optimal', color: 'text-green' },
        { name: 'Reserva del Sur', desc: 'Local Route', time: '18 min', status: 'minor delays', color: 'text-orange' },
        { name: 'Mall Llanogrande', desc: 'Via Llanogrande', time: '11 min', status: 'smooth', color: 'text-green' }
    ];
    
    commuteList.innerHTML = commutes.map(c => `
        <div class="commute-item">
            <div class="commute-loc">
                <span class="commute-name">${c.name}</span>
                <span class="commute-desc">${c.desc}</span>
            </div>
            <div class="commute-status">
                <span class="commute-time">${c.time}</span>
                <span class="commute-indicator ${c.color}">${c.status}</span>
            </div>
        </div>
    `).join('');
}

// 6. WHOOP METRICS (Latest from DB)
async function fetchWhoopMetrics() {
    try {
        const [recoveryList, sleepsList] = await Promise.all([
            fetch('/api/recovery?days=7').then(res => res.json()),
            fetch('/api/sleeps?days=7').then(res => res.json())
        ]);
        
        const latestRecovery = recoveryList.reverse().find(r => r.recovery_score !== null);
        if (latestRecovery) {
            screenRecovery.textContent = `${latestRecovery.recovery_score}%`;
            screenHRV.textContent = latestRecovery.hrv_rmssd ? `${Math.round(latestRecovery.hrv_rmssd)} ms` : '-- ms';
            screenRHR.textContent = latestRecovery.resting_heart_rate ? `${latestRecovery.resting_heart_rate} bpm` : '-- bpm';
            
            screenRecovery.className = 'metric-val';
            if (latestRecovery.recovery_score >= 67) {
                screenRecovery.classList.add('text-green');
            } else if (latestRecovery.recovery_score >= 34) {
                screenRecovery.classList.add('text-orange');
            } else {
                screenRecovery.classList.add('text-pink');
            }
        }
        
        const latestSleep = sleepsList.reverse().find(s => s.sleep_performance_percentage !== null);
        if (latestSleep) {
            screenSleep.textContent = `${latestSleep.sleep_performance_percentage}%`;
        }
    } catch (err) {
        console.error('Error fetching WHOOP metrics:', err);
    }
}

// 7. REAL HABITS & HISTORICAL STREAKS (DB)
function getTodayDateString() {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    const localDate = new Date(now.getTime() - (offset * 60 * 1000));
    return localDate.toISOString().split('T')[0];
}

async function fetchHabits() {
    const today = getTodayDateString();
    try {
        // Fetch today's completion status
        const habitsResponse = await fetch(`/api/habits?date=${today}`);
        const habits = await habitsResponse.json();
        
        Object.keys(habitsState).forEach(habitId => {
            habitsState[habitId] = !!habits[habitId];
            updateHabitUI(habitId, habitsState[habitId]);
        });
        
        // Fetch last 7 days history for streaks
        const historyResponse = await fetch(`/api/habits/history?date=${today}&days=7`);
        const historyData = await historyResponse.json();
        
        if (historyData && historyData.dates) {
            Object.keys(habitsState).forEach(habitId => {
                renderHabitStreak(habitId, historyData.dates, historyData.history[habitId] || {});
            });
        }
    } catch (err) {
        console.error('Error fetching habits:', err);
    }
}

function updateHabitUI(habitId, completed) {
    const btn = document.getElementById(`habit_${habitId}`);
    if (!btn) return;
    
    const iconContainer = btn.querySelector('.habit-checkbox');
    if (completed) {
        btn.classList.add('completed');
        iconContainer.innerHTML = '<i data-lucide="check-circle-2" class="habit-icon-check" style="color: #000000"></i>';
    } else {
        btn.classList.remove('completed');
        iconContainer.innerHTML = '<i data-lucide="circle" class="habit-icon-check"></i>';
    }
    lucide.createIcons();
}

function renderHabitStreak(habitId, dates, completions) {
    const container = document.getElementById(`streak_${habitId}`);
    if (!container) return;
    
    // Draw 7 dots
    container.innerHTML = dates.map(date => {
        const completed = !!completions[date];
        return `<div class="streak-dot ${completed ? 'completed' : ''}" title="${date}"></div>`;
    }).join('');
}

async function toggleHabit(habitId) {
    const today = getTodayDateString();
    const targetState = !habitsState[habitId];
    
    updateHabitUI(habitId, targetState);

    try {
        const response = await fetch('/api/habits/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: today, habit_id: habitId })
        });
        
        const result = await response.json();
        habitsState[habitId] = result.completed;
        updateHabitUI(habitId, result.completed);
        
        // Reload streaks to include this update
        fetchHabits();
        
        showToast(`${habitId.charAt(0).toUpperCase() + habitId.slice(1)} ${result.completed ? 'completed!' : 'reset.'}`);
    } catch (err) {
        console.error('Error toggling habit:', err);
        updateHabitUI(habitId, habitsState[habitId]);
        showToast('Error saving habit completion.', true);
    }
}

// 8. REAL HYDRATION TRACKER (DB)
let currentWaterIntake = 0;

async function fetchWaterIntake() {
    const today = getTodayDateString();
    try {
        const response = await fetch(`/api/water?date=${today}`);
        const data = await response.json();
        currentWaterIntake = data.amount_ml || 0;
        updateWaterUI();
    } catch (err) {
        console.error('Error loading water:', err);
    }
}

function updateWaterUI() {
    waterCurrent.textContent = currentWaterIntake;
    const pct = Math.min((currentWaterIntake / 2000) * 100, 100);
    waterBarFill.style.width = `${pct}%`;
}

async function addWater(amount) {
    const today = getTodayDateString();
    // Optimistic UI update
    currentWaterIntake += amount;
    updateWaterUI();
    
    try {
        const response = await fetch('/api/water/increment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: today, increment_ml: amount })
        });
        const result = await response.json();
        currentWaterIntake = result.amount_ml;
        updateWaterUI();
        showToast(`Added ${amount}ml of water.`);
    } catch (err) {
        console.error('Error adding water:', err);
        showToast('Error updating water tracker.', true);
    }
}

async function resetWater() {
    const today = getTodayDateString();
    // Reset means we increment with negative values to reach 0
    const decrement = -currentWaterIntake;
    
    currentWaterIntake = 0;
    updateWaterUI();
    
    try {
        await fetch('/api/water/increment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: today, increment_ml: decrement })
        });
        showToast('Water tracker reset.');
    } catch (err) {
        console.error('Error resetting water:', err);
        showToast('Error resetting water tracker.', true);
    }
}

// 9. MOCKED SPOTIFY TRACK PROGRESS
function runSpotifyMockProgress() {
    const fill = document.getElementById('spotifyProgressFill');
    if (!fill) return;
    
    setInterval(() => {
        let widthPct = parseFloat(fill.style.width);
        if (widthPct >= 100) {
            widthPct = 0; // restart
        } else {
            widthPct += 0.3; // simulate playing
        }
        fill.style.width = `${widthPct}%`;
    }, 1000);
}

// Toast Notification Helper
function showToast(message, isError = false) {
    toastMessage.textContent = message;
    toast.classList.add('show');
    
    if (isError) {
        toast.style.borderColor = '#ff1744';
        toast.style.boxShadow = '0 10px 25px rgba(255, 23, 68, 0.15)';
    } else {
        toast.style.borderColor = 'var(--accent-green)';
        toast.style.boxShadow = '0 10px 25px rgba(0, 230, 118, 0.15)';
    }
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// INITIALIZE
updateTime();
setInterval(updateTime, 1000);

loadMockAgenda();
loadMockLinearPriorities();
loadMockCommuteTraffic();
fetchWeather();
fetchWhoopMetrics();
fetchHabits();
fetchWaterIntake();
runSpotifyMockProgress();

// Refresh live endpoints every 10 minutes
setInterval(() => {
    fetchWeather();
    fetchWhoopMetrics();
    fetchHabits();
    fetchWaterIntake();
}, 600000);
