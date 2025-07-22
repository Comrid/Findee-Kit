"""
Findee Web Code Editor

웹 기반 Python 코드 에디터
- 실시간 코드 편집 및 실행
- Findee 로봇 하드웨어 제어 (카메라, 모터, 초음파 센서)
- 무한루프 실행 지원
- 실시간 디버깅 환경
"""

import os
import sys
import logging
import threading
import time

import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from findee import Findee, FindeeFormatter

from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO, emit
from pydantic import BaseModel


@dataclass
class FlaskMessage:
    robot_init_start: str = "로봇 초기화 시작"
    robot_init_success: str = "로봇 초기화 성공"
    robot_init_failure: str = "로봇 초기화 실패: {error}"
    code_execution_start: str = "코드 실행 시작"
    code_execution_success: str = "코드 실행 완료"
    code_execution_error: str = "코드 실행 오류: {error}"


@dataclass
class CodeExecutionResult:
    """코드 실행 결과 데이터 클래스"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = ""


class CodeExecutionRequest(BaseModel):
    code: str
    timeout: int = 30  # 기본 30초 타임아웃


class Config:
    SECRET_KEY = 'Findee-Web-Editor'
    PORT = 5000
    CAMERA_RESOLUTION = (640, 480)
    SOCKET_TIMEOUT = 60
    SOCKET_PING_INTERVAL = 25
    MAX_CODE_LENGTH = 10000  # 최대 코드 길이
    DEFAULT_TIMEOUT = 30  # 기본 실행 타임아웃 (초)
    INFINITE_LOOP_TIMEOUT = 300  # 무한루프 감지 타임아웃 (초)

# Findee Logger Initialization
logger = FindeeFormatter().get_logger()
FindeeFormatter.disable_flask_logger()

# Findee Robot Initialization
logger.info(FlaskMessage.robot_init_start)
robot = Findee(safe_mode=True, camera_resolution=Config.CAMERA_RESOLUTION)

robot_status = robot.get_status()

if robot_status['camera_status']:
    robot.camera.start_frame_capture()

robot_connected = True
logger.info(FlaskMessage.robot_init_success)

# 코드 실행 관련 변수
_code_execution_thread: Optional[threading.Thread] = None
_code_stop_event = threading.Event()
_code_running = False
_code_output_buffer = []
_code_output_lock = threading.Lock()

# 초음파 센서 관련 변수
_sensor_config = {'interval': 1.0}
_sensor_readings: List[Dict[str, Any]] = []
_sensor_data_lock = threading.Lock()
_sensor_thread: Optional[threading.Thread] = None
_sensor_stop_event = threading.Event()
_sensor_running = False


def _safe_execute_code(code: str, timeout: int = Config.DEFAULT_TIMEOUT) -> CodeExecutionResult:
    """안전한 코드 실행 (실시간 출력 지원)"""
    start_time = time.time()
    output_buffer = []
    error_message = None
    
    # 실시간 출력을 위한 함수
    def real_time_print(*args):
        output = ' '.join(map(str, args))
        output_buffer.append(output)
        # Socket.IO로 즉시 전송
        socketio.emit('code_output', {
            'output': output,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
    
    # 로컬 네임스페이스에 Findee 객체 추가
    local_namespace = {
        'robot': robot,
        'Findee': Findee,  # Findee 클래스 추가 - 사용자가 직접 Findee() 호출 가능
        'time': time,
        'print': real_time_print,  # 실시간 출력 함수 사용
        '__builtins__': __builtins__
    }
    
    try:
        # 코드 실행을 별도 스레드에서 실행
        def execute_in_thread():
            try:
                exec(code, local_namespace)
            except Exception as e:
                nonlocal error_message
                error_message = str(e)
                real_time_print(f"Error: {str(e)}")
        
        execution_thread = threading.Thread(target=execute_in_thread, daemon=True)
        execution_thread.start()
        
        # 타임아웃 설정
        execution_thread.join(timeout=timeout)
        
        if execution_thread.is_alive():
            # 타임아웃 발생
            error_message = f"코드 실행이 {timeout}초 후 타임아웃되었습니다."
            real_time_print(error_message)
        
        execution_time = time.time() - start_time
        
        return CodeExecutionResult(
            success=error_message is None,
            output='\n'.join(output_buffer),
            error=error_message,
            execution_time=execution_time,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return CodeExecutionResult(
            success=False,
            output='\n'.join(output_buffer),
            error=str(e),
            execution_time=execution_time,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )


def _stream_code_output():
    """코드 실행 중 실시간 출력 스트리밍"""
    while _code_running and not _code_stop_event.is_set():
        with _code_output_lock:
            if _code_output_buffer:
                output = _code_output_buffer.pop(0)
                socketio.emit('code_output', {
                    'output': output,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
        time.sleep(0.1)


def _get_distance() -> Optional[float]:
    """거리 측정"""
    if robot_connected and robot and robot_status['ultrasonic_status']:
        try:
            return robot.ultrasonic.get_distance()
        except Exception as e:
            logger.error(f"❌ Ultrasonic sensor error: {e}")
            return None
    else:
        # 시뮬레이션 모드
        import random
        return round(random.uniform(5.0, 200.0), 1)


def _sensor_measurement_loop():
    """초음파 센서 측정 루프"""
    while not _sensor_stop_event.is_set():
        try:
            distance = _get_distance()
            if distance is not None:
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                reading = {
                    'distance': distance,
                    'timestamp': timestamp
                }
                
                with _sensor_data_lock:
                    _sensor_readings.append(reading)
                    if len(_sensor_readings) > 50:  # 최대 50개 데이터 유지
                        _sensor_readings.pop(0)
                
                # Socket.IO로 실시간 데이터 전송
                socketio.emit('ultrasonic_data', {
                    'distance': distance,
                    'timestamp': timestamp
                })
            
            time.sleep(_sensor_config['interval'])
            
        except Exception as e:
            logger.error(f"❌ Sensor measurement error: {e}")
            time.sleep(1)


def _start_sensor_measurement() -> bool:
    """초음파 센서 측정 시작"""
    global _sensor_running
    if _sensor_running:
        return True
    
    try:
        _sensor_stop_event.clear()
        _sensor_thread = threading.Thread(target=_sensor_measurement_loop, daemon=True)
        _sensor_thread.start()
        _sensor_running = True
        logger.info("📡 Ultrasonic sensor measurement started")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start sensor measurement: {e}")
        return False


def _stop_sensor_measurement() -> bool:
    """초음파 센서 측정 중지"""
    global _sensor_running
    if not _sensor_running:
        return True
    
    try:
        _sensor_stop_event.set()
        if _sensor_thread and _sensor_thread.is_alive():
            _sensor_thread.join(timeout=2)
        _sensor_running = False
        logger.info("📡 Ultrasonic sensor measurement stopped")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stop sensor measurement: {e}")
        return False


# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Socket.IO 초기화
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=Config.SOCKET_TIMEOUT,
    ping_interval=Config.SOCKET_PING_INTERVAL,
    transports=['websocket', 'polling']
)


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """비디오 스트리밍 엔드포인트"""
    if not robot_connected or not robot_status['camera_status']:
        return "Camera not available", 503

    return Response(
        robot.camera.generate_frames(quality=80),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/system_info')
def api_system_info():
    """시스템 정보 API"""
    if not robot_connected:
        return jsonify({'error': 'Robot not connected'})

    try:
        system_info = robot.get_system_info()
        current_status = robot.get_status()

        system_info.update({
            'hostname': robot.get_hostname(),
            'camera_fps': robot.camera.fps if robot_status['camera_status'] else 0,
            'current_resolution': robot.camera.get_current_resolution() if robot_status['camera_status'] else 'N/A',
            'camera_status': current_status['camera_status'],
            'motor_status': current_status['motor_status'],
            'ultrasonic_status': current_status['ultrasonic_status'],
            'code_running': _code_running
        })

        return jsonify(system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """상태 확인 API"""
    return jsonify({
        'connected': robot_connected,
        'motor_available': robot_status['motor_status'],
        'camera_available': robot_status['camera_status'],
        'ultrasonic_available': robot_status['ultrasonic_status'],
        'code_running': _code_running
    })


@app.route('/api/execute', methods=['POST'])
def api_execute_code():
    """코드 실행 API"""
    global _code_running, _code_execution_thread
    
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'Code not provided'}), 400
        
        code = data['code']
        timeout = data.get('timeout', Config.DEFAULT_TIMEOUT)
        
        if len(code) > Config.MAX_CODE_LENGTH:
            return jsonify({'error': f'Code too long (max {Config.MAX_CODE_LENGTH} characters)'}), 400
        
        if _code_running:
            return jsonify({'error': 'Code is already running'}), 409
        
        # 코드 실행 시작
        _code_running = True
        _code_stop_event.clear()
        
        def execute_code():
            global _code_running
            try:
                result = _safe_execute_code(code, timeout)
                socketio.emit('code_execution_result', {
                    'success': result.success,
                    'output': result.output,
                    'error': result.error,
                    'execution_time': result.execution_time,
                    'timestamp': result.timestamp
                })
            except Exception as e:
                socketio.emit('code_execution_result', {
                    'success': False,
                    'output': '',
                    'error': str(e),
                    'execution_time': 0,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
            finally:
                _code_running = False
        
        _code_execution_thread = threading.Thread(target=execute_code, daemon=True)
        _code_execution_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Code execution started',
            'execution_id': id(_code_execution_thread)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def api_stop_code():
    """코드 실행 중지 API"""
    global _code_running
    
    try:
        if not _code_running:
            return jsonify({'error': 'No code is running'}), 409
        
        _code_stop_event.set()
        _code_running = False
        
        # 모터 정지 (안전을 위해)
        if robot_connected and robot_status['motor_status']:
            try:
                robot.motor.stop()
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': 'Code execution stopped'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save', methods=['POST'])
def api_save_code():
    """코드 저장 API"""
    try:
        data = request.get_json()
        if not data or 'code' not in data or 'filename' not in data:
            return jsonify({'error': 'Code and filename required'}), 400
        
        code = data['code']
        filename = data['filename']
        
        # 파일명 검증
        if not filename.endswith('.py'):
            filename += '.py'
        
        # 안전한 파일명인지 확인
        if '/' in filename or '\\' in filename or filename.startswith('.'):
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(app.static_folder, 'workspace', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return jsonify({
            'success': True,
            'message': f'Code saved as {filename}',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/load/<filename>')
def api_load_code(filename):
    """코드 로드 API"""
    try:
        if not filename.endswith('.py'):
            filename += '.py'
        
        filepath = os.path.join(app.static_folder, 'workspace', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        return jsonify({
            'success': True,
            'code': code,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files')
def api_list_files():
    """작업공간 파일 목록 API"""
    try:
        workspace_dir = os.path.join(app.static_folder, 'workspace')
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)
        
        files = []
        for filename in os.listdir(workspace_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(workspace_dir, filename)
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return jsonify({
            'success': True,
            'files': sorted(files, key=lambda x: x['modified'], reverse=True)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Socket.IO 이벤트 핸들러
@socketio.on('connect')
def handle_connect():
    """클라이언트 연결"""
    logger.info(f"🔌 Client connected: {request.sid}")
    
    emit('connection_status', {
        'connected': True,
        'message': 'Connected to Findee Web Editor',
        'robot_status': robot_connected
    })
    
    if robot_connected:
        status = robot.get_status()
        emit('robot_status', {
            'connected': True,
            'camera_available': status.get('camera_status', False),
            'motor_available': status.get('motor_status', False),
            'ultrasonic_available': status.get('ultrasonic_status', False),
            'code_running': _code_running
        })


@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제"""
    logger.info(f"🔌 Client disconnected: {request.sid}")
    
    # 안전을 위해 로봇 정지
    if robot_connected and robot and robot_status['motor_status']:
        try:
            robot.motor.stop()
            logger.info("🛑 Robot stopped due to client disconnect")
        except Exception as e:
            logger.error(f"❌ Error stopping robot: {e}")


