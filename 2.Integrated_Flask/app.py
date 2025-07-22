"""
Findee Integrated Flask Web Application

통합 로봇 제어 웹 애플리케이션
- Flask + Socket.IO를 사용한 실시간 로봇 제어
- MJPEG 스트리밍을 통한 카메라 피드
- RESTful API를 통한 상태 조회 및 초음파 센서 제어
- Findee 모듈을 통한 하드웨어 제어
"""

from dataclasses import dataclass
import os
import sys
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from findee import Findee, FindeeFormatter

from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO, emit
from pydantic import BaseModel


@dataclass
class FlaskMessage:
    robot_init_start: str = "로봇 초기화 시작"
    robot_init_success: str = "로봇 초기화 성공"
    robot_init_failure: str = "로봇 초기화 실패: {error}"


@dataclass
class SensorConfig:
    """초음파 센서 설정 데이터 클래스"""
    interval: float = 1.0


class Config:
    SECRET_KEY = 'Integrated-Findee-Dashboard'
    PORT = 5000
    CAMERA_RESOLUTION = (640, 480)
    SOCKET_TIMEOUT = 60
    SOCKET_PING_INTERVAL = 25
    UPDATE_INTERVAL = 1  # 실시간 업데이트 주기 (초)

#-Findee Logger Initialization-#
logger = FindeeFormatter().get_logger()
FindeeFormatter.disable_flask_logger()


#-Findee Robot Initialization-#
logger.info(FlaskMessage.robot_init_start)
robot = Findee(safe_mode=True, camera_resolution=Config.CAMERA_RESOLUTION)

robot_status = robot.get_status()

if robot_status['camera_status']:
    robot.camera.start_frame_capture()

robot_connected = True
logger.info(FlaskMessage.robot_init_success)


class Info(BaseModel):
    connected: bool = robot_connected
    running: bool = robot_connected
    motor_status: bool = robot_status['motor_status']
    camera_status: bool = robot_status['camera_status']
    ultrasonic_status: bool = robot_status['ultrasonic_status']
    camera_fps: int = 0
    speed: int = 60
    direction: str = 'stop'

def get_info_data(speed: int = None) -> dict:
    if not robot_connected or not robot:
        return Info(
            connected=False,
            running=False,
            motor_status=False,
            camera_status=False,
            ultrasonic_status=False,
            camera_fps=0
        ).model_dump()

    current_status = robot.get_status()
    return Info(
        connected=robot_connected,
        running=robot_connected,
        motor_status=current_status['motor_status'],
        camera_status=current_status['camera_status'],
        ultrasonic_status=current_status['ultrasonic_status'],
        camera_fps=int(robot.camera.fps) if robot_status['camera_status'] else 0,
        speed=speed or 60,
        direction='stop'
    ).model_dump()


# 초음파 센서 관련 변수
sensor_config = SensorConfig()
_sensor_thread: Optional[threading.Thread] = None
_sensor_stop_event = threading.Event()
_sensor_running = False


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
    global _sensor_running
    while not _sensor_stop_event.is_set():
        try:
            distance = _get_distance()
            if distance is not None:
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Socket.IO로 실시간 데이터 전송
                socketio.emit('ultrasonic_data', {
                    'distance': distance,
                    'timestamp': timestamp
                })
            
            time.sleep(sensor_config.interval)
            
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
    transports=['websocket', 'polling']  # WebSocket 우선, polling 백업
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
        robot.camera.generate_frames(quality=100),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/system_info')
