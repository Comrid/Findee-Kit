class FindeeRobotController {
    constructor() {
        this.currentSpeed = 60;
        this.activeButtons = new Set();
        this.pressedKeys = new Set();
        this.keyPressOrder = [];
        this.isConnected = false;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupSpeedControl();
        this.setupSocketConnection();
        this.setupLogPanel();
        this.startSystemInfoUpdates();

        document.body.focus();
        document.body.tabIndex = 0;
    }

    setupEventListeners() {
        // 마우스 이벤트
        document.querySelectorAll('.direction-btn').forEach(btn => {
            btn.addEventListener('mousedown', (e) => this.handleButtonPress(e.target));
            btn.addEventListener('mouseup', (e) => this.handleButtonRelease(e.target));
            btn.addEventListener('mouseleave', (e) => this.handleButtonRelease(e.target));
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.handleButtonPress(e.target);
            });
            btn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.handleButtonRelease(e.target);
            });
        });

        // 키보드 이벤트
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
        document.addEventListener('keyup', (e) => this.handleKeyUp(e));
        document.addEventListener('click', () => document.body.focus());

        // 카메라 스트림 이벤트
        const cameraStream = document.getElementById('cameraStream');
        cameraStream.addEventListener('load', () => {
            document.getElementById('cameraError').style.display = 'none';
            cameraStream.style.display = 'block';
            this.addLog('📹 Camera stream connected', 'system');
        });

        cameraStream.addEventListener('error', () => {
            document.getElementById('cameraError').style.display = 'flex';
            cameraStream.style.display = 'none';
            this.addLog('📹 Camera stream error', 'warning');
        });
    }

    setupSpeedControl() {
        const speedSlider = document.getElementById('speedSlider');
        const speedValue = document.getElementById('speedValue');

        speedSlider.addEventListener('input', (e) => {
            this.currentSpeed = parseInt(e.target.value);
            speedValue.textContent = `${this.currentSpeed}%`;

            // 현재 이동 중이면 속도 업데이트
            if (this.activeButtons.size > 0) {
                this.updateMotorCommand();
            }
        });
    }

    setupSocketConnection() {
        this.socket = io();

        // 연결 이벤트
        this.socket.on('connect', () => {
            this.addLog('🔌 Socket connected to server', 'system');
            this.isConnected = true;
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            this.addLog('🔌 Socket disconnected from server', 'warning');
            this.isConnected = false;
            this.updateConnectionStatus(false);
        });

        // 서버 응답 이벤트
        this.socket.on('connection_status', (data) => {
            this.isConnected = data.connected;
            this.addLog(`📡 ${data.message}`, data.connected ? 'system' : 'warning');
            this.updateConnectionStatus(data.connected);
        });

        this.socket.on('robot_status', (data) => {
            this.updateRobotStatus(data);
            this.currentSpeed = data.speed || this.currentSpeed;
            document.getElementById('speedSlider').value = this.currentSpeed;
            document.getElementById('speedValue').textContent = `${this.currentSpeed}%`;
            this.addLog(`🤖 Robot connected - Motor: ${data.motor_status}, Camera: ${data.camera_status}`, 'system');
        });

        this.socket.on('motor_feedback', (data) => {
            if (data.success) {
                this.addLog(`✅ Motor: ${data.direction} (${data.speed}%)`, 'command');
            } else {
                this.addLog(`❌ Motor error: ${data.error}`, 'error');
            }
        });

        // 🚀 실시간 대시보드 업데이트 수신
        this.socket.on('dashboard_update', (data) => {
            try {
                if (data.system_info && !data.system_info.error) {
                    this.updateSystemInfo(data.system_info);
                }
                if (data.robot_status) {
                    this.updateRobotStatus(data.robot_status);
                }

                // 디버그용 - 실시간 업데이트 확인
                console.log('📡 Real-time dashboard update received:', new Date(data.timestamp * 1000).toLocaleTimeString());
            } catch (error) {
                console.error('Dashboard update error:', error);
            }
        });
    }

    setupLogPanel() {
        const clearBtn = document.getElementById('clearLogBtn');
        clearBtn.addEventListener('click', () => {
            this.clearLog();
        });
    }

    startSystemInfoUpdates() {
        this.addLog('📡 실시간 Socket.IO 업데이트 활성화', 'system');
    }

    updateSystemInfo(data) {
        // 네트워크 정보 업데이트
        document.getElementById('networkInfo').textContent = `📶 IP: ${data.hostname || '--'}`;

        // 시스템 정보 업데이트
        const cpuTemp = data.cpu_temperature ? `${data.cpu_temperature.toFixed(1)}°C` : '--';
        const cpuUsage = data.cpu_percent ? `${data.cpu_percent.toFixed(1)}%` : '--';
        document.getElementById('systemInfo').textContent = `🔋 CPU: ${cpuUsage} / ${cpuTemp}`;
    }

    handleButtonPress(button) {
        const direction = button.dataset.direction;
        if (!direction || this.activeButtons.has(direction)) return;

        this.activeButtons.add(direction);
        button.classList.add('active');
        this.sendMotorCommand(direction);
        this.addLog(`🎮 ${direction} pressed (${this.currentSpeed}%)`, 'command');
    }

    handleButtonRelease(button) {
        const direction = button.dataset.direction;
        if (!direction || !this.activeButtons.has(direction)) return;

        this.activeButtons.delete(direction);
        button.classList.remove('active');

        if (this.activeButtons.size === 0) {
            this.sendMotorCommand('stop');
        } else {
            this.updateMotorCommand();
        }
    }

    handleKeyDown(e) {
        // 속도 조절
        if (e.key === '+' || e.key === '=') {
            this.adjustSpeed(5);
            e.preventDefault();
            return;
        } else if (e.key === '-') {
            this.adjustSpeed(-5);
            e.preventDefault();
            return;
        }

        // 방향키 처리
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) return;
        if (this.pressedKeys.has(e.code)) return;

        this.pressedKeys.add(e.code);
        this.keyPressOrder.push(e.code);
        this.updateDirectionFromKeys();
        e.preventDefault();
    }

    handleKeyUp(e) {
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) return;

        this.pressedKeys.delete(e.code);
        this.keyPressOrder = this.keyPressOrder.filter(key => key !== e.code);
        this.updateDirectionFromKeys();
    }

    updateDirectionFromKeys() {
        const newDirection = this.getDirectionFromKeys();
        const currentDirection = Array.from(this.activeButtons)[0] || null;

        if (currentDirection && currentDirection !== newDirection) {
            const oldButton = document.querySelector(`[data-direction="${currentDirection}"]`);
            if (oldButton) this.handleButtonRelease(oldButton);
        }

        if (newDirection && newDirection !== currentDirection) {
            const newButton = document.querySelector(`[data-direction="${newDirection}"]`);
            if (newButton) this.handleButtonPress(newButton);
        }
    }

    getDirectionFromKeys() {
        const up = this.pressedKeys.has('ArrowUp');
        const down = this.pressedKeys.has('ArrowDown');
        const left = this.pressedKeys.has('ArrowLeft');
        const right = this.pressedKeys.has('ArrowRight');
        const stop = this.pressedKeys.has('Space');

        if (stop) return 'stop';

        const lastKey = this.keyPressOrder[this.keyPressOrder.length - 1];

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

    adjustSpeed(delta) {
        const newSpeed = Math.max(20, Math.min(100, this.currentSpeed + delta));
        document.getElementById('speedSlider').value = newSpeed;
        document.getElementById('speedSlider').dispatchEvent(new Event('input'));
    }

    updateMotorCommand() {
        if (this.activeButtons.size > 0) {
            const direction = Array.from(this.activeButtons)[0];
            this.sendMotorCommand(direction);
        }
    }

    sendMotorCommand(direction) {
        if (!this.isConnected) {
            this.addLog('🚫 Robot not connected', 'warning');
            return;
        }

        const command = {
            direction: direction,
            speed: this.currentSpeed,
            timestamp: Date.now()
        };

        if (this.socket) {
            this.socket.emit('motor_control', command);
        } else {
            this.addLog('🚫 Socket not available', 'error');
        }
    }

    updateConnectionStatus(connected) {
        const dot = document.getElementById('connectionDot');
        const status = document.getElementById('connectionStatus');

        if (connected) {
            dot.className = 'status-dot';
            status.textContent = 'Connected';
        } else {
            dot.className = 'status-dot error';
            status.textContent = 'Disconnected';
        }
    }

    updateRobotStatus(data) {
        const robotStatus = data;

        // 로봇 상태 표시
        document.getElementById('motorStatus').textContent = robotStatus.motor_status ? '✅' : '❌';
        document.getElementById('cameraStatus').textContent = robotStatus.camera_status ? '✅' : '❌';
        document.getElementById('ultrasonicStatus').textContent = robotStatus.ultrasonic_status ? '✅' : '❌';

        // 카메라 정보 업데이트
        const cameraInfo = document.getElementById('cameraInfo');
        if (robotStatus.camera_status) {
            cameraInfo.textContent = '📹 Camera: Active';
            const fps = robotStatus.camera_fps || 0;
            document.getElementById('fpsStatus').textContent = fps;
        } else {
            cameraInfo.textContent = '📹 Camera: Standby';
            document.getElementById('fpsStatus').textContent = 'N/A';
        }
    }

    addLog(message, type = 'system') {
        const logContent = document.getElementById('logContent');
        const logItem = document.createElement('div');
        logItem.className = `log-item ${type}`;

        const timestamp = new Date().toLocaleTimeString();
        logItem.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span> ${message}
        `;

        logContent.appendChild(logItem);
        logContent.scrollTop = logContent.scrollHeight;

        // 로그 개수 제한
        const logItems = logContent.querySelectorAll('.log-item');
        if (logItems.length > 80) {
            logItems[0].remove();
        }
    }

    clearLog() {
        const logContent = document.getElementById('logContent');
        logContent.innerHTML = '';
        this.addLog('📝 Log cleared', 'system');
    }
}

// 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    const controller = new FindeeRobotController();
    window.robotController = controller;

    setTimeout(() => {
        controller.addLog('📖 사용법:', 'system');
        controller.addLog('   - 마우스: 버튼 클릭으로 조작', 'system');
        controller.addLog('   - 키보드: 화살표키, Space(정지), +/-(속도)', 'system');
        controller.addLog('   - 카메라: 자동으로 MJPEG 스트리밍', 'system');
    }, 100);
});

// 페이지 언로드시 정리
window.addEventListener('beforeunload', () => {
    if (window.robotController) {
        window.robotController.sendMotorCommand('stop');
    }
}); 