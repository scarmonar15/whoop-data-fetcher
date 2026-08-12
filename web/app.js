// WHOOP Performance Dashboard JavaScript

let currentDays = 30;
let recoveryChart = null;
let strainChart = null;
let sleepChart = null;

// DOM Elements
const syncBtn = document.getElementById('syncBtn');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');
const timeFilters = document.querySelectorAll('.filter-btn');

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    setupEventListeners();
});

function setupEventListeners() {
    // Time Range Filters
    timeFilters.forEach(btn => {
        btn.addEventListener('click', (e) => {
            timeFilters.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentDays = parseInt(e.target.getAttribute('data-days'));
            updateDashboardData();
        });
    });

    // Sync Button
    syncBtn.addEventListener('click', () => {
        triggerSync();
    });
}

async function initDashboard() {
    showToast('Loading dashboard data...');
    await loadUserProfile();
    await updateDashboardData();
}

async function loadUserProfile() {
    try {
        const response = await fetch('/api/profile');
        if (!response.ok) throw new Error('Failed to load profile');
        const profile = await response.json();
        
        // Update elements
        document.getElementById('userName').textContent = `${profile.first_name} ${profile.last_name}`;
        document.getElementById('userEmail').textContent = profile.email;
        
        // Avatar initials
        const initials = `${profile.first_name[0] || ''}${profile.last_name[0] || ''}`.toUpperCase();
        document.getElementById('userAvatar').textContent = initials || 'WU';
        
        // Height & Weight sub-metrics in workouts card
        document.getElementById('valWeight').textContent = profile.weight_kg ? `${profile.weight_kg.toFixed(1)} kg` : '--';
        document.getElementById('valHeight').textContent = profile.height_meter ? `${profile.height_meter.toFixed(2)} m` : '--';
    } catch (err) {
        console.error('Error loading profile:', err);
    }
}

async function updateDashboardData() {
    showToast(`Loading last ${currentDays} days...`);
    try {
        // Fetch data concurrently
        const [summary, recovery, sleeps, cycles, workouts] = await Promise.all([
            fetch(`/api/summary?days=${currentDays}`).then(res => res.json()),
            fetch(`/api/recovery?days=${currentDays}`).then(res => res.json()),
            fetch(`/api/sleeps?days=${currentDays}`).then(res => res.json()),
            fetch(`/api/cycles?days=${currentDays}`).then(res => res.json()),
            fetch(`/api/workouts?days=${currentDays}`).then(res => res.json())
        ]);

        renderSummaryCards(summary, recovery, sleeps, cycles);
        renderCharts(recovery, sleeps, cycles);
        renderWorkoutsTable(workouts);
        hideToast();
    } catch (err) {
        console.error('Error loading dashboard data:', err);
        showToast('Error loading dashboard data. Check database.', true);
    }
}

