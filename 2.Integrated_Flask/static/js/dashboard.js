// 전역 변수
let socket;
let currentSpeed = 60;
let isConnected = false;
let activeDirection = null;
let ultrasonicRunning = false;

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeControls();
    loadResolutions();
    startSystemInfoUpdates();
    updateTime();
    setInterval(updateTime, 1000);
});

// Socket.IO 초기화
function initializeSocket() {
    socket = io();

    socket.on('connect', function() {
        console.log('Connected to server');
        isConnected = true;
        showSuccess('서버에 연결되었습니다.');
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        isConnected = false;
        showError('서버와의 연결이 끊어졌습니다.');
        resetActiveDirection();
    });

    socket.on('robot_status', function(data) {
        updateRobotStatus(data);
    });

    socket.on('motor_feedback', function(data) {
        handleMotorFeedback(data);
    });

    socket.on('ultrasonic_data', function(data) {
        updateUltrasonicData(data);
    });
}

// 컨트롤 초기화
function initializeControls() {
    // 방향 패드 버튼 이벤트
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.addEventListener('mousedown', function() {
            const direction = this.dataset.direction;
            sendMotorCommand(direction, currentSpeed);
        });

        btn.addEventListener('mouseup', function() {
            if (this.dataset.direction !== 'stop') {
                sendMotorCommand('stop', 0);
            }
        });

        btn.addEventListener('mouseleave', function() {
            if (this.dataset.direction !== 'stop') {
                sendMotorCommand('stop', 0);
            }
        });
    });

    // 속도 슬라이더
    document.getElementById('speedSlider').addEventListener('input', function() {
        currentSpeed = parseInt(this.value);
        document.getElementById('speedValue').textContent = currentSpeed + '%';
    });

    // 키보드 이벤트
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
}

// 모터 명령 전송
function sendMotorCommand(direction, speed) {
    if (!isConnected) {
        showError('서버에 연결되지 않았습니다.');
        return;
    }

    socket.emit('motor_control', {
        direction: direction,
        speed: speed
    });

    updateActiveDirection(direction);
}

