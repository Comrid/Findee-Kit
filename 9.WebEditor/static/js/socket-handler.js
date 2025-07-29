// Socket.IO 이벤트 핸들러 및 통신

// Socket.IO 초기화
function initializeSocket() {
    try {
        if (typeof window.io === 'undefined') {
            console.error('Socket.IO 라이브러리가 로드되지 않았습니다.');
            return;
        }

        socket = window.io();

        // 연결시
        socket.on('connect', function() {
            console.log('Connected to server');
            isConnected = true;
            updateConnectionStatus(true);
            showToast('서버에 연결되었습니다.', 'success');
        });

        // 연결 해제시
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            isConnected = false;
            updateConnectionStatus(false);
            showToast('서버와의 연결이 끊어졌습니다.', 'error');
        });

        // 코드 실행 결과를 실시간으로 출력하기 위한 핸들러
        socket.on('code_output', function(data) {
            addOutput(data.output, 'output');
        });

        socket.on('code_execution_result', function(data) {
            codeRunning = false;
            updateExecutionButtons(false);

            if (data.success) {
                updateExecutionStatus('완료');
                addOutput('✅ 코드 실행 완료 (' + data.execution_time.toFixed(2) + '초)', 'success');
            } else {
                updateExecutionStatus('오류');
                addOutput('❌ 실행 오류: ' + data.error, 'error');
            }
        });
    } catch (error) {
        console.error('Socket.IO 초기화 중 오류:', error);
        showToast('연결 초기화 중 오류가 발생했습니다.', 'error');
    }
}

// 연결 상태 업데이트
function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-item span');

    if (statusDot && statusText) {
        statusDot.className = 'status-dot';
        if (connected) {
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'Disconnected';
        }
    }
}