function renderSummaryCards(summary, recoveryList, sleepsList, cyclesList) {
    // 1. Recovery
    const latestRecovery = recoveryList[recoveryList.length - 1];
    if (latestRecovery && latestRecovery.recovery_score !== null) {
        const score = latestRecovery.recovery_score;
        const valRecoveryEl = document.getElementById('valRecovery');
        valRecoveryEl.textContent = `${score}%`;
        
        // Set color class based on score
        valRecoveryEl.className = 'card-value';
        if (score >= 67) {
            valRecoveryEl.classList.add('recovery-green');
            document.getElementById('labelRecoveryState').textContent = 'Optimal Recovery';
        } else if (score >= 34) {
            valRecoveryEl.classList.add('recovery-yellow');
            document.getElementById('labelRecoveryState').textContent = 'Adequate Recovery';
        } else {
            valRecoveryEl.classList.add('recovery-red');
            document.getElementById('labelRecoveryState').textContent = 'Poor Recovery';
        }
        
        document.getElementById('valHRV').textContent = latestRecovery.hrv_rmssd ? `${Math.round(latestRecovery.hrv_rmssd)} ms` : '--';
        document.getElementById('valRHR').textContent = latestRecovery.resting_heart_rate ? `${latestRecovery.resting_heart_rate} bpm` : '--';
    } else {
        document.getElementById('valRecovery').textContent = '--%';
        document.getElementById('labelRecoveryState').textContent = 'No Data';
    }

    // 2. Sleep
    const latestSleep = sleepsList[sleepsList.length - 1];
    if (latestSleep && latestSleep.sleep_performance_percentage !== null) {
        document.getElementById('valSleepPerf').textContent = `${latestSleep.sleep_performance_percentage}%`;
        
        // Calculate sleep duration in hours
        const start = new Date(latestSleep.start_time);
        const end = new Date(latestSleep.end_time);
        const diffHrs = (end - start) / (1000 * 60 * 60);
        document.getElementById('valSleepHours').textContent = `${diffHrs.toFixed(1)} hrs`;
        
        document.getElementById('valSleepCons').textContent = latestSleep.sleep_consistency_percentage ? `${latestSleep.sleep_consistency_percentage}%` : '--';
        document.getElementById('valRespRate').textContent = latestSleep.respiratory_rate ? `${latestSleep.respiratory_rate.toFixed(1)} rpm` : '--';
    } else {
        document.getElementById('valSleepPerf').textContent = '--%';
        document.getElementById('valSleepHours').textContent = '--';
    }

    // 3. Strain
    const latestCycle = cyclesList[cyclesList.length - 1];
    if (latestCycle && latestCycle.strain !== null) {
        document.getElementById('valStrain').textContent = latestCycle.strain.toFixed(1);
        document.getElementById('valCalories').textContent = latestCycle.kilocalories ? `${Math.round(latestCycle.kilocalories)} kcal` : '--';
        document.getElementById('valAvgHR').textContent = latestCycle.average_heart_rate ? `${latestCycle.average_heart_rate} bpm` : '--';
        document.getElementById('valMaxHR').textContent = latestCycle.max_heart_rate ? `${latestCycle.max_heart_rate} bpm` : '--';
    } else {
        document.getElementById('valStrain').textContent = '--';
        document.getElementById('valCalories').textContent = '--';
    }

    // 4. Workouts Count
    document.getElementById('valWorkouts').textContent = summary.workouts_count !== undefined ? summary.workouts_count : '--';
}

function calculateRollingAverage(data, windowSize) {
    const averages = [];
    for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - windowSize + 1);
        const windowData = data.slice(start, i + 1);
        const validData = windowData.filter(v => v !== null && v !== undefined);
        if (validData.length === 0) {
            averages.push(null);
        } else {
            const sum = validData.reduce((acc, val) => acc + val, 0);
            averages.push(sum / validData.length);
        }
    }
    return averages;
}

