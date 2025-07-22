// 유틸리티 함수들 (코드 실행, 출력 관리, 시스템 정보, 토스트 등)

// 코드 실행
async function runCode() {
    if (!isConnected) {
        showToast('서버에 연결되지 않았습니다.', 'error');
        return;
    }

    if (codeRunning) {
        showToast('코드가 이미 실행 중입니다.', 'warning');
        return;
    }

    const code = editor.getValue();
    if (!code.trim()) {
        showToast('실행할 코드가 없습니다.', 'warning');
        return;
    }

    try {
        codeRunning = true;
        updateExecutionStatus('실행 중...');
        updateExecutionButtons(true);

        addOutput('🚀 코드 실행 시작...', 'system');

        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                timeout: 30
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        showToast('코드 실행이 시작되었습니다.', 'success');

    } catch (error) {
        codeRunning = false;
        updateExecutionStatus('실행 실패');
        updateExecutionButtons(false);
        addOutput('❌ 실행 오류: ' + error.message, 'error');
        showToast('실행 오류: ' + error.message, 'error');
    }
}

// 코드 중지
async function stopCode() {
    if (!codeRunning) {
        showToast('실행 중인 코드가 없습니다.', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/stop', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            codeRunning = false;
            updateExecutionStatus('중지됨');
            updateExecutionButtons(false);
            addOutput('🛑 코드 실행이 중지되었습니다.', 'warning');
            showToast('코드 실행이 중지되었습니다.', 'success');
        } else {
            throw new Error(data.error);
        }

    } catch (error) {
        showToast('중지 오류: ' + error.message, 'error');
    }
}

// 출력 추가
function addOutput(message, type = 'output') {
    const outputContent = document.getElementById('outputContent');
    const outputItem = document.createElement('div');
    outputItem.className = 'output-item ' + type;
    outputItem.textContent = '[' + new Date().toLocaleTimeString() + '] ' + message;
    
    outputContent.appendChild(outputItem);
    outputContent.scrollTop = outputContent.scrollHeight;
}

// 출력 클리어
function clearOutput() {
    const outputContent = document.getElementById('outputContent');
    outputContent.innerHTML = `
        <div class="output-item system">🚀 Findee Web Code Editor가 준비되었습니다.</div>
        <div class="output-item system">💡 사용 가능한 객체: robot, time, Findee</div>
        <div class="output-item system">🔧 robot = Findee()로 로봇을 초기화하고 사용하세요!</div>
        <div class="output-item system">📝 예제 코드를 작성하고 실행해보세요!</div>
    `;
}

// 실행 상태 업데이트
function updateExecutionStatus(status) {
    document.getElementById('outputStatus').textContent = status;
}

// 실행 버튼 상태 업데이트
function updateExecutionButtons(running) {
    document.getElementById('runBtn').disabled = running;
    document.getElementById('stopBtn').disabled = !running;
}

// 시스템 정보 업데이트
async function updateSystemInfo() {
    try {
        const response = await fetch('/api/system_info');
        const data = await response.json();
        
        if (data) {
            document.getElementById('cpuUsage').textContent = (data.cpu_usage || 0).toFixed(1) + '%';
            document.getElementById('cpuTemp').textContent = (data.cpu_temp || 0).toFixed(1) + '°C';
            document.getElementById('memoryUsage').textContent = (data.memory_usage || 0).toFixed(1) + '%';
            document.getElementById('ipAddress').textContent = data.ip_address || '--';
            document.getElementById('cameraFps').textContent = data.camera_fps || '--';
            document.getElementById('cameraResolution').textContent = data.current_resolution || '--';
            
            // 카메라가 사용 가능하면 해상도 목록도 업데이트
            if (data.camera_status) {
                await loadCameraResolutions();
            }
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

// Toast 메시지 표시
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
} 