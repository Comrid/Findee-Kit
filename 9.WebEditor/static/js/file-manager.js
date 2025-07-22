// 파일 관리 기능 (저장, 로드, 예제 코드)

// 파일 목록 로드
async function loadFileList() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('fileSelect');
            select.innerHTML = '<option value="">파일 선택...</option>';
            
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.name;
                option.textContent = file.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('파일 목록 로드 실패:', error);
    }
}

// 파일 로드
async function loadFile() {
    const select = document.getElementById('fileSelect');
    const filename = select.value;
    
    if (!filename) {
        showToast('파일을 선택해주세요.', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/load/' + filename);
        const data = await response.json();
        
        if (data.success) {
            editor.setValue(data.code);
            currentFileName = filename;
            showToast('파일 "' + filename + '"을 로드했습니다.', 'success');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('파일 로드 오류: ' + error.message, 'error');
    }
}

// 파일 저장
async function saveFile() {
    const code = editor.getValue();
    
    if (!code.trim()) {
        showToast('저장할 코드가 없습니다.', 'warning');
        return;
    }

    let filename = currentFileName;
    if (!filename) {
        filename = prompt('파일명을 입력하세요 (확장자 제외):');
        if (!filename) return;
    }

    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                filename: filename
            })
        });

        const data = await response.json();
        
        if (data.success) {
            currentFileName = data.filename;
            showToast('파일 "' + data.filename + '"을 저장했습니다.', 'success');
            loadFileList(); // 파일 목록 새로고침
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('파일 저장 오류: ' + error.message, 'error');
    }
}

// 새 파일
function newFile() {
    if (confirm('현재 코드를 지우고 새 파일을 만드시겠습니까?')) {
        editor.setValue('# 새 파일\nprint("Hello, Findee!")');
        currentFileName = '';
        showToast('새 파일을 생성했습니다.', 'success');
    }
}

// 예제 코드 로드
function loadExample(exampleName) {
    if (codeExamples[exampleName]) {
        editor.setValue(codeExamples[exampleName]);
        showToast('예제 "' + exampleName + '"을 로드했습니다.', 'success');
    } else {
        showToast('예제를 찾을 수 없습니다.', 'error');
    }
} 