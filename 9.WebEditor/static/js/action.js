// Monaco Editor 인스턴스 (전역 변수)
let monacoEditor = null;

// Monaco Editor 설정 함수에서 에디터 인스턴스 저장
function setMonacoEditor(editor) {
    monacoEditor = editor;
}

// Run 버튼 클릭 이벤트 핸들러
function handleRunButtonClick() {
    if (!monacoEditor) {
        console.error('Monaco Editor가 초기화되지 않았습니다.');
        showToast('에디터가 준비되지 않았습니다.', 'error');
        return;
    }

    const code = monacoEditor.getValue();

    if (!code || code.trim() === '') {
        showToast('실행할 코드가 없습니다.', 'warning');
        return;
    }

    showToast('코드 실행을 시작합니다...', 'info');


    if (window.socket && window.socket.connected) {
        window.socket.emit('execute_code', {code: code});
    } else {
        console.error('Socket.IO가 초기화되지 않았거나 연결되지 않았습니다.');
        showToast('연결이 준비되지 않았습니다. 잠시 후 다시 시도해주세요.', 'error');

        setTimeout(() => {
            if (window.socket && window.socket.connected) {
                handleRunButtonClick();
            } else {
                showToast('연결에 실패했습니다. 페이지를 새로고침해주세요.', 'error');
            }
        }, 2000);
    }
}

// 출력 패널 초기화
function clearOutput() {
    const outputContent = document.querySelector('.output-content');
    if (outputContent) {
        outputContent.innerHTML = '';
    }
}

// 출력 메시지 추가
function addOutputMessage(message, type = 'info') {
    const outputContent = document.querySelector('.output-content');
    if (!outputContent) return;

    const outputItem = document.createElement('div');
    outputItem.className = `output-item ${type}`;
    outputItem.textContent = message;

    outputContent.appendChild(outputItem);

    // 자동 스크롤
    outputContent.scrollTop = outputContent.scrollHeight;
}

// Socket.IO 이벤트 리스너 설정
function setupSocketListeners() {
    if (!window.socket) {
        console.error('Socket.IO가 초기화되지 않았습니다.');
        return;
    }

    // 실행 시작 이벤트
    window.socket.on('execution_started', function(data) {
        addOutputMessage(`System: ${data.message}`, 'system');
    });

    // 표준 출력 이벤트
    window.socket.on('stdout', function(data) {
        addOutputMessage(data.output, 'info');
    });

    // 표준 에러 이벤트
    window.socket.on('stderr', function(data) {
        addOutputMessage(data.output, 'error');
    });

    // 실행 완료 이벤트
    window.socket.on('finished', function(data) {
        addOutputMessage('System: 코드 실행이 완료되었습니다.', 'system');
        showToast('코드 실행이 완료되었습니다.', 'success');
    });

    // 실행 에러 이벤트
    window.socket.on('execution_error', function(data) {
        addOutputMessage(`Error: ${data.error}`, 'error');
        showToast(`실행 오류: ${data.error}`, 'error');
    });
}

// 전역 함수로 노출 (다른 파일에서 사용 가능)
window.handleRunButtonClick = handleRunButtonClick;
window.setMonacoEditor = setMonacoEditor;
window.addOutputMessage = addOutputMessage;
window.showToast = showToast;
window.setupSocketListeners = setupSocketListeners;
