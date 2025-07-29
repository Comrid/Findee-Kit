from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import subprocess
import sys
import tempfile
import threading
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'findee-secret-key'
# Socket.IO 초기화
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=10,
    transports=['websocket', 'polling']
)


@app.route('/')
def index():
    return render_template('index.html')


#region 코드 실행 부분분
def _stream_lines(pipe, sid, stream_type):
    """파이프에서 라인을 읽어서 클라이언트에 전송"""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                # stdout, stderr 핸들러 실행
                socketio.emit(stream_type, {'output': line.strip()}, room=sid)
    except Exception as e:
        socketio.emit('stderr', {'output': f'스트리밍 오류: {str(e)}'}, room=sid)
    finally:
        pipe.close()


def execute_code(code: str, sid: str):
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # 파이프 생성 (임시 파일 사용)
        process = subprocess.Popen(
            [sys.executable, '-u', tmp_path],  # 임시 파일 경로 사용
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # 버퍼링 완전 비활성화
        )

        threading.Thread(target=_stream_lines,
                         args=(process.stdout, sid, 'stdout'),
                         daemon=True).start()
        threading.Thread(target=_stream_lines,
                         args=(process.stderr, sid, 'stderr'),
                         daemon=True).start()

        process.wait()

    finally:
        # 임시 파일 정리
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # 코드 실행 완료 알림
    socketio.emit('finished', {}, room=sid)

@socketio.on('execute_code')
def handle_execute_code(data):
    try:
        code = data.get('code', '')
        if not code:
            emit('execution_error', {'error': '코드가 제공되지 않았습니다.'})
            return

        # 실행 시작 알림
        emit('execution_started', {'message': '코드 실행을 시작합니다...'})

        # 현재 세션 ID 가져오기
        sid = request.sid

        # 별도 스레드에서 코드 실행
        thread = threading.Thread(
            target=execute_code,
            args=(code, sid)
        )
        thread.daemon = True
        thread.start()

    except Exception as e:
        emit('execution_error', {'error': f'코드 실행 중 오류가 발생했습니다: {str(e)}'})
#endregion

@socketio.on('connect')
def handle_connect():
    """클라이언트가 연결되었을 때 호출"""
    print('클라이언트가 연결되었습니다.')
    emit('connected', {'message': '서버에 연결되었습니다.'})


@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트가 연결을 해제했을 때 호출"""
    print('클라이언트가 연결을 해제했습니다.')


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)