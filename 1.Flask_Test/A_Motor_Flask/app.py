from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO, emit
from findee import Findee, FindeeFormatter
import time
import threading
import cv2
import numpy as np

#-Logger Initialization-#
logger = FindeeFormatter().get_logger()

#-Robot Initialization-#
logger.info("🤖 Initializing Pathfinder robot...")
try:
    robot = Findee(safe_mode=True, camera_resolution=(640, 480))
    logger.info("✅ Robot connected successfully!")
    robot_connected = True

    # 카메라 프레임 캡처 시작
    if robot.camera._is_available:
        robot.camera.start_frame_capture()
        logger.info("📹 Camera frame capture started")

except Exception as e:
    logger.error(f"❌ Robot connection failed: {e}")
    robot_connected = False
    robot = None

#-Flask Initialization-#
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Pathfinder-Findee'

# Socket.IO 초기화
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=False,
                   engineio_logger=False,
                   ping_timeout=60,
                   ping_interval=25,
                   transports=['polling'])

#-Flask Routes-#
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """비디오 스트리밍 엔드포인트 (MJPEG)"""
    if not robot_connected or robot is None or not robot.camera._is_available:
        return "Camera not available", 503

    # findee 모듈의 generate_frames 사용
    return Response(robot.camera.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/system_info')
def api_system_info():
    """시스템 정보 API"""
    if not robot_connected or robot is None:
        return jsonify({'error': 'Robot not connected'}), 503

    try:
        # findee 모듈의 get_system_info 사용
        system_info = robot.get_system_info()

        # 추가적인 Findee 상태 정보
        status = robot.get_status()
        system_info.update({
            'hostname': robot.get_hostname(),
            'camera_fps': robot.camera.fps if robot.camera._is_available else 0,
            'current_resolution': robot.camera.get_current_resolution() if robot.camera._is_available else 'N/A',
            'component_status': status
        })

        return jsonify(system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_status():
    """상태 확인 API"""
    if not robot_connected or robot is None:
        return jsonify({'error': 'Robot not connected'}), 503

    status = robot.get_status()
    return jsonify({
        'running': True,
        'camera_available': status.get('camera', False),
        'motor_available': status.get('motor', False),
        'ultrasonic_available': status.get('ultrasonic', False),
        'current_resolution': robot.camera.get_current_resolution() if robot.camera._is_available else 'N/A',
        'camera_fps': robot.camera.fps if robot.camera._is_available else 0
    })

@socketio.on('connect')
def handle_connect():
    """클라이언트가 연결되었을 때"""
    logger.info(f"🔌 Client connected: {request.sid}")

    # 클라이언트에게 연결 상태 알림
    emit('connection_status', {
        'connected': True,
        'message': 'Connected to Pathfinder server',
        'robot_status': robot_connected
    })

    # 로봇 상태도 함께 전송
    if robot_connected:
        status = robot.get_status()
        emit('robot_status', {
            'connected': True,
            'speed': 60,  # 기본 속도
            'direction': 'stop',
            'camera_available': status.get('camera', False),
            'motor_available': status.get('motor', False),
            'ultrasonic_available': status.get('ultrasonic', False)
        })

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트가 연결을 끊었을 때"""
    logger.info(f"🔌 Client disconnected: {request.sid}")

    # 안전을 위해 로봇 정지
    if robot_connected and robot and robot.motor._is_available:
        try:
            robot.motor.stop()
            logger.info("🛑 Robot stopped due to client disconnect")
        except Exception as e:
            logger.error(f"❌ Error stopping robot: {e}")

@socketio.on('motor_control')
def handle_motor_control(data):
    """모터 제어 명령 처리"""
    logger.info(f"🎮 Motor control received: {data}")

    # 데이터 유효성 검사
    if not data or 'direction' not in data:
        emit('motor_feedback', {
            'success': False,
            'error': 'Invalid command data'
        })
        return

    direction = data['direction']
    speed = data.get('speed', 60)  # 기본값 60

    # 로봇 연결 및 모터 상태 확인
    if not robot_connected or robot is None or not robot.motor._is_available:
        emit('motor_feedback', {
            'success': False,
            'direction': direction,
            'error': 'Robot motor not available'
        })
        return

    # 실제 모터 제어 실행
    try:
        if direction == 'forward':
            robot.motor.move_forward(speed)
        elif direction == 'backward':
            robot.motor.move_backward(speed)
        elif direction == 'rotate-left':
            robot.motor.turn_left(speed)
        elif direction == 'rotate-right':
            robot.motor.turn_right(speed)
        elif direction == 'curve-left':
            robot.motor.curve_left(speed, 30)  # 30도 곡선
        elif direction == 'curve-right':
            robot.motor.curve_right(speed, 30)  # 30도 곡선
        elif direction == 'stop':
            robot.motor.stop()
        else:
            emit('motor_feedback', {
                'success': False,
                'direction': direction,
                'error': f'Direction "{direction}" not implemented yet'
            })
            return

        # 성공 응답
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

if __name__ == '__main__':
    logger.info("🚀 Pathfinder Robot Control Server Starting...")
    logger.info("🔧 Server starting on all network interfaces...")

    if robot_connected:
        logger.info(f"📡 Server will be available at: http://{robot.get_hostname()}:5000")
        status = robot.get_status()
        logger.info(f"🤖 Robot status - Motor: {status.get('motor', False)}, Camera: {status.get('camera', False)}, Ultrasonic: {status.get('ultrasonic', False)}")
    else:
        logger.info("📡 Server will be available at: http://localhost:5000")

    logger.info("🌐 Socket.IO for motor control, MJPEG for camera streaming")
    logger.info("=" * 60)

    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server shutdown requested...")
    finally:
        # 정리 작업
        if robot_connected and robot:
            try:
                robot.cleanup()
                logger.info("✅ Robot cleanup completed")
            except Exception as e:
                logger.error(f"❌ Error during cleanup: {e}")
        logger.info("✅ Server shutdown completed")