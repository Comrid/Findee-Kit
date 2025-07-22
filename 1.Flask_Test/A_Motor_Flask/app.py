"""
Findee Robot Flask Web Controller

간소화된 로봇 제어 웹 애플리케이션
- Flask + Socket.IO를 사용한 실시간 로봇 제어
- MJPEG 스트리밍을 통한 카메라 피드
- RESTful API를 통한 상태 조회
"""

from dataclasses import dataclass
import os
import sys
import logging
import threading
import time
from findee import Findee, FindeeFormatter

from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO, emit
from pydantic import BaseModel
from typing import Optional



@dataclass
class FlaskMessage:
    robot_init_start: str = "로봇 초기화 시작"
    robot_init_success: str = "로봇 초기화 성공"
    robot_init_failure: str = "로봇 초기화 실패: {error}"




class Config:
    SECRET_KEY = 'Pathfinder-Findee'
    PORT = 5000
    DEFAULT_SPEED = 60
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



# 실시간 업데이트를 위한 전역 변수
update_thread = None
update_running = False

class Info(BaseModel):
    connected: bool = robot_status
    running: bool = robot_status
    motor_status: bool = robot_status['motor_status']
    camera_status: bool = robot_status['camera_status']
    ultrasonic_status: bool = robot_status['ultrasonic_status']
    camera_fps: int = 0
    speed: int = Config.DEFAULT_SPEED
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
        camera_fps=int(robot.camera.fps),
        speed=speed or Config.DEFAULT_SPEED,
        direction='stop'
    ).model_dump()

def broadcast_dashboard_data():
    """모든 클라이언트에게 대시보드 데이터 실시간 전송"""
    global update_running

    while update_running:
        try:
            if robot_connected and robot:
                # 시스템 정보 + 로봇 상태 통합
                dashboard_data = {
                    'system_info': robot.get_system_info(),
                    'robot_status': get_info_data(),
                    'timestamp': time.time()
                }
            else:
                dashboard_data = {
                    'system_info': {'error': 'Robot not connected'},
                    'robot_status': get_info_data(),
                    'timestamp': time.time()
                }

            # 모든 연결된 클라이언트에게 전송
            socketio.emit('dashboard_update', dashboard_data)

        except Exception as e:
            logger.error(f"Dashboard broadcast error: {e}")
        time.sleep(Config.UPDATE_INTERVAL)


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
    return render_template('index.html')





@app.route('/video_feed')
def video_feed():
    if not robot_connected or not robot_status['camera_status']:
        return "Camera not available"

    return Response(
        robot.camera.generate_frames(quality=100),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )





@app.route('/api/system_info')
def api_system_info():
    if not robot_connected:
        return jsonify({'error': 'Robot not connected'})

    try:
        return jsonify(robot.get_system_info())
    except Exception as e:
        return jsonify({'error': str(e)})



@app.route('/api/status')
def api_status():
    return jsonify(get_info_data())

@app.route('/api/dashboard')
def api_dashboard():
    """통합 대시보드 정보 - 시스템 정보 + 로봇 상태"""
    if not robot_connected or not robot:
        return jsonify({
            'system_info': {'error': 'Robot not connected'},
            'robot_status': get_info_data()
        })

    try:
        return jsonify({
            'system_info': robot.get_system_info(),
            'robot_status': get_info_data()
        })
    except Exception as e:
        return jsonify({
            'system_info': {'error': str(e)},
            'robot_status': get_info_data()
        })




@socketio.on('connect')
def handle_connect():
    global update_thread, update_running

    logger.info(f"🔌 Client connected: {request.sid}")

    emit('connection_status', {
        'connected': True,
        'message': 'Connected to Pathfinder server',
        'robot_status': robot_connected
    })

    emit('robot_status', get_info_data())

    # 첫 번째 클라이언트 연결 시 실시간 업데이트 시작
    if not update_running:
        update_running = True
        update_thread = threading.Thread(target=broadcast_dashboard_data, daemon=True)
        update_thread.start()
        logger.info("📡 실시간 대시보드 업데이트 시작")





@socketio.on('disconnect')
def handle_disconnect():
    global update_running

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
    logger.info(f"🎮 Motor control received: {data}")

    # 데이터 유효성 검사
    if not data or 'direction' not in data:
        return emit('motor_feedback', {
            'success': False,
            'error': 'Invalid command data'
        })

    direction = data['direction']
    speed = data.get('speed', Config.DEFAULT_SPEED)

    # 로봇 상태 확인
    if not robot_connected or not robot or not robot_status['motor_status']:
        return emit('motor_feedback', {
            'success': False,
            'direction': direction,
            'error': 'Robot motor not available'
        })

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

    # 명령 실행
    try:
        if direction not in motor_commands:
            return emit('motor_feedback', {
                'success': False,
                'direction': direction,
                'error': f'Direction "{direction}" not implemented'
            })

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
    logger.info(f"📡 Server available at: http://{address}:{Config.PORT}")
    logger.info("=" * 60)

    try:
        socketio.run(app=app, debug=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server shutdown requested...")
    finally:
        global update_running
        update_running = False
        if robot_connected and robot:
            robot.cleanup()






if __name__ == '__main__':
    run_server()