def api_system_info():
    """시스템 정보 API"""
    if not robot_connected:
        return jsonify({'error': 'Robot not connected'})

    try:
        # Findee 모듈의 get_system_info 사용
        system_info = robot.get_system_info()
        current_status = robot.get_status()

        # Findee SystemInfo 필드명을 JavaScript에서 기대하는 키로 매핑
        mapped_system_info = {
            'hostname': system_info.get('hostname', 'localhost'),
            'cpu_usage': system_info.get('cpu_percent', 0.0),  # cpu_percent -> cpu_usage
            'cpu_temp': system_info.get('cpu_temperature', 0.0),  # cpu_temperature -> cpu_temp
            'memory_usage': system_info.get('memory_percent', 0.0),  # memory_percent -> memory_usage
            'num_cpu_cores': system_info.get('num_cpu_cores', 1),
            'cpu_cores_percent': system_info.get('cpu_cores_percent', []),
            'camera_fps': robot.camera.fps if robot_status['camera_status'] else 0,
            'current_resolution': robot.camera.get_current_resolution() if robot_status['camera_status'] else 'N/A',
            'camera_status': current_status['camera_status'],
            'motor_status': current_status['motor_status'],
            'ultrasonic_status': current_status['ultrasonic_status']
        }
        
        # IP 주소 추가 (hostname에서 추출)
        hostname = mapped_system_info['hostname']
        if hostname and hostname != 'localhost':
            # hostname이 IP 주소인 경우 (예: "192.168.1.100")
            mapped_system_info['ip_address'] = hostname
        else:
            mapped_system_info['ip_address'] = '--'

        return jsonify(mapped_system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """상태 확인 API"""
    return jsonify(get_info_data())


@app.route('/api/resolutions')
def api_resolutions():
    """사용 가능한 해상도 목록 API"""
    if not robot_connected or not robot_status['camera_status']:
        return jsonify({'error': 'Camera not available'}), 503

    try:
        resolutions = robot.camera.get_available_resolutions()
        current_resolution = robot.camera.get_current_resolution()
        
        # 해상도 데이터를 문자열로 변환
        formatted_resolutions = []
        for resolution in resolutions:
            if isinstance(resolution, (list, tuple)) and len(resolution) == 2:
                # (width, height) 형태인 경우
                formatted_resolutions.append(f"{resolution[0]}x{resolution[1]}")
            elif isinstance(resolution, dict) and 'width' in resolution and 'height' in resolution:
                # {'width': x, 'height': y} 형태인 경우
                formatted_resolutions.append(f"{resolution['width']}x{resolution['height']}")
            elif isinstance(resolution, str):
                # 이미 문자열인 경우
                formatted_resolutions.append(resolution)
            else:
                # 기타 형태는 문자열로 변환
                formatted_resolutions.append(str(resolution))
        
        return jsonify({
            'resolutions': formatted_resolutions,
            'current': current_resolution
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/resolution', methods=['POST'])
def api_change_resolution():
    """해상도 변경 API"""
    if not robot_connected or not robot_status['camera_status']:
        return jsonify({'error': 'Camera not available'}), 503

    try:
        data = request.get_json()
        resolution = data.get('resolution')

        if not resolution:
            return jsonify({'error': 'Resolution not provided'}), 400

        # 해상도 파싱 (예: "640x480")
        try:
            width, height = map(int, resolution.split('x'))
        except ValueError:
            return jsonify({'error': 'Invalid resolution format'}), 400

        # Findee 모듈의 configure_resolution 사용
        robot.camera.configure_resolution((width, height))

        return jsonify({
            'success': True,
            'resolution': f"{width}x{height}",
            'message': f'해상도가 {width}x{height}로 변경되었습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '해상도 변경 중 오류가 발생했습니다.'
        }), 500


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
        logger.error(f"❌ Error starting ultrasonic measurement: {e}")
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
        logger.error(f"❌ Error stopping ultrasonic measurement: {e}")
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
            'config': {
                'interval': sensor_config.interval
            }
        })
    
    try:
        data = request.get_json()
        if 'interval' in data:
            sensor_config.interval = max(0.1, float(data['interval']))
        
        return jsonify({
            'success': True,
            'message': '설정이 업데이트되었습니다.',
            'config': {
                'interval': sensor_config.interval
            }
        })
    except Exception as e:
        logger.error(f"❌ Error updating ultrasonic config: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@socketio.on('connect')
def handle_connect():
    """클라이언트가 연결되었을 때"""
    global update_thread, update_running

    logger.info(f"🔌 Client connected: {request.sid}")

    emit('connection_status', {
        'connected': True,
        'message': 'Connected to Integrated Findee server',
        'robot_status': robot_connected
    })

    if robot_connected:
        status = robot.get_status()
        emit('robot_status', {
            'connected': True,
            'speed': 60,
            'direction': 'stop',
            'camera_available': status.get('camera_status', False),
            'motor_available': status.get('motor_status', False),
            'ultrasonic_available': status.get('ultrasonic_status', False)
        })


@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트가 연결을 끊었을 때"""
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
        'forward-right': lambda: robot.motor.curve_right(speed, 30),
        'backward-left': lambda: robot.motor.curve_left(-speed, 30),
        'backward-right': lambda: robot.motor.curve_right(-speed, 30),
        'stop': lambda: robot.motor.stop()
    }

    # 명령 실행
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


def run_server():
    address = robot.get_hostname() if robot_connected else "localhost"
    logger.info(f"📡 Integrated server available at: http://{address}:{Config.PORT}")
    logger.info("=" * 60)

    try:
        socketio.run(app=app, debug=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server shutdown requested...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        # 센서 측정 중지
        try:
            _stop_sensor_measurement()
        except Exception as e:
            logger.error(f"❌ Error stopping sensor measurement: {e}")
        
        # 로봇 정리
        if robot_connected and robot:
            try:
                robot.cleanup()
            except Exception as e:
                logger.error(f"❌ Error cleaning up robot: {e}")


if __name__ == '__main__':
    run_server()
