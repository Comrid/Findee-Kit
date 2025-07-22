// Monaco Editor 설정 및 자동완성 시스템
// Monaco Editor 초기화
function initializeMonacoEditor() {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});
    
    require(['vs/editor/editor.main'], function() {
        // 동적 자동완성 시스템
        monaco.languages.registerCompletionItemProvider('python', {
            provideCompletionItems: function(model, position) {
                const linePrefix = model.getLineContent(position.lineNumber).substring(0, position.column - 1);
                const suggestions = [];
                
                // 기본 Python 키워드들
                const pythonKeywords = [
                    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
                    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
                    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
                    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
                    'try', 'while', 'with', 'yield'
                ];
                
                // 기본 Python 내장 함수들
                const pythonBuiltins = [
                    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'breakpoint', 'bytearray',
                    'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
                    'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
                    'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
                    'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
                    'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
                    'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord',
                    'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round',
                    'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str',
                    'sum', 'super', 'tuple', 'type', 'vars', 'zip'
                ];
                
                // Findee 로봇 관련 객체들
                const findeeObjects = {
                    'robot': {
                        methods: ['get_status', 'get_system_info', 'get_hostname'],
                        description: 'Findee 로봇 메인 객체'
                    },
                    'Findee': {
                        methods: ['__init__', 'get_status', 'get_system_info', 'get_hostname'],
                        description: 'Findee 로봇 클래스 - robot = Findee()로 초기화'
                    }
                };
                
                // 모듈별 함수들
                const moduleFunctions = {
                    'time': ['sleep', 'time', 'ctime', 'gmtime', 'localtime', 'mktime', 'strftime', 'strptime'],
                    'math': ['sin', 'cos', 'tan', 'sqrt', 'pow', 'exp', 'log', 'pi', 'e'],
                    'random': ['random', 'randint', 'choice', 'shuffle', 'uniform'],
                    'os': ['path', 'listdir', 'mkdir', 'remove', 'rename', 'getcwd'],
                    'sys': ['argv', 'path', 'version', 'exit'],
                    'json': ['loads', 'dumps', 'load', 'dump'],
                    're': ['search', 'match', 'findall', 'sub', 'compile']
                };
                
                // 현재 라인에서 import 문 분석
                const importAnalysis = analyzeImports(model);
                
                // 컨텍스트 기반 제안 생성
                function addContextualSuggestions() {
                    // 1. 기본 키워드 제안
                    pythonKeywords.forEach(keyword => {
                        if (keyword.toLowerCase().includes(linePrefix.toLowerCase())) {
                            suggestions.push({
                                label: keyword,
                                kind: monaco.languages.CompletionItemKind.Keyword,
                                insertText: keyword,
                                documentation: 'Python 키워드: ' + keyword
                            });
                        }
                    });
                    
                    // 2. 기본 내장 함수 제안
                    pythonBuiltins.forEach(func => {
                        if (func.toLowerCase().includes(linePrefix.toLowerCase())) {
                            suggestions.push({
                                label: func,
                                kind: monaco.languages.CompletionItemKind.Function,
                                insertText: func + '(${1:})',
                                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                documentation: '내장 함수: ' + func
                            });
                        }
                    });
                    
                    // 3. Findee 객체 제안
                    Object.keys(findeeObjects).forEach(obj => {
                        if (obj.toLowerCase().includes(linePrefix.toLowerCase())) {
                            suggestions.push({
                                label: obj,
                                kind: monaco.languages.CompletionItemKind.Variable,
                                insertText: obj,
                                documentation: findeeObjects[obj].description
                            });
                        }
                    });
                    
                    // 4. 점(.) 뒤에 오는 메서드 제안
                    if (linePrefix.includes('.')) {
                        const parts = linePrefix.split('.');
                        const objectName = parts[parts.length - 2];
                        const methodPrefix = parts[parts.length - 1];
                        
                        // Findee 객체 메서드
                        if (findeeObjects[objectName]) {
                            findeeObjects[objectName].methods.forEach(method => {
                                if (method.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: method,
                                        kind: monaco.languages.CompletionItemKind.Method,
                                        insertText: method + '(${1:})',
                                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                        documentation: objectName + '.' + method + ' 메서드'
                                    });
                                }
                            });
                        }
                        
                        // robot.motor. 메서드들 (또는 다른 Findee 인스턴스)
                        if (parts.length >= 3 && parts[1] === 'motor') {
                            const motorMethods = ['move_forward', 'move_backward', 'turn_left', 'turn_right', 'stop', 'curve_left', 'curve_right'];
                            motorMethods.forEach(method => {
                                if (method.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: method,
                                        kind: monaco.languages.CompletionItemKind.Method,
                                        insertText: method + '(${1:})',
                                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                        documentation: parts[0] + '.motor.' + method + ' 메서드'
                                    });
                                }
                            });
                        }
                        
                        // robot.camera. 메서드들 (또는 다른 Findee 인스턴스)
                        if (parts.length >= 3 && parts[1] === 'camera') {
                            const cameraMethods = ['get_current_resolution', 'get_available_resolutions', 'configure_resolution'];
                            cameraMethods.forEach(method => {
                                if (method.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: method,
                                        kind: monaco.languages.CompletionItemKind.Method,
                                        insertText: method + '(${1:})',
                                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                        documentation: parts[0] + '.camera.' + method + ' 메서드'
                                    });
                                }
                            });
                        }
                        
                        // robot.ultrasonic. 메서드들 (또는 다른 Findee 인스턴스)
                        if (parts.length >= 3 && parts[1] === 'ultrasonic') {
                            const ultrasonicMethods = ['get_distance'];
                            ultrasonicMethods.forEach(method => {
                                if (method.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: method,
                                        kind: monaco.languages.CompletionItemKind.Method,
                                        insertText: method + '(${1:})',
                                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                        documentation: parts[0] + '.ultrasonic.' + method + ' 메서드'
                                    });
                                }
                            });
                        }
                        
                        // robot. 속성들 (또는 다른 Findee 인스턴스)
                        if (parts.length === 2) {
                            // Findee 인스턴스인지 확인 (robot, a, my_robot 등)
                            const robotProperties = ['motor', 'camera', 'ultrasonic'];
                            robotProperties.forEach(prop => {
                                if (prop.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: prop,
                                        kind: monaco.languages.CompletionItemKind.Property,
                                        insertText: prop,
                                        documentation: objectName + '.' + prop + ' 객체'
                                    });
                                }
                            });
                        }
                        
                        // 모듈 함수들
                        if (importAnalysis.importedModules[objectName]) {
                            const moduleName = importAnalysis.importedModules[objectName];
                            if (moduleFunctions[moduleName]) {
                                moduleFunctions[moduleName].forEach(func => {
                                    if (func.toLowerCase().includes(methodPrefix.toLowerCase())) {
                                        suggestions.push({
                                            label: func,
                                            kind: monaco.languages.CompletionItemKind.Function,
                                            insertText: func + '(${1:})',
                                            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                            documentation: moduleName + '.' + func + ' 함수'
                                        });
                                    }
                                });
                            }
                        }
                    }
                    
                    // 5. import된 모듈의 함수들
                    Object.keys(importAnalysis.importedModules).forEach(alias => {
                        const moduleName = importAnalysis.importedModules[alias];
                        if (moduleFunctions[moduleName]) {
                            moduleFunctions[moduleName].forEach(func => {
                                if (func.toLowerCase().includes(linePrefix.toLowerCase())) {
                                    suggestions.push({
                                        label: alias + '.' + func,
                                        kind: monaco.languages.CompletionItemKind.Function,
                                        insertText: alias + '.' + func + '(${1:})',
                                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                                        documentation: moduleName + '.' + func + ' 함수'
                                    });
                                }
                            });
                        }
                    });
                }
                
                addContextualSuggestions();
                
                // 스니펫 템플릿 추가
                const snippets = [
                    {
                        label: 'for',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'for ${1:item} in ${2:iterable}:\n\t${3:pass}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'for 루프 템플릿'
                    },
                    {
                        label: 'while',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'while ${1:condition}:\n\t${2:pass}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'while 루프 템플릿'
                    },
                    {
                        label: 'if',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'if ${1:condition}:\n\t${2:pass}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'if 조건문 템플릿'
                    },
                    {
                        label: 'def',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'def ${1:function_name}(${2:parameters}):\n\t${3:pass}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: '함수 정의 템플릿'
                    },
                    {
                        label: 'try',
                        kind: monaco.languages.CompletionItemKind.Snippet,
                        insertText: 'try:\n\t${1:pass}\nexcept ${2:Exception} as ${3:e}:\n\t${4:pass}',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        documentation: 'try-except 예외 처리 템플릿'
                    }
                ];
                
                // 스니펫도 추가
                snippets.forEach(snippet => {
                    if (snippet.label.toLowerCase().includes(linePrefix.toLowerCase())) {
                        suggestions.push(snippet);
                    }
                });
                
                return { suggestions: suggestions };
            }
        });
        
        // 에디터 생성
        editor = monaco.editor.create(document.getElementById('monacoEditor'), {
            value: '# Findee 로봇 프로그래밍을 시작하세요!\n# 사용 가능한 객체: robot, time, Findee\n# 변수명은 자유롭게 사용 가능: a = Findee(), my_robot = Findee() 등\n\n# Findee 로봇 초기화\nrobot = Findee()\nprint("Hello, Findee!")',
            language: 'python',
            theme: 'vs-dark',
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            readOnly: false,
            automaticLayout: true,
            minimap: {
                enabled: true
            },
            scrollbar: {
                vertical: 'visible',
                horizontal: 'visible'
            },
            // 자동완성 설정
            quickSuggestions: {
                other: true,
                comments: false,
                strings: true
            },
            suggestOnTriggerCharacters: true,
            acceptSuggestionOnEnter: 'on',
            tabCompletion: 'on',
            wordBasedSuggestions: true
        });

        // 에디터 포커스 이벤트 추가
        editor.onDidFocusEditorWidget(() => {
            editorFocused = true;
            updateKeyboardStatus(false);
            console.log('📝 Editor focused - keyboard control disabled');
        });

        editor.onDidBlurEditorWidget(() => {
            editorFocused = false;
            updateKeyboardStatus(true);
            console.log('📝 Editor blurred - keyboard control enabled');
        });

        // 기본 Python 코드 설정
        editor.setValue(codeExamples.motor_test);
    });
}

// import 문 분석 함수
function analyzeImports(model) {
    const importedModules = {};
    const lines = model.getLinesContent();
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // import 모듈명
        const importMatch = line.match(/^import\s+(\w+)/);
        if (importMatch) {
            const moduleName = importMatch[1];
            importedModules[moduleName] = moduleName;
        }
        
        // from 모듈명 import 함수명
        const fromImportMatch = line.match(/^from\s+(\w+)\s+import\s+(.+)/);
        if (fromImportMatch) {
            const moduleName = fromImportMatch[1];
            const imports = fromImportMatch[2].split(',').map(s => s.trim());
            
            imports.forEach(importItem => {
                // as 별칭 처리
                const asMatch = importItem.match(/(\w+)\s+as\s+(\w+)/);
                if (asMatch) {
                    importedModules[asMatch[2]] = moduleName;
                } else {
                    importedModules[importItem] = moduleName;
                }
            });
        }
        
        // import 모듈명 as 별칭
        const importAsMatch = line.match(/^import\s+(\w+)\s+as\s+(\w+)/);
        if (importAsMatch) {
            const moduleName = importAsMatch[1];
            const alias = importAsMatch[2];
            importedModules[alias] = moduleName;
        }
    }
    
    return { importedModules };
} 