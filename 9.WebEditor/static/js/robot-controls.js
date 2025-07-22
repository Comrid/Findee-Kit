// 로봇 제어 기능 (모터, 카메라, 초음파 센서)

// 모터 명령 전송
function sendMotorCommand(direction, speed) {
    if (!isConnected) {
        showToast('연결되지 않음', 'error');
        return;
    }

    const command = {
        direction: direction,
        speed: speed
    };

    socket.emit('motor_control', command);
    
    // 모터 상태 표시 업데이트
    const statusMap = {
        'forward': { text: '전진', class: 'forward' },
        'backward': { text: '후진', class: 'backward' },
        'left': { text: '좌회전', class: 'left' },
        'right': { text: '우회전', class: 'right' },
        'forward-left': { text: '전진+좌회전', class: 'forward' },
        'forward-right': { text: '전진+우회전', class: 'forward' },
        'backward-left': { text: '후진+좌회전', class: 'backward' },
        'backward-right': { text: '후진+우회전', class: 'backward' },
        'rotate-left': { text: '제자리 좌회전', class: 'left' },
        'rotate-right': { text: '제자리 우회전', class: 'right' },
        'stop': { text: '정지', class: 'stop' }
    };
    
    const status = statusMap[direction] || { text: '명령 없음', class: 'idle' };
    updateMotorStatus(status.text, status.class);
}

// 활성 방향 업데이트
function updateActiveDirection(direction) {
    // 기존 활성 방향 제거
    resetActiveDirection();
    
    if (direction) {
        // 새로운 방향 활성화
        const btn = document.querySelector(`[data-direction="${direction}"]`);
        if (btn) {
            btn.classList.add('active');
            activeDirection = direction;
        }
    }
}

function resetActiveDirection() {
    // 모든 방향 버튼에서 활성 상태 제거
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    activeDirection = null;
}

// 모터 상태 표시 업데이트 함수
function updateMotorStatus(command, className = '') {
    const statusElement = document.getElementById('motorStatusValue');
    if (statusElement) {
        statusElement.textContent = command;
        statusElement.className = 'status-value ' + className;
        currentMotorCommand = command;
    }
}

// 모터 피드백 처리
function handleMotorFeedback(data) {
    // 모터 피드백 처리
    console.log('Motor feedback:', data);
}

// 초음파 데이터 업데이트
function updateUltrasonicData(data) {
    // 현재 거리 표시
    document.getElementById('currentDistance').textContent = data.distance + ' cm';
}

// 초음파 센서 측정 토글
async function toggleUltrasonicMeasurement() {
    if (ultrasonicRunning) {
        await stopUltrasonicMeasurement();
    } else {
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
            const btn = document.getElementById('ultrasonicToggleBtn');
            btn.innerHTML = '<i class="fas fa-stop"></i> 중지';
            btn.className = 'btn btn-danger';
            showToast('초음파 센서 측정이 시작되었습니다.', 'success');
        } else {
            showToast(data.message || '측정 시작에 실패했습니다.', 'error');
        }
    } catch (error) {
        showToast('측정 시작 중 오류가 발생했습니다.', 'error');
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
            const btn = document.getElementById('ultrasonicToggleBtn');
            btn.innerHTML = '<i class="fas fa-play"></i> 시작';
            btn.className = 'btn btn-success';
            showToast('초음파 센서 측정이 중지되었습니다.', 'success');
        } else {
            showToast(data.message || '측정 중지에 실패했습니다.', 'error');
        }
    } catch (error) {
        showToast('측정 중지 중 오류가 발생했습니다.', 'error');
    }
}

// 측정 간격 업데이트
async function updateInterval() {
    const interval = document.getElementById('intervalRange').value;
    document.getElementById('intervalDisplay').textContent = interval + '초';
    
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

// 카메라 해상도 목록 로드
async function loadCameraResolutions() {
    try {
        const response = await fetch('/api/camera/resolutions');
        const data = await response.json();
        
        if (data.success && data.resolutions) {
            const select = document.getElementById('resolutionSelect');
            select.innerHTML = '<option value="">해상도 선택...</option>';
            
            data.resolutions.forEach(resolution => {
                if (resolution && typeof resolution === 'string') {
                    const option = document.createElement('option');
                    option.value = resolution;
                    option.textContent = resolution;
                    select.appendChild(option);
                }
            });
            
            console.log('📹 카메라 해상도 목록 로드 완료:', data.resolutions);
        } else {
            console.warn('⚠️ 카메라 해상도 목록 로드 실패:', data.message);
        }
    } catch (error) {
        console.error('❌ 카메라 해상도 목록 로드 실패:', error);
        // 기본 해상도 목록 설정
        const select = document.getElementById('resolutionSelect');
        select.innerHTML = '<option value="">해상도 선택...</option>';
        const defaultResolutions = ['640x480', '1280x720', '1920x1080'];
        defaultResolutions.forEach(resolution => {
            const option = document.createElement('option');
            option.value = resolution;
            option.textContent = resolution;
            select.appendChild(option);
        });
    }
}

// 카메라 해상도 적용
async function applyCameraResolution() {
    const resolution = document.getElementById('resolutionSelect').value;
    
    if (!resolution) {
        showToast('해상도를 선택해주세요.', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/camera/resolution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resolution: resolution })
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('카메라 해상도가 "' + resolution + '"로 변경되었습니다.', 'success');
            // 현재 해상도 표시 업데이트
            document.getElementById('cameraResolution').textContent = resolution;
        } else {
            showToast(data.message || '해상도 변경에 실패했습니다.', 'error');
        }
    } catch (error) {
        showToast('해상도 변경 중 오류가 발생했습니다.', 'error');
    }
}

