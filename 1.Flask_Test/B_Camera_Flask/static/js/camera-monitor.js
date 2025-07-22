let updateInterval = null;

// 토스트 메시지 표시
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

// 시스템 정보 업데이트
function updateSystemInfo() {
    fetch('/api/system_info')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                updateConnectionStatus(false, data.error);
                return;
            }

            // 연결 상태 업데이트
            updateConnectionStatus(true);

            // 카메라 상태 업데이트
            updateCameraStatus(data.camera_status);

            // FPS 업데이트
            document.getElementById('fpsDisplay').textContent = data.camera_fps || 0;

            // 시스템 정보 업데이트
            const systemInfo = document.getElementById('systemInfo');
            systemInfo.innerHTML = `
                <div class="info-card">
                    <h3>CPU 사용률</h3>
                    <div class="info-value">${(data.cpu_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="info-card">
                    <h3>메모리 사용률</h3>
                    <div class="info-value">${(data.memory_percent || 0).toFixed(1)}%</div>
                </div>
                <div class="info-card">
                    <h3>CPU 온도</h3>
                    <div class="info-value">${(data.cpu_temperature || 0).toFixed(1)}°C</div>
                </div>
                <div class="info-card">
                    <h3>현재 해상도</h3>
                    <div class="info-value" style="font-size: 1.2em;">${data.current_resolution || 'Unknown'}</div>
                </div>
                <div class="info-card">
                    <h3>IP 주소</h3>
                    <div class="info-value" style="font-size: 1em;">${data.hostname || 'Unknown'}</div>
                </div>
            `;

            // 컴포넌트 상태 업데이트
            updateComponentStatus({
                camera: data.camera_status,
                motor: data.motor_status,
                ultrasonic: data.ultrasonic_status
            });
        })
        .catch(error => {
            console.error('시스템 정보 로드 실패:', error);
            updateConnectionStatus(false, '연결 실패');
        });
}

function updateConnectionStatus(isConnected, errorMsg = '') {
    const dot = document.getElementById('connectionDot');
    const status = document.getElementById('connectionStatus');

    if (isConnected) {
        dot.className = 'status-dot';
        status.textContent = '서버 연결됨';
    } else {
        dot.className = 'status-dot offline';
        status.textContent = errorMsg || '서버 연결 실패';
    }
}

function updateCameraStatus(isActive) {
    const dot = document.getElementById('cameraDot');
    const status = document.getElementById('cameraStatus');

    if (isActive) {
        dot.className = 'status-dot';
        status.textContent = '카메라 활성';
    } else {
        dot.className = 'status-dot offline';
        status.textContent = '카메라 비활성';
    }
}

function updateComponentStatus(components) {
    const container = document.getElementById('componentStatus');
    container.innerHTML = '';

    Object.entries(components).forEach(([name, isActive]) => {
        const card = document.createElement('div');
        card.className = `component-card ${isActive ? 'active' : 'inactive'}`;

        const displayName = {
            camera: '카메라',
            motor: '모터',
            ultrasonic: '초음파'
        }[name] || name;

        card.innerHTML = `
            <div>${displayName}</div>
            <div style="font-size: 0.8em; margin-top: 5px;">
                ${isActive ? '✅ 활성' : '❌ 비활성'}
            </div>
        `;
        container.appendChild(card);
    });
}

// 기능 함수들
function loadAvailableResolutions() {
    fetch('/api/resolutions')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('resolutionSelect');
            select.innerHTML = '';

            data.forEach(resolution => {
                const option = document.createElement('option');
                option.value = resolution.value;
                option.textContent = resolution.label;
                select.appendChild(option);
            });

            console.log(`✅ ${data.length}개 해상도 로드됨`);
            
            // 현재 해상도를 드롭다운에 반영
            updateCurrentResolutionInDropdown();
        })
        .catch(error => {
            console.error('해상도 로드 실패:', error);
            const select = document.getElementById('resolutionSelect');
            select.innerHTML = '<option value="">로드 실패</option>';
        });
}

function updateCurrentResolutionInDropdown() {
    // 시스템 정보에서 현재 해상도를 가져와서 드롭다운에 설정
    fetch('/api/system_info')
        .then(response => response.json())
        .then(data => {
            if (data.current_resolution && data.current_resolution !== 'N/A') {
                const select = document.getElementById('resolutionSelect');
                select.value = data.current_resolution;
            }
        })
        .catch(error => {
            console.error('현재 해상도 업데이트 실패:', error);
        });
}

function changeResolution() {
    const select = document.getElementById('resolutionSelect');
    const selectedResolution = select.value;

    if (!selectedResolution) {
        showToast('알림', '⚠️ 해상도를 선택해주세요.', 'warning');
        return;
    }

    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '📐 변경 중...';

    const selectedOption = select.options[select.selectedIndex];
    const resolutionLabel = selectedOption ? selectedOption.textContent : selectedResolution;

    // 해상도 변경 진행
    showToast('변경 중', `해상도를 ${resolutionLabel}로 변경하고 있습니다...`, 'info');

    fetch('/api/resolution', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution: selectedResolution })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('성공', `✅ ${data.message}`, 'success');
            // 해상도 변경 후 현재 해상도 업데이트
            updateCurrentResolutionInDropdown();
            setTimeout(() => {
                refreshStream();
            }, 1000);
        } else {
            showToast('실패', `❌ 해상도 변경 실패: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        showToast('오류', `❌ 네트워크 오류: ${error.message}`, 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = originalText;
    });
}

function refreshStream() {
    const img = document.getElementById('videoStream');
    const src = img.src;
    img.src = '';
    setTimeout(() => {
        img.src = src + '?t=' + new Date().getTime();
    }, 100);
}

// 초기화 및 주기적 업데이트
function startMonitoring() {
    loadAvailableResolutions(); // 해상도 목록 로드
    updateSystemInfo(); // 즉시 업데이트
    updateInterval = setInterval(updateSystemInfo, 1000); // 1초마다 업데이트
}

function stopMonitoring() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

// 페이지 로드 시 시작

document.addEventListener('DOMContentLoaded', startMonitoring);

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', stopMonitoring);

// 비디오 스트림 에러 처리
document.getElementById('videoStream').addEventListener('error', function() {
    console.warn('비디오 스트림 로드 실패');
});

console.log('🎥 Findee 카메라 모니터 초기화 완료'); 