@socketio.on('motor_control')
def handle_motor_control(data):
    """모터 제어 명령 처리"""
    logger.info(f"🎮 Motor control received: {data}")
    
    if not data or 'direction' not in data:
        emit('motor_feedback', {
            'success': False,
            'error': 'Invalid command data'
        })
        return
    
    direction = data['direction']
    speed = data.get('speed', 60)
    
    if not robot_connected or not robot or not robot_status['motor_status']:
        emit('motor_feedback', {
            'success': False,
            'direction': direction,
            'error': 'Robot motor not available'
        })
        return
    
    # 모터 제어 명령 매핑
    motor_commands = {
        'forward': lambda: robot.motor.move_forward(speed),
        'backward': lambda: robot.motor.move_backward(speed),
        'rotate-left': lambda: robot.motor.turn_left(speed),
        'rotate-right': lambda: robot.motor.turn_right(speed),
        'forward-left': lambda: robot.motor.curve_left(speed, 30),
        'backward-left': lambda: robot.motor.curve_left(-speed, 30),
        'forward-right': lambda: robot.motor.curve_right(speed, 30),
        'backward-right': lambda: robot.motor.curve_right(-speed, 30),
        'stop': lambda: robot.motor.stop()
    }
    
    try:
        if direction not in motor_commands:
            emit('motor_feedback', {
                'success': False,
                'direction': direction,
                'error': f'Direction "{direction}" not implemented'
            })
            return
        
        motor_commands[direction]()
        
        emit('motor_feedback', {
            'success': True,
            'direction': direction,
            'speed': speed
        })
        
        logger.info(f"✅ Motor command executed: {direction} at {speed}%")
        
    except Exception as e:
        emit('motor_feedback', {
            'success': False,
            'direction': direction,
            'error': str(e)
        })
        logger.error(f"❌ Motor control error: {e}")


