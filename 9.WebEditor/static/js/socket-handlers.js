// Socket.IO 이벤트 핸들러 및 통신

// Socket.IO 초기화
function initializeSocket() {
    socket = io();

    socket.on('connect', function() {
        console.log('Connected to server');
        isConnected = true;
        updateConnectionStatus(true);
        showToast('서버에 연결되었습니다.', 'success');
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        isConnected = false;
        updateConnectionStatus(false);
        showToast('서버와의 연결이 끊어졌습니다.', 'error');
        resetActiveDirection();
    });

    socket.on('robot_status', function(data) {
        updateRobotStatus(data);
    });

    socket.on('motor_feedback', function(data) {
        handleMotorFeedback(data);
    });

    socket.on('code_output', function(data) {
        // 실시간 출력을 즉시 표시
        addOutput(data.output, 'output');
    });

    socket.on('code_execution_result', function(data) {
        codeRunning = false;
        updateExecutionButtons(false);

        if (data.success) {
            updateExecutionStatus('완료');
            addOutput('✅ 코드 실행 완료 (' + data.execution_time.toFixed(2) + '초)', 'success');
            // 실시간 출력이 이미 표시되었으므로 추가 출력은 하지 않음
        } else {
            updateExecutionStatus('오류');
            addOutput('❌ 실행 오류: ' + data.error, 'error');
        }
    });

    socket.on('ultrasonic_data', function(data) {
        updateUltrasonicData(data);
    });
}

// 연결 상태 업데이트
function updateConnectionStatus(connected) {
    const statusDot = document.getElementById('connectionStatus');
    const statusText = document.getElementById('connectionText');
    
    statusDot.className = 'status-dot';
    if (connected) {
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.add('error');
        statusText.textContent = 'Disconnected';
    }
}

// 로봇 상태 업데이트
function updateRobotStatus(data) {
    const motorStatus = document.getElementById('motorStatus');
    const cameraStatus = document.getElementById('cameraStatus');
    const ultrasonicStatus = document.getElementById('ultrasonicStatus');

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

// 키보드 상태 업데이트
function updateKeyboardStatus(active) {
    const statusIndicator = document.getElementById('keyboardStatus');
    const statusText = document.getElementById('keyboardStatusText');
    const statusHint = document.getElementById('keyboardHint');
    
    if (active) {
        statusIndicator.className = 'status-indicator active';
        statusText.textContent = '키보드 제어 활성화';
        statusHint.textContent = '에디터 클릭 시 자동 비활성화';
    } else {
        statusIndicator.className = 'status-indicator inactive';
        statusText.textContent = '키보드 제어 비활성화';
        statusHint.textContent = '에디터 외부 클릭 시 활성화';
    }
} 