function renderCharts(recoveryList, sleepsList, cyclesList) {
    // 1. RECOVERY TREND CHART (Score + 3D, 7D, 30D averages)
    const recDates = recoveryList.map(r => formatDate(r.date || r.created_at));
    const recScores = recoveryList.map(r => r.recovery_score);
    
    const rec3D = calculateRollingAverage(recScores, 3);
    const rec7D = calculateRollingAverage(recScores, 7);
    const rec30D = calculateRollingAverage(recScores, 30);

    if (recoveryChart) recoveryChart.destroy();
    
    const ctxRec = document.getElementById('recoveryChart').getContext('2d');
    recoveryChart = new Chart(ctxRec, {
        type: 'line',
        data: {
            labels: recDates,
            datasets: [
                {
                    label: 'Daily Recovery (Raw)',
                    data: recScores,
                    showLine: false,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#00e676',
                    pointBorderColor: 'rgba(7, 9, 14, 0.8)',
                    pointBorderWidth: 1.5,
                    borderColor: 'transparent',
                    fill: false
                },
                {
                    label: '3-Day Average',
                    data: rec3D,
                    borderColor: 'rgba(0, 230, 118, 0.4)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '7-Day Average',
                    data: rec7D,
                    borderColor: '#ffea00',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '30-Day Average',
                    data: rec30D,
                    borderColor: '#2979ff',
                    borderWidth: 4,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#ffffff', font: { family: 'Outfit', size: 11 } } }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Recovery Score %', color: '#8e9bb0', font: { family: 'Outfit' } }
                }
            }
        }
    });

    // 2. STRAIN TREND CHART (Score + 3D, 7D, 30D averages)
    const strainDates = cyclesList.map(c => formatDate(c.start_time));
    const strainScores = cyclesList.map(c => c.strain);
    
    const strain3D = calculateRollingAverage(strainScores, 3);
    const strain7D = calculateRollingAverage(strainScores, 7);
    const strain30D = calculateRollingAverage(strainScores, 30);

    if (strainChart) strainChart.destroy();
    
    const ctxStrain = document.getElementById('strainChart').getContext('2d');
    strainChart = new Chart(ctxStrain, {
        type: 'line',
        data: {
            labels: strainDates,
            datasets: [
                {
                    label: 'Daily Strain (Raw)',
                    data: strainScores,
                    showLine: false,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#ff5722',
                    pointBorderColor: 'rgba(7, 9, 14, 0.8)',
                    pointBorderWidth: 1.5,
                    borderColor: 'transparent',
                    fill: false
                },
                {
                    label: '3-Day Average',
                    data: strain3D,
                    borderColor: 'rgba(255, 87, 34, 0.4)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '7-Day Average',
                    data: strain7D,
                    borderColor: '#ff9100',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '30-Day Average',
                    data: strain30D,
                    borderColor: '#ff1744',
                    borderWidth: 4,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#ffffff', font: { family: 'Outfit', size: 11 } } }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } }
                },
                y: {
                    min: 0,
                    max: 21,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Strain (0-21)', color: '#8e9bb0', font: { family: 'Outfit' } }
                }
            }
        }
    });

    // 3. SLEEP TREND CHART (Score + 3D, 7D, 30D averages)
    const sleepDates = sleepsList.map(s => formatDate(s.start_time));
    const sleepScores = sleepsList.map(s => s.sleep_performance_percentage);
    
    const sleep3D = calculateRollingAverage(sleepScores, 3);
    const sleep7D = calculateRollingAverage(sleepScores, 7);
    const sleep30D = calculateRollingAverage(sleepScores, 30);

    if (sleepChart) sleepChart.destroy();
    
    const ctxSleep = document.getElementById('sleepChart').getContext('2d');
    sleepChart = new Chart(ctxSleep, {
        type: 'line',
        data: {
            labels: sleepDates,
            datasets: [
                {
                    label: 'Daily Sleep (Raw)',
                    data: sleepScores,
                    showLine: false,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#2979ff',
                    pointBorderColor: 'rgba(7, 9, 14, 0.8)',
                    pointBorderWidth: 1.5,
                    borderColor: 'transparent',
                    fill: false
                },
                {
                    label: '3-Day Average',
                    data: sleep3D,
                    borderColor: 'rgba(41, 121, 255, 0.4)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '7-Day Average',
                    data: sleep7D,
                    borderColor: '#00e5ff',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: '30-Day Average',
                    data: sleep30D,
                    borderColor: '#7c4dff',
                    borderWidth: 4,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#ffffff', font: { family: 'Outfit', size: 11 } } }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8e9bb0', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Sleep Performance %', color: '#8e9bb0', font: { family: 'Outfit' } }
                }
            }
        }
    });
}