// 키보드 이벤트 처리
function handleKeyDown(event) {
    if (event.repeat) return;

    // 에디터가 포커스되어 있으면 키보드 제어 비활성화
    if (editorFocused) {
        return;
    }

    // 속도 조절
    if (event.key === '+' || event.key === '=') {
        adjustSpeed(5);
        event.preventDefault();
        return;
    } else if (event.key === '-') {
        adjustSpeed(-5);
        event.preventDefault();
        return;
    }

    // 방향키 처리
    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(event.code)) return;
    if (pressedKeys.has(event.code)) return;

    pressedKeys.add(event.code);
    keyPressOrder.push(event.code);
    updateDirectionFromKeys();
    event.preventDefault();
}

function handleKeyUp(event) {
    // 에디터가 포커스되어 있으면 키보드 제어 비활성화
    if (editorFocused) {
        return;
    }

    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(event.code)) return;

    pressedKeys.delete(event.code);
    keyPressOrder = keyPressOrder.filter(key => key !== event.code);
    updateDirectionFromKeys();
}

// 키보드 조합으로 방향 결정
function updateDirectionFromKeys() {
    const newDirection = getDirectionFromKeys();
    const currentDirection = activeDirection;

    if (currentDirection && currentDirection !== newDirection) {
        sendMotorCommand('stop', 0);
        resetActiveDirection();
    }

    if (newDirection && newDirection !== currentDirection) {
        sendMotorCommand(newDirection, currentSpeed);
        updateActiveDirection(newDirection);
    }
}

// 키보드 조합에서 방향 추출
function getDirectionFromKeys() {
    const up = pressedKeys.has('ArrowUp');
    const down = pressedKeys.has('ArrowDown');
    const left = pressedKeys.has('ArrowLeft');
    const right = pressedKeys.has('ArrowRight');
    const stop = pressedKeys.has('Space');

    if (stop) return 'stop';

    const lastKey = keyPressOrder[keyPressOrder.length - 1];

    // 8방향 조합
    if (up && left) return 'forward-left';
    if (up && right) return 'forward-right';
    if (down && left) return 'backward-left';
    if (down && right) return 'backward-right';

    // 단일 방향
    if (lastKey === 'ArrowUp' && up) return 'forward';
    if (lastKey === 'ArrowDown' && down) return 'backward';
    if (lastKey === 'ArrowLeft' && left) return 'rotate-left';
    if (lastKey === 'ArrowRight' && right) return 'rotate-right';

    if (up) return 'forward';
    if (down) return 'backward';
    if (left) return 'rotate-left';
    if (right) return 'rotate-right';

    return null;
}

// 속도 조절 함수
function adjustSpeed(delta) {
    const newSpeed = Math.max(20, Math.min(100, currentSpeed + delta));
    const speedSlider = document.getElementById('speedSlider');
    const speedValue = document.getElementById('speedValue');
    
    if (speedSlider && speedValue) {
        speedSlider.value = newSpeed;
        speedValue.textContent = newSpeed + '%';
        currentSpeed = newSpeed;
        
        // 현재 이동 중이면 속도 업데이트
        if (activeDirection) {
            sendMotorCommand(activeDirection, currentSpeed);
        }
    }
}

// 컨트롤 초기화
function initializeControls() {
    // 방향 패드 버튼 이벤트
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.addEventListener('mousedown', function() {
            const direction = this.dataset.direction;
            sendMotorCommand(direction, currentSpeed);
            updateActiveDirection(direction);
        });

        btn.addEventListener('mouseup', function() {
            if (this.dataset.direction !== 'stop') {
                sendMotorCommand('stop', 0);
                resetActiveDirection();
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