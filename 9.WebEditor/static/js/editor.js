/*
 * CONTENTS
 * ========
 * Monaco Editor Initialization
 * Editor Configuration
 * IntelliSense Configuration
 * Editor Event Handlers
 */

// Initialize Monaco Editor
function initializeMonacoEditor() {
    require.config({
        paths: {
            vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs'
        }
    });

    require(['vs/editor/editor.main'], function() {
        // Monaco Editor의 내장 Python 지원 사용
        // 토큰화 규칙은 내장 지원 사용, 자동완성만 추가

        const pythonKeywords = [
            'and', 'assert', 'async', 'await',
            'break',
            'case', 'class', 'continue',
            'def', 'del',
            'elif', 'else', 'except',
            'finally', 'for', 'from', 'False',
            'global',
            'if', 'import', 'in', 'is',
            'lambda',
            'match',
            'nonlocal', 'not', 'None',
            'or',
            'pass',
            'raise', 'return',
            'try', 'True',
            'while', 'with',
            'yield'
        ];

        const pythonFunctions = [
            'abs', 'aiter', 'all', 'anext', 'any', 'ascii',
            'bin', 'breakpoint', '__build_class__',
            'callable', 'chr', 'compile', 'copyright', 'credits',
            'delattr', 'dir', 'divmod',
            'eval', 'exec', 'exit',
            'format',
            'getattr', 'globals',
            'hasattr', 'hash', 'help', 'hex',
            'id', 'input', 'isinstance', 'issubclass', 'iter', '__import__',
            'len', 'license', 'locals',
            'max', 'min',
            'next',
            'oct', 'open', 'ord',
            'pow', 'print',
            'quit',
            'repr', 'round',
            'setattr', 'sorted', 'sum',
            'tuple', 'type',
            'vars',
        ];

        const pythonClasses = [
            'ArithmeticError', 'AssertionError', 'AttributeError',
            'bytes', 'bool', 'bytearray', 'BaseException', 'BaseExceptionGroup', 'BlockingIOError', 'BrokenPipeError', 'BufferError', 'BytesWarning',
            'classmethod', 'complex', 'ChildProcessError', 'ConnectionAbortedError', 'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
            'dict', 'DeprecationWarning',
            'enumerate', 'EncodingWarning', 'EOFError', 'Exception', 'ExceptionGroup',
            'filter', 'float', 'frozenset', 'function', 'FileExistsError', 'FileNotFoundError', 'FloatingPointError', 'FutureWarning',
            'GeneratorExit',
            'int', 'ImportError', 'ImportWarning', 'IndentationError', 'IndexError', 'InterruptedError', 'IsADirectoryError',
            'KeyboardInterrupt', 'KeyError',
            'list', 'LookupError',
            'map', 'memoryview', 'MemoryError', 'ModuleNotFoundError',
            'NameError', 'NotADirectoryError', 'NotImplementedError',
            'object', 'OSError', 'OverflowError',
            'property', 'PendingDeprecationWarning', 'PermissionError', 'ProcessLookupError', 'PythonFinalizationError',
            'range', 'reversed', 'RecursionError', 'ReferenceError', 'ResourceWarning', 'RuntimeError', 'RuntimeWarning',
            'set', 'slice', 'staticmethod', 'str', 'super', 'StopAsyncIteration', 'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
            'tuple', 'type', 'TimeoutError', 'TabError', 'TypeError',
            'UnicodeTranslateError', 'UnboundLocalError', 'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError', 'UnicodeWarning', 'UserWarning',
            'ValueError',
            'Warning',
            'zip', 'ZeroDivisionError'
        ];

        const pythonValuables = [
            '__annotations__',
            '__builtins__',
            '__cached__',
            '__dict__', '__doc__',
            'ellipsis', 'Ellipsis', 'EnvironmentError',
            '__file__',
            'IOError',
            '__loader__',
            'NotImplemented', '__name__',
            '__package__', '__path__',
            '__spec__',
            'WindowsError',
        ]

        const pythonModules = [
            'math', 'random', 'os', 'sys', 'time', 'findee', 'cv2', 'numpy',
            'pandas'
        ];

        // 자동완성 프로바이더 등록
        monaco.languages.registerCompletionItemProvider('python', {
            provideCompletionItems: function(model, position) {
                const suggestions = [
                    // 키워드들
                    ...pythonKeywords.map(keyword => ({
                        label: keyword,
                        insertText: keyword,
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        documentation: `Python keyword: ${keyword}`
                    })),

                    // 함수들
                    ...pythonFunctions.map(func => ({
                        label: func,
                        insertText: func,
                        kind: monaco.languages.CompletionItemKind.Function,
                        documentation: `Built-in function: ${func}`
                    })),

                    // 클래스들
                    ...pythonClasses.map(cls => ({
                        label: cls,
                        insertText: cls,
                        kind: monaco.languages.CompletionItemKind.Class,
                        documentation: `Built-in class: ${cls}`
                    })),

                    // Valuables
                    ...pythonValuables.map(valuable => ({
                        label: valuable,
                        insertText: valuable,
                        kind: monaco.languages.CompletionItemKind.Variable,
                        documentation: `Python valuable: ${valuable}`
                    })),

                    // 모듈들
                    ...pythonModules.map(module => ({
                        label: module,
                        insertText: module,
                        kind: monaco.languages.CompletionItemKind.Module,
                        documentation: `Python module: ${module}`
                    }))
                ];

                return { suggestions: suggestions };
            }
        });

        // 에디터 생성
        const editor = monaco.editor.create(document.getElementById('monaco-editor'), {
            value: getInitialCode(),
            language: 'python',  // Monaco Editor의 내장 Python 지원 사용
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 16,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',

            // IntelliSense 설정
            wordBasedSuggestions: true,
            quickSuggestions: {
                other: true,
                comments: true,
                strings: true
            },
            quickSuggestionsDelay: 0,
            suggestOnTriggerCharacters: true,
            tabCompletion: 'on',
            autoClosingPairs: 'always',
            autoSurround: 'quotes',

            // 추가 IntelliSense 옵션
            suggest: {
                showKeywords: true,
                showSnippets: true,
                showClasses: true,
                showFunctions: true,
                showVariables: true,
                showModules: true,
                showProperties: true,
                showEvents: true,
                showOperators: true,
                showUnits: true,
                showValues: true,
                showConstants: true,
                showEnums: true,
                showEnumMembers: true,
                showColors: true,
                showFiles: true,
                showReferences: true,
                showFolders: true,
                showTypeParameters: true,
                showWords: true
            }
        });

        // 윈도우 리사이즈 시 에디터 크기 조정
        window.addEventListener('resize', () => {
            editor.layout();
        });

        // 전역 변수로 에디터 인스턴스 저장
        window.monacoEditor = editor;
        
        // action.js에서 사용할 수 있도록 설정
        if (window.setMonacoEditor) {
            window.setMonacoEditor(editor);
        }
    });
}

function getInitialCode() {
    return `# Welcome to Findee Python Web Editor
# Start coding with Monaco Editor's built-in Python support!

def greet(name):
    """Simple greeting function"""
    return f"Hello, {name}!"

# Try typing and see Monaco Editor's built-in IntelliSense in action
print("Hello, World!")
print(greet("Python"))

# All Python keywords, functions, and classes are automatically supported
# Keywords: def, class, if, for, while, try, import, from, return, etc.
# Functions: print, len, range, abs, all, any, etc.
# Classes: list, dict, str, int, float, bool, etc.
# Values: True, False, None
`;
}