# 초음파 센서 API
@app.route('/api/ultrasonic/start', methods=['POST'])
def start_ultrasonic_measurement():
    """초음파 센서 측정 시작 API"""
    try:
        success = _start_sensor_measurement()
        return jsonify({
            'success': success,
            'message': '측정이 시작되었습니다.' if success else '측정 시작에 실패했습니다.',
            'is_running': _sensor_running
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}',
            'is_running': False
        }), 500


@app.route('/api/ultrasonic/stop', methods=['POST'])
def stop_ultrasonic_measurement():
    """초음파 센서 측정 중지 API"""
    try:
        success = _stop_sensor_measurement()
        return jsonify({
            'success': success,
            'message': '측정이 중지되었습니다.' if success else '측정 중지에 실패했습니다.',
            'is_running': _sensor_running
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}',
            'is_running': _sensor_running
        }), 500


@app.route('/api/ultrasonic/config', methods=['GET', 'POST'])
def handle_ultrasonic_config():
    """초음파 센서 설정 API"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': _sensor_config
        })
    
    try:
        data = request.get_json()
        if 'interval' in data:
            _sensor_config['interval'] = max(0.1, float(data['interval']))
        
        return jsonify({
            'success': True,
            'message': '설정이 업데이트되었습니다.',
            'config': _sensor_config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/ultrasonic/data')
def get_ultrasonic_data():
    """초음파 센서 데이터 조회 API"""
    try:
        with _sensor_data_lock:
            data = _sensor_readings.copy()
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'is_running': _sensor_running,
            'config': _sensor_config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/ultrasonic/latest')
def get_latest_ultrasonic():
    """최신 초음파 센서 데이터 반환"""
    try:
        with _sensor_data_lock:
            if _sensor_readings:
                latest = _sensor_readings[-1]
                return jsonify({
                    'success': True,
                    'distance': latest['distance'],
                    'timestamp': latest['timestamp']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '측정 데이터가 없습니다.'
                })
    except Exception as e:
        logger.error(f"최신 초음파 데이터 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'데이터 조회 실패: {str(e)}'
        }), 500

# 카메라 해상도 관련 API 엔드포인트
@app.route('/api/camera/resolutions')
def get_camera_resolutions():
    """사용 가능한 카메라 해상도 목록 반환"""
    try:
        if robot_status['camera_status']:
            resolutions = robot.camera.get_available_resolutions()
            
            # 해상도 목록을 문자열로 변환 (원래 순서 유지)
            resolution_strings = []
            seen_resolutions = set()  # 중복 체크용
            
            for resolution in resolutions:
                resolution_str = None
                
                if isinstance(resolution, (list, tuple)):
                    # (width, height) 형태인 경우
                    width, height = resolution
                    resolution_str = f"{width}x{height}"
                elif isinstance(resolution, dict):
                    # {'label': '640x480 (VGA)', 'value': '640x480', 'width': 640, 'height': 480} 형태인 경우
                    if 'value' in resolution:
                        resolution_str = resolution['value']
                    elif 'width' in resolution and 'height' in resolution:
                        resolution_str = f"{resolution['width']}x{resolution['height']}"
                    elif 'w' in resolution and 'h' in resolution:
                        resolution_str = f"{resolution['w']}x{resolution['h']}"
                elif isinstance(resolution, str):
                    # 이미 문자열인 경우
                    resolution_str = resolution
                else:
                    # 기타 형태는 문자열로 변환
                    resolution_str = str(resolution)
                
                # 중복 제거하면서 원래 순서 유지
                if resolution_str and resolution_str not in seen_resolutions:
                    resolution_strings.append(resolution_str)
                    seen_resolutions.add(resolution_str)
            
            return jsonify({
                'success': True,
                'resolutions': resolution_strings
            })
        else:
            return jsonify({
                'success': False,
                'message': '카메라를 사용할 수 없습니다.'
            })
    except Exception as e:
        logger.error(f"카메라 해상도 목록 조회 실패: {e}")
        # 기본 해상도 목록 반환 (Findee 순서대로)
        default_resolutions = ['320x240', '640x480', '800x600', '1024x768', '1280x720', '1920x1080']
        return jsonify({
            'success': True,
            'resolutions': default_resolutions,
            'message': f'기본 해상도 목록을 반환합니다. (오류: {str(e)})'
        })

@app.route('/api/camera/resolution', methods=['POST'])
def set_camera_resolution():
    """카메라 해상도 설정"""
    try:
        data = request.get_json()
        resolution = data.get('resolution')
        
        if not resolution:
            return jsonify({
                'success': False,
                'message': '해상도가 지정되지 않았습니다.'
            }), 400
        
        if robot_status['camera_status']:
            # 해상도 문자열을 튜플로 변환 (예: "640x480" -> (640, 480))
            if 'x' in resolution:
                width, height = map(int, resolution.split('x'))
                resolution_tuple = (width, height)
            else:
                return jsonify({
                    'success': False,
                    'message': '잘못된 해상도 형식입니다. (예: 640x480)'
                }), 400
            
            # 카메라 해상도 변경 (올바른 메서드명 사용)
            robot.camera.configure_resolution(resolution_tuple)
            
            logger.info(f"카메라 해상도 변경: {resolution}")
            return jsonify({
                'success': True,
                'message': f'해상도가 {resolution}로 변경되었습니다.',
                'resolution': resolution
            })
        else:
            return jsonify({
                'success': False,
                'message': '카메라를 사용할 수 없습니다.'
            })
    except Exception as e:
        logger.error(f"카메라 해상도 설정 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'해상도 설정 실패: {str(e)}'
        }), 500


def run_server():
    """서버 실행"""
    address = robot.get_hostname() if robot_connected else "localhost"
    logger.info(f"📡 Web Editor available at: http://{address}:{Config.PORT}")
    logger.info("=" * 60)
    
    try:
        socketio.run(app=app, debug=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server shutdown requested...")
    finally:
        # 코드 실행 중지
        global _code_running
        _code_running = False
        _code_stop_event.set()
        
        # 초음파 센서 측정 중지
        _stop_sensor_measurement()
        
        # 로봇 정리
        if robot_connected and robot:
            robot.cleanup()


if __name__ == '__main__':
    run_server()