// 활성 방향 업데이트
function updateActiveDirection(direction) {
    // 모든 버튼에서 active 클래스 제거
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 현재 방향 버튼에 active 클래스 추가
    if (direction !== 'stop') {
        const activeBtn = document.querySelector(`[data-direction="${direction}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    }

    activeDirection = direction === 'stop' ? null : direction;
}

// 활성 방향 리셋
function resetActiveDirection() {
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    activeDirection = null;
}

// 모터 피드백 처리
function handleMotorFeedback(data) {
    if (!data.success) {
        showError(data.error || '명령 실행에 실패했습니다.');
        resetActiveDirection();
    }
}

// 키보드 이벤트 처리
function handleKeyDown(event) {
    if (event.repeat) return;

    const keyMap = {
        'ArrowUp': 'forward',
        'ArrowDown': 'backward',
        'ArrowLeft': 'rotate-left',
        'ArrowRight': 'rotate-right',
        ' ': 'stop',
        'Space': 'stop',
        'KeyW': 'forward',
        'KeyS': 'backward',
        'KeyA': 'rotate-left',
        'KeyD': 'rotate-right',
        'KeyQ': 'forward-left',
        'KeyE': 'forward-right',
        'KeyZ': 'backward-left',
        'KeyC': 'backward-right'
    };

    const direction = keyMap[event.code];
    if (direction && direction !== activeDirection) {
        event.preventDefault();
        sendMotorCommand(direction, currentSpeed);
    }

    // 속도 조절 (+, - 키)
    if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        currentSpeed = Math.min(100, currentSpeed + 5);
        document.getElementById('speedSlider').value = currentSpeed;
        document.getElementById('speedValue').textContent = currentSpeed + '%';
    } else if (event.key === '-') {
        event.preventDefault();
        currentSpeed = Math.max(20, currentSpeed - 5);
        document.getElementById('speedSlider').value = currentSpeed;
        document.getElementById('speedValue').textContent = currentSpeed + '%';
    }
}

function handleKeyUp(event) {
    const keyMap = {
        'ArrowUp': 'forward',
        'ArrowDown': 'backward',
        'ArrowLeft': 'rotate-left',
        'ArrowRight': 'rotate-right',
        'KeyW': 'forward',
        'KeyS': 'backward',
        'KeyA': 'rotate-left',
        'KeyD': 'rotate-right',
        'KeyQ': 'forward-left',
        'KeyE': 'forward-right',
        'KeyZ': 'backward-left',
        'KeyC': 'backward-right'
    };

    const direction = keyMap[event.code];
    if (direction === activeDirection) {
        event.preventDefault();
        sendMotorCommand('stop', 0);
    }
}

// 로봇 상태 업데이트
function updateRobotStatus(data) {
    const motorStatus = document.getElementById('motorStatus');
    const cameraStatus = document.getElementById('cameraStatus');
    const ultrasonicStatus = document.getElementById('ultrasonicStatus');

    // 상태 점 업데이트
    updateStatusDot(motorStatus, data.motor_available);
    updateStatusDot(cameraStatus, data.camera_available);
    updateStatusDot(ultrasonicStatus, data.ultrasonic_available);
}

function updateStatusDot(element, isAvailable) {
    element.className = 'status-dot';
    if (isAvailable) {
        element.classList.add('status-dot');
    } else {
        element.classList.add('error');
    }
}

// 해상도 목록 로드
async function loadResolutions() {
    try {
        const response = await fetch('/api/resolutions');
        const data = await response.json();
        
        const select = document.getElementById('resolutionSelect');
        select.innerHTML = '<option value="">해상도 선택...</option>';
        
        if (data.resolutions && Array.isArray(data.resolutions)) {
            data.resolutions.forEach(resolution => {
                const option = document.createElement('option');
                option.value = resolution;
                option.textContent = resolution;
                
                // 현재 해상도와 비교
                const currentResolution = data.current || '';
                if (resolution === currentResolution) {
                    option.selected = true;
                }
                
                select.appendChild(option);
            });
            
            // 현재 해상도 표시
            const currentResolution = data.current || 'N/A';
            document.getElementById('cameraResolution').textContent = currentResolution;
        } else {
            select.innerHTML = '<option value="">해상도 데이터 오류</option>';
        }
    } catch (error) {
        const select = document.getElementById('resolutionSelect');
        select.innerHTML = '<option value="">해상도 로드 실패</option>';
    }
}

// 해상도 적용
async function applyResolution() {
    const select = document.getElementById('resolutionSelect');
    const resolution = select.value;
    
    if (!resolution) {
        showError('해상도를 선택해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/resolution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resolution: resolution })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('cameraResolution').textContent = resolution;
            showSuccess(data.message);
            
            // 카메라 피드 새로고침
            setTimeout(() => {
                const img = document.getElementById('cameraFeed');
                img.src = img.src + '?' + new Date().getTime();
            }, 1000);
        } else {
            showError(data.message || '해상도 변경에 실패했습니다.');
        }
    } catch (error) {
        showError('해상도 변경 중 오류가 발생했습니다.');
    }
}

// 초음파 센서 측정 토글
async function toggleUltrasonicMeasurement() {
    const toggleBtn = document.getElementById('ultrasonicToggleBtn');
    
    if (ultrasonicRunning) {
        // 현재 실행 중이면 중지
        await stopUltrasonicMeasurement();
    } else {
        // 현재 중지 중이면 시작
        await startUltrasonicMeasurement();
    }
}

// 초음파 센서 측정 시작
async function startUltrasonicMeasurement() {
    try {
        const response = await fetch('/api/ultrasonic/start', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            ultrasonicRunning = true;
            updateUltrasonicToggleButton();
            showToast('시작됨', '초음파 센서 측정이 시작되었습니다.', 'success');
        } else {
            showToast('오류', data.message || '측정 시작에 실패했습니다.', 'error');
        }
    } catch (error) {
        showToast('오류', '측정 시작 중 오류가 발생했습니다.', 'error');
    }
}

// 초음파 센서 측정 중지
async function stopUltrasonicMeasurement() {
    try {
        const response = await fetch('/api/ultrasonic/stop', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            ultrasonicRunning = false;
            updateUltrasonicToggleButton();
            showToast('중지됨', '초음파 센서 측정이 중지되었습니다.', 'info');
        } else {
            showToast('오류', data.message || '측정 중지에 실패했습니다.', 'error');
        }
    } catch (error) {
        showToast('오류', '측정 중지 중 오류가 발생했습니다.', 'error');
    }
}

// 초음파 토글 버튼 업데이트
function updateUltrasonicToggleButton() {
    const toggleBtn = document.getElementById('ultrasonicToggleBtn');
    const icon = toggleBtn.querySelector('i');
    
    if (ultrasonicRunning) {
        // 실행 중일 때
        toggleBtn.className = 'btn btn-danger';
        icon.className = 'fas fa-stop';
        toggleBtn.innerHTML = '<i class="fas fa-stop"></i> 중지';
    } else {
        // 중지 중일 때
        toggleBtn.className = 'btn btn-success';
        icon.className = 'fas fa-play';
        toggleBtn.innerHTML = '<i class="fas fa-play"></i> 시작';
    }
}

// 측정 간격 업데이트
async function updateInterval() {
    const interval = document.getElementById('intervalRange').value;
    document.getElementById('intervalDisplay').textContent = interval + '초';
    document.getElementById('intervalValue').textContent = interval + '초';
    
    try {
        await fetch('/api/ultrasonic/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ interval: parseFloat(interval) })
        });
    } catch (error) {
        console.error('간격 설정 실패:', error);
    }
}

// 초음파 데이터 업데이트
function updateUltrasonicData(data) {
    // 현재 거리 표시
    document.getElementById('currentDistance').textContent = data.distance + ' cm';
}

// 시스템 정보 업데이트
async function updateSystemInfo() {
    try {
        const response = await fetch('/api/system_info');
        const data = await response.json();
        
        if (data && !data.error) {
            // 각 필드별로 데이터 확인 및 업데이트
            const cpuUsage = data.cpu_usage || data.cpu || 0;
            const cpuTemp = data.cpu_temp || data.temperature || 0;
            const memoryUsage = data.memory_usage || data.memory || data.ram || 0;
            const ipAddress = data.ip_address || data.ip || '--';
            const cameraFps = data.camera_fps || '--';
            
            document.getElementById('cpuUsage').textContent = cpuUsage.toFixed(1) + '%';
            document.getElementById('cpuTemp').textContent = cpuTemp.toFixed(1) + '°C';
            document.getElementById('memoryUsage').textContent = memoryUsage.toFixed(1) + '%';
            document.getElementById('ipAddress').textContent = ipAddress;
            document.getElementById('cameraFps').textContent = cameraFps;
        }
    } catch (error) {
        console.error('시스템 정보 업데이트 실패:', error);
    }
}

// 시스템 정보 업데이트 시작
function startSystemInfoUpdates() {
    updateSystemInfo();
    setInterval(updateSystemInfo, 3000);
}

// 시간 업데이트
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    document.getElementById('systemTime').textContent = timeString;
}

// 메시지 토스트 표시
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <strong>${title}</strong>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 3000);
}

// 성공 토스트
function showSuccess(message) {
    showToast(message, 'success', 2000);
}

// 오류 토스트
function showError(message) {
    showToast(message, 'error', 4000);
}

// 정보 토스트
function showInfo(message) {
    showToast(message, 'info', 3000);
}

// 경고 토스트
function showWarning(message) {
    showToast(message, 'warning', 3000);
} 