function renderWorkoutsTable(workouts) {
    const tableBody = document.getElementById('workoutsTableBody');
    if (!workouts || workouts.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-table-row">No workout data found in this period.</td>
            </tr>
        `;
        return;
    }

    // Sort workouts descending (newest first)
    workouts.sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

    tableBody.innerHTML = workouts.map(w => {
        const dateObj = new Date(w.start_time);
        const formattedDate = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
        const formattedTime = dateObj.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        
        // Convert sport ID to text (Common WHOOP sports)
        const sportName = getSportName(w.sport_id);

        const strainVal = w.strain ? w.strain.toFixed(1) : '--';
        const avgHr = w.average_heart_rate ? `${w.average_heart_rate} bpm` : '--';
        const maxHr = w.max_heart_rate ? `${w.max_heart_rate} bpm` : '--';
        const cals = w.kilocalories ? `${Math.round(w.kilocalories)} kcal` : '--';
        const dist = w.distance_meter ? `${(w.distance_meter / 1000).toFixed(2)} km` : '--';

        return `
            <tr>
                <td><strong>${formattedDate}</strong><br><span style="font-size: 11px; color: var(--text-secondary);">${formattedTime}</span></td>
                <td><span class="sport-badge">${sportName}</span></td>
                <td><span style="color: var(--accent-strain); font-weight: 600;">${strainVal}</span></td>
                <td>${avgHr}</td>
                <td>${maxHr}</td>
                <td>${cals}</td>
                <td>${dist}</td>
            </tr>
        `;
    }).join('');
}

// Helpers
function formatDate(dateString) {
    if (!dateString) return '';
    const d = new Date(dateString);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function showToast(message, isError = false) {
    toastMessage.textContent = message;
    toast.className = 'toast show';
    
    // Add spinner or alert icon based on status
    const icon = isError ? '<i data-lucide="alert-triangle" style="color: #ff1744"></i>' : '<i data-lucide="loader" class="spin"></i>';
    toast.innerHTML = `${icon} <span id="toastMessage">${message}</span>`;
    lucide.createIcons();

    if (isError) {
        setTimeout(hideToast, 5000);
    }
}

function hideToast() {
    toast.classList.remove('show');
}

async function triggerSync() {
    showToast('Requesting data sync from WHOOP API...');
    try {
        const response = await fetch('/api/sync', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showToast('Sync completed successfully!');
            setTimeout(async () => {
                await updateDashboardData();
            }, 1500);
        } else {
            showToast(`Sync failed: ${result.error || 'Server error'}`, true);
        }
    } catch (err) {
        showToast('Connection error. Server may not be running.', true);
    }
}

// Mapping WHOOP Sport IDs (standard list)
function getSportName(sportId) {
    const sports = {
        "-1": "Active Recovery",
        "0": "Running",
        "1": "Cycling",
        "2": "Swimming",
        "3": "Fitness/Gym",
        "4": "Strength Training",
        "5": "CrossFit",
        "6": "Functional Fitness",
        "7": "Rowing",
        "8": "Yoga",
        "9": "Pilates",
        "10": "Walking",
        "11": "Hiking",
        "12": "Climbing",
        "13": "Walking",
        "14": "Basketball",
        "15": "Soccer",
        "16": "Tennis",
        "17": "Golf",
        "18": "Boxing",
        "19": "Martial Arts",
        "20": "Wrestling",
        "21": "Rugby",
        "22": "Football",
        "23": "Lacrosse",
        "24": "Baseball/Softball",
        "25": "Squash",
        "26": "Badminton",
        "27": "Gymnastics",
        "28": "Dancing",
        "29": "Barre",
        "30": "Equestrian",
        "31": "Skiing",
        "32": "Snowboarding",
        "33": "Cross Country Skiing",
        "34": "Indoor Rowing",
        "35": "Spinning",
        "36": "Indoor Cycling",
        "37": "Indoor Running/Treadmill",
        "38": "Stairmaster",
        "39": "Elliptical",
        "40": "HIIT",
        "44": "Paddleboarding",
        "45": "Surfing",
        "46": "Kayaking",
        "47": "Canoeing",
        "48": "Sailing",
        "49": "Windsurfing",
        "51": "Ice Hockey",
        "52": "Field Hockey",
        "53": "Ice Skating",
        "55": "Snowshoeing",
        "57": "Skateboarding",
        "63": "Ultimate Frisbee",
        "65": "Volleyball",
        "72": "Motocross",
        "76": "Track & Field",
        "82": "Water Polo",
        "83": "Wrestling",
        "84": "Weightlifting",
        "85": "Powerlifting",
        "86": "Kettlebell",
        "87": "Bodyweight",
        "88": "Cardio",
        "91": "Rucking",
        "93": "Obstacle Course Racing",
        "96": "Kickboxing",
        "97": "Jiu Jitsu",
        "98": "Judo",
        "100": "Karate",
        "101": "Taekwondo",
        "113": "Ski Ergometer",
        "114": "Assault Bike",
        "118": "Pickleball",
        "121": "Paddle Tennis",
        "124": "High Intensity Interval Training",
        "125": "Functional Training",
        "126": "Zone 2 Cardio"
    };
    return sports[sportId] || `Sport #${sportId}`;
}
