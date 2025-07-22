// 전역 변수
let isRunning = false;
let dataUpdateInterval;
let distanceData = [];
let filteredData = [];
let timeLabels = [];
let chart;
let movingAverageWindow = 5;

// DOM 요소
const elements = {
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    clearBtn: document.getElementById('clearBtn'),
    intervalRange: document.getElementById('intervalRange'),
    intervalValue: document.getElementById('intervalValue'),
    intervalDisplay: document.getElementById('intervalDisplay'),
    closeThreshold: document.getElementById('closeThreshold'),
    farThreshold: document.getElementById('farThreshold'),
    currentDistance: document.getElementById('currentDistance'),
    filteredDistance: document.getElementById('filteredDistance'),
    statusText: document.getElementById('statusText'),
    warningIndicator: document.getElementById('warningIndicator'),
    showRaw: document.getElementById('showRaw'),
    showFiltered: document.getElementById('showFiltered'),
    sensorModeBadge: document.getElementById('sensorModeBadge')
};

// API 통신 함수
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`/api/${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error(`API 호출 실패 (${endpoint}):`, error);
        return { success: false, message: '서버 통신에 실패했습니다.' };
    }
}

// 차트 초기화
function initChart() {
    const ctx = document.getElementById('distanceChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [
                {
                    label: '실시간 측정값',
                    data: distanceData,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: false
                },
                {
                    label: '필터링된 값',
                    data: filteredData,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '시간별 거리 측정값'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '시간'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '거리 (cm)'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

// 이동평균 계산
function calculateMovingAverage(data, window) {
    if (data.length < window) return data[data.length - 1] || 0;
    const slice = data.slice(-window);
    return slice.reduce((sum, val) => sum + val, 0) / window;
}

// 경고 상태 업데이트
function updateWarningStatus(status) {
    let statusText, indicatorClass, color;

    switch(status) {
        case 'close':
            statusText = '가까움';
            indicatorClass = 'warning-close';
            color = '#e74c3c';
            break;
        case 'far':
            statusText = '멀음';
            indicatorClass = 'warning-far';
            color = '#f39c12';
            break;
        default:
            statusText = '정상';
            indicatorClass = 'warning-normal';
            color = '#27ae60';
    }

    elements.statusText.textContent = statusText;
    elements.statusText.style.color = color;
    elements.warningIndicator.className = `warning-indicator ${indicatorClass}`;
}

// 데이터 추가 (증분 업데이트)
function addNewData(newReading) {
    if (!newReading) return;

    // 새 데이터 추가
    distanceData.push(newReading.distance);
    timeLabels.push(newReading.timestamp);

    // 최대 데이터 포인트 수 제한 (50개)
    if (distanceData.length > 50) {
        distanceData.shift();
        timeLabels.shift();
    }

    // 필터링된 데이터 계산
    const slice = distanceData.slice(-movingAverageWindow);
    const filtered = calculateMovingAverage(slice, Math.min(movingAverageWindow, slice.length));
    filteredData.push(filtered);

    // 필터링된 데이터도 제한
    if (filteredData.length > 50) {
        filteredData.shift();
    }

    // UI 업데이트
    elements.currentDistance.textContent = newReading.distance.toFixed(1) + ' cm';
    elements.filteredDistance.textContent = filtered.toFixed(1) + ' cm';
    updateWarningStatus(newReading.status);

    // 차트 업데이트
    updateChart();
}

// 차트 업데이트
function updateChart() {
    chart.data.labels = timeLabels;
    chart.data.datasets[0].data = distanceData;
    chart.data.datasets[1].data = filteredData;
    chart.data.datasets[0].hidden = !elements.showRaw.checked;
    chart.data.datasets[1].hidden = !elements.showFiltered.checked;
    chart.update('none');
}

// 실시간 데이터 가져오기 (증분 업데이트)
async function fetchLatestData() {
    const result = await apiCall('data');
    if (result.success && result.data) {
        addNewData(result.data);
        isRunning = result.is_running;
        updateButtonStates();
    }
}

// 시스템 상태 가져오기
async function fetchStatus() {
    const result = await apiCall('status');
    if (result.success) {
        const { system } = result;

        // 센서 모드 표시
        const badge = elements.sensorModeBadge;
        if (system.sensor_mode === 'simulation') {
            badge.textContent = '시뮬레이션 모드';
            badge.className = 'sensor-mode-badge mode-simulation';
        } else {
            badge.textContent = '하드웨어 모드';
            badge.className = 'sensor-mode-badge mode-hardware';
        }

        isRunning = system.is_running;
        updateButtonStates();
    }
}

// 버튼 상태 업데이트
function updateButtonStates() {
    elements.startBtn.disabled = isRunning;
    elements.stopBtn.disabled = !isRunning;
}

// 측정 시작
async function startMeasurement() {
    const result = await apiCall('start', 'POST');
    if (result.success) {
        isRunning = true;
        updateButtonStates();
        // 현재 설정된 간격에 맞춰 실시간 데이터 업데이트 시작
        const intervalMs = parseFloat(elements.intervalRange.value) * 1000;
        dataUpdateInterval = setInterval(fetchLatestData, Math.max(100, intervalMs)); // 최소 100ms
        console.log(`측정이 시작되었습니다. 업데이트 간격: ${intervalMs}ms`);
    } else {
        alert(result.message || '측정 시작에 실패했습니다.');
    }
}

// 측정 중지
async function stopMeasurement() {
    const result = await apiCall('stop', 'POST');
    if (result.success) {
        isRunning = false;
        updateButtonStates();
        // 실시간 데이터 업데이트 중지
        if (dataUpdateInterval) {
            clearInterval(dataUpdateInterval);
            dataUpdateInterval = null;
        }
        console.log('측정이 중지되었습니다.');
    } else {
        alert(result.message || '측정 중지에 실패했습니다.');
    }
}

// 데이터 초기화
async function clearData() {
    const result = await apiCall('clear', 'POST');
    if (result.success) {
        distanceData.length = 0;
        filteredData.length = 0;
        timeLabels.length = 0;

        elements.currentDistance.textContent = '-- cm';
        elements.filteredDistance.textContent = '-- cm';
        elements.statusText.textContent = '정상';
        elements.statusText.style.color = '#27ae60';
        elements.warningIndicator.className = 'warning-indicator warning-normal';

        chart.update();
        console.log('데이터가 초기화되었습니다.');
    } else {
        alert(result.message || '데이터 초기화에 실패했습니다.');
    }
}

// 설정 업데이트
async function updateConfig() {
    const config = {
        interval: parseFloat(elements.intervalRange.value),
        close_threshold: parseFloat(elements.closeThreshold.value),
        far_threshold: parseFloat(elements.farThreshold.value)
    };

    const result = await apiCall('config', 'POST', config);
    if (result.success) {
        // 측정 중일 때 데이터 업데이트 간격도 변경
        if (isRunning && dataUpdateInterval) {
            clearInterval(dataUpdateInterval);
            const intervalMs = config.interval * 1000;
            dataUpdateInterval = setInterval(fetchLatestData, Math.max(100, intervalMs)); // 최소 100ms
            console.log(`설정이 업데이트되었습니다. 새 업데이트 간격: ${intervalMs}ms`);
        } else {
            console.log('설정이 업데이트되었습니다.');
        }
    } else {
        alert(result.message || '설정 업데이트에 실패했습니다.');
    }
}

// 간격 변경 처리
function updateInterval() {
    const value = parseFloat(elements.intervalRange.value);
    elements.intervalValue.textContent = value.toFixed(1) + '초';
    elements.intervalDisplay.textContent = value.toFixed(1) + '초';
}

// 이벤트 리스너 설정
function setupEventListeners() {
    elements.startBtn.addEventListener('click', startMeasurement);
    elements.stopBtn.addEventListener('click', stopMeasurement);
    elements.clearBtn.addEventListener('click', clearData);
    elements.intervalRange.addEventListener('input', updateInterval);
    elements.intervalRange.addEventListener('change', updateConfig);
    elements.closeThreshold.addEventListener('change', updateConfig);
    elements.farThreshold.addEventListener('change', updateConfig);
    elements.showRaw.addEventListener('change', updateChart);
    elements.showFiltered.addEventListener('change', updateChart);
}

// 초기화
async function init() {
    initChart();
    setupEventListeners();
    updateInterval();

    // 초기 상태 로드
    await fetchStatus();

    console.log('초음파 센서 대시보드 초기화 완료');
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', init);

// 페이지 언로드 시 측정 중지
window.addEventListener('beforeunload', () => {
    if (isRunning) {
        apiCall('stop', 'POST');
    }
}); 