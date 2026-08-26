// Jarvis Screen Dashboard JavaScript

// DOM Elements
const screenClock = document.getElementById('screenClock');
const screenDate = document.getElementById('screenDate');
const weatherTemp = document.getElementById('weatherTemp');
const weatherDesc = document.getElementById('weatherDesc');
const weatherIcon = document.getElementById('weatherIcon');

const screenRecovery = document.getElementById('screenRecovery');
const screenSleep = document.getElementById('screenSleep');
const screenHRV = document.getElementById('screenHRV');
const screenRHR = document.getElementById('screenRHR');

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
    
    // Time format (HH:MM)
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    screenClock.textContent = `${hours}:${minutes}`;
    
    // Date format (Wednesday, Aug 26)
    const options = { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' };
    screenDate.textContent = now.toLocaleDateString(undefined, options);
}

// 2. WEATHER FETCHING (Rionegro)
async function fetchWeather() {
    try {
        const response = await fetch('/api/weather');
        if (!response.ok) throw new Error('Weather fetch failed');
        const data = await response.json();
        
        if (data && data.temperature !== undefined) {
            weatherTemp.textContent = `${Math.round(data.temperature)}°C`;
            const weatherCondition = mapWeatherCode(data.weathercode);
            weatherDesc.textContent = weatherCondition.desc;
            
            // Update icon
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

// 3. WHOOP METRICS FETCHING (Latest)
async function fetchWhoopMetrics() {
    try {
        // Query last 7 days of data to guarantee we grab the most recent non-empty record
        const [recoveryList, sleepsList] = await Promise.all([
            fetch('/api/recovery?days=7').then(res => res.json()),
            fetch('/api/sleeps?days=7').then(res => res.json())
        ]);
        
        // Find latest valid recovery record
        const latestRecovery = recoveryList.reverse().find(r => r.recovery_score !== null);
        if (latestRecovery) {
            screenRecovery.textContent = `${latestRecovery.recovery_score}%`;
            screenHRV.textContent = latestRecovery.hrv_rmssd ? `${Math.round(latestRecovery.hrv_rmssd)} ms` : '-- ms';
            screenRHR.textContent = latestRecovery.resting_heart_rate ? `${latestRecovery.resting_heart_rate} bpm` : '-- bpm';
            
            // Color code recovery
            screenRecovery.className = 'metric-val';
            if (latestRecovery.recovery_score >= 67) {
                screenRecovery.classList.add('text-green');
            } else if (latestRecovery.recovery_score >= 34) {
                screenRecovery.classList.add('text-orange');
            } else {
                screenRecovery.classList.add('text-pink'); // using pink for red/poor recovery
            }
        }
        
        // Find latest valid sleep record
        const latestSleep = sleepsList.reverse().find(s => s.sleep_performance_percentage !== null);
        if (latestSleep) {
            screenSleep.textContent = `${latestSleep.sleep_performance_percentage}%`;
        }
    } catch (err) {
        console.error('Error fetching WHOOP metrics:', err);
    }
}

// 4. HABITS TRACKING
function getTodayDateString() {
    const now = new Date();
    // Get YYYY-MM-DD format in local timezone
    const offset = now.getTimezoneOffset();
    const localDate = new Date(now.getTime() - (offset * 60 * 1000));
    return localDate.toISOString().split('T')[0];
}

async function fetchHabits() {
    const today = getTodayDateString();
    try {
        const response = await fetch(`/api/habits?date=${today}`);
        if (!response.ok) throw new Error('Failed to load habits');
        const habits = await response.json();
        
        // Update states
        Object.keys(habitsState).forEach(habitId => {
            habitsState[habitId] = !!habits[habitId];
            updateHabitUI(habitId, habitsState[habitId]);
        });
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

async function toggleHabit(habitId) {
    const today = getTodayDateString();
    const btn = document.getElementById(`habit_${habitId}`);
    if (!btn) return;

    // Optimistically update UI
    const targetState = !habitsState[habitId];
    updateHabitUI(habitId, targetState);

    try {
        const response = await fetch('/api/habits/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: today,
                habit_id: habitId
            })
        });
        
        if (!response.ok) throw new Error('Toggle request failed');
        const result = await response.json();
        
        // Confirm real state
        habitsState[habitId] = result.completed;
        updateHabitUI(habitId, result.completed);
        
        showToast(`${habitId.charAt(0).toUpperCase() + habitId.slice(1)} ${result.completed ? 'completed!' : 'reset.'}`);
    } catch (err) {
        console.error('Error toggling habit:', err);
        // Rollback state on error
        updateHabitUI(habitId, habitsState[habitId]);
        showToast('Error saving habit completion.', true);
    }
}

// Toast Notifications
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

// 5. INITIALIZE AND START TIMER/INTERVALS
updateTime();
setInterval(updateTime, 1000); // Update clock every second

// Fetch data
fetchWeather();
fetchWhoopMetrics();
fetchHabits();

// Autorefresh dashboard metrics & weather every 10 minutes
setInterval(() => {
    fetchWeather();
    fetchWhoopMetrics();
    fetchHabits();
}, 600000);
