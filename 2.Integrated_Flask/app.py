from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO, emit
import sys
import os
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

# Findee 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../findee'))

try:
    from findee import Findee, FindeeFormatter
    FINDEE_AVAILABLE = True
except ImportError as e:
    print(f"Findee 모듈을 가져올 수 없습니다: {e}")
    print("시뮬레이션 모드로 동작합니다.")
    FINDEE_AVAILABLE = False
    Findee = None
    FindeeFormatter = None

@dataclass
class SensorReading:
    """초음파 센서 읽기 데이터 클래스"""
    distance: float
    timestamp: str
    status: str

@dataclass
class SensorConfig:
    """초음파 센서 설정 데이터 클래스"""
    interval: float = 1.0
    close_threshold: float = 10.0
    far_threshold: float = 100.0
    max_data_points: int = 50

class IntegratedFindeeFlask:
    """통합 Findee Flask 애플리케이션 클래스"""
    
    def __init__(self):
        """초기화"""
        # 로깅 설정
        if FindeeFormatter and FINDEE_AVAILABLE:
            self.logger = FindeeFormatter().get_logger()
        else:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        
        # 로봇 초기화
        self._init_robot()
        
        # Flask 애플리케이션 초기화
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'Integrated-Findee-Dashboard'
        
        # Socket.IO 초기화
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25,
            transports=['polling']
        )
        
        # 초음파 센서 관련 변수
        self.sensor_config = SensorConfig()
        self._sensor_readings: List[SensorReading] = []
        self._data_lock = threading.Lock()
        self._sensor_thread: Optional[threading.Thread] = None
        self._sensor_stop_event = threading.Event()
        self._sensor_running = False
        
        # 라우트 등록
        self._register_routes()
        self._register_socketio_events()
    
    def _init_robot(self):
        """로봇 초기화"""
        self.logger.info("🤖 Initializing Integrated Findee robot...")
        try:
            if FINDEE_AVAILABLE:
                self.robot = Findee(safe_mode=True, camera_resolution=(640, 480))
                self.logger.info("✅ Robot connected successfully!")
                self.robot_connected = True
                
                # 카메라 프레임 캡처 시작
                if self.robot.camera._is_available:
                    self.robot.camera.start_frame_capture()
                    self.logger.info("📹 Camera frame capture started")
            else:
                self.robot = None
                self.robot_connected = False
                self.logger.warning("❌ Findee 모듈 사용 불가 - 시뮬레이션 모드")
        except Exception as e:
            self.logger.error(f"❌ Robot connection failed: {e}")
            self.robot_connected = False
            self.robot = None
    
    def _register_routes(self):
        """Flask 라우트 등록"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/video_feed')
        def video_feed():
            """비디오 스트리밍 엔드포인트 (MJPEG)"""
            if not self.robot_connected or self.robot is None or not self.robot.camera._is_available:
                return "Camera not available", 503
            
            return Response(
                self.robot.camera.generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/api/system_info')
        def api_system_info():
            """시스템 정보 API"""
            if not self.robot_connected or self.robot is None:
                return jsonify({'error': 'Robot not connected'}), 503
            
            try:
                system_info = self.robot.get_system_info()
                status = self.robot.get_status()
                system_info.update({
                    'hostname': self.robot.get_hostname(),
                    'camera_fps': self.robot.camera.fps if self.robot.camera._is_available else 0,
                    'current_resolution': self.robot.camera.get_current_resolution() if self.robot.camera._is_available else 'N/A',
                    'component_status': status
                })
                return jsonify(system_info)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/status')
        def api_status():
            """상태 확인 API"""
            if not self.robot_connected or self.robot is None:
                return jsonify({'error': 'Robot not connected'}), 503
            
            status = self.robot.get_status()
            return jsonify({
                'running': True,
                'camera_available': status.get('camera', False),
                'motor_available': status.get('motor', False),
                'ultrasonic_available': status.get('ultrasonic', False),
                'current_resolution': self.robot.camera.get_current_resolution() if self.robot.camera._is_available else 'N/A',
                'camera_fps': self.robot.camera.fps if self.robot.camera._is_available else 0
            })
        
        @self.app.route('/api/resolutions')
        def api_resolutions():
            """사용 가능한 해상도 목록 API"""
            if not self.robot_connected or not self.robot.camera._is_available:
                return jsonify({'error': 'Camera not available'}), 503
            
            resolutions = self.robot.camera.get_available_resolutions()
            current_resolution = self.robot.camera.get_current_resolution()
            
            return jsonify({
                'resolutions': resolutions,
                'current': current_resolution
            })
        
        @self.app.route('/api/resolution', methods=['POST'])
        def api_change_resolution():
            """해상도 변경 API"""
            if not self.robot_connected or not self.robot.camera._is_available:
                return jsonify({'error': 'Camera not available'}), 503
            
            try:
                data = request.get_json()
                resolution = data.get('resolution')
                
                if not resolution:
                    return jsonify({'error': 'Resolution not provided'}), 400
                
                width, height = map(int, resolution.split('x'))
                self.robot.camera.configure_resolution(width, height)
                
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
        @self.app.route('/api/ultrasonic/start', methods=['POST'])
        def start_ultrasonic_measurement():
            """초음파 센서 측정 시작 API"""
            try:
                success = self._start_sensor_measurement()
                return jsonify({
                    'success': success,
                    'message': '측정이 시작되었습니다.' if success else '측정 시작에 실패했습니다.',
                    'is_running': self._sensor_running
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}',
                    'is_running': False
                }), 500
        
        @self.app.route('/api/ultrasonic/stop', methods=['POST'])
        def stop_ultrasonic_measurement():
            """초음파 센서 측정 중지 API"""
            try:
                success = self._stop_sensor_measurement()
                return jsonify({
                    'success': success,
                    'message': '측정이 중지되었습니다.' if success else '측정 중지에 실패했습니다.',
                    'is_running': self._sensor_running
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}',
                    'is_running': self._sensor_running
                }), 500
        
        @self.app.route('/api/ultrasonic/clear', methods=['POST'])
        def clear_ultrasonic_data():
            """초음파 센서 데이터 초기화 API"""
            try:
                with self._data_lock:
                    self._sensor_readings.clear()
                return jsonify({
                    'success': True,
                    'message': '데이터가 초기화되었습니다.',
                    'data_count': 0
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/ultrasonic/data')
        def get_ultrasonic_data():
            """초음파 센서 데이터 조회 API"""
            try:
                with self._data_lock:
                    data = [asdict(reading) for reading in self._sensor_readings]
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'is_running': self._sensor_running,
                    'config': asdict(self.sensor_config)
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/ultrasonic/latest')
        def get_latest_ultrasonic():
            """최신 초음파 센서 데이터 조회 API"""
            try:
                with self._data_lock:
                    latest = self._sensor_readings[-1] if self._sensor_readings else None
                
                return jsonify({
                    'success': True,
                    'data': asdict(latest) if latest else None,
                    'is_running': self._sensor_running
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/ultrasonic/config', methods=['GET', 'POST'])
        def handle_ultrasonic_config():
            """초음파 센서 설정 API"""
            if request.method == 'GET':
                return jsonify({
                    'success': True,
                    'config': asdict(self.sensor_config)
                })
            
            try:
                data = request.get_json()
                if 'interval' in data:
                    self.sensor_config.interval = max(0.1, float(data['interval']))
                if 'close_threshold' in data:
                    self.sensor_config.close_threshold = max(1.0, float(data['close_threshold']))
                if 'far_threshold' in data:
                    self.sensor_config.far_threshold = max(10.0, float(data['far_threshold']))
                
                return jsonify({
                    'success': True,
                    'message': '설정이 업데이트되었습니다.',
                    'config': asdict(self.sensor_config)
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
    
    def _register_socketio_events(self):
        """Socket.IO 이벤트 등록"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """클라이언트가 연결되었을 때"""
            self.logger.info(f"🔌 Client connected: {request.sid}")
            
            emit('connection_status', {
                'connected': True,
                'message': 'Connected to Integrated Findee server',
                'robot_status': self.robot_connected
            })
            
            if self.robot_connected:
                status = self.robot.get_status()
                emit('robot_status', {
                    'connected': True,
                    'speed': 60,
                    'direction': 'stop',
                    'camera_available': status.get('camera', False),
                    'motor_available': status.get('motor', False),
                    'ultrasonic_available': status.get('ultrasonic', False)
                })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """클라이언트가 연결을 끊었을 때"""
            self.logger.info(f"🔌 Client disconnected: {request.sid}")
            
            if self.robot_connected and self.robot and self.robot.motor._is_available:
                try:
                    self.robot.motor.stop()
                    self.logger.info("🛑 Robot stopped due to client disconnect")
                except Exception as e:
                    self.logger.error(f"❌ Error stopping robot: {e}")
        
        @self.socketio.on('motor_control')
        def handle_motor_control(data):
            """모터 제어 명령 처리"""
            self.logger.info(f"🎮 Motor control received: {data}")
            
            if not data or 'direction' not in data:
                emit('motor_feedback', {
                    'success': False,
                    'error': 'Invalid command data'
                })
                return
            
            direction = data['direction']
            speed = data.get('speed', 60)
            
            if not self.robot_connected or self.robot is None or not self.robot.motor._is_available:
                emit('motor_feedback', {
                    'success': False,
                    'direction': direction,
                    'error': 'Robot motor not available'
                })
                return
            
            try:
                if direction == 'forward':
                    self.robot.motor.move_forward(speed)
                elif direction == 'backward':
                    self.robot.motor.move_backward(speed)
                elif direction == 'rotate-left':
                    self.robot.motor.turn_left(speed)
                elif direction == 'rotate-right':
                    self.robot.motor.turn_right(speed)
                elif direction == 'curve-left':
                    self.robot.motor.curve_left(speed, 30)
                elif direction == 'curve-right':
                    self.robot.motor.curve_right(speed, 30)
                elif direction == 'stop':
                    self.robot.motor.stop()
                else:
                    emit('motor_feedback', {
                        'success': False,
                        'direction': direction,
                        'error': f'Direction "{direction}" not implemented yet'
                    })
                    return
                
                emit('motor_feedback', {
                    'success': True,
                    'direction': direction,
                    'speed': speed
                })
                
                self.logger.info(f"✅ Motor command executed: {direction} at {speed}%")
                
            except Exception as e:
                emit('motor_feedback', {
                    'success': False,
                    'direction': direction,
                    'error': str(e)
                })
                self.logger.error(f"❌ Motor control error: {e}")
    
    def _get_distance(self) -> Optional[float]:
        """거리 측정"""
        if self.robot_connected and self.robot and self.robot.ultrasonic._is_available:
            try:
                return self.robot.ultrasonic.get_distance()
            except Exception as e:
                self.logger.error(f"❌ Ultrasonic sensor error: {e}")
                return None
        else:
            # 시뮬레이션 모드
            import random
            return round(random.uniform(5.0, 200.0), 1)
    
    def _determine_status(self, distance: float) -> str:
        """거리에 따른 상태 결정"""
        if distance <= self.sensor_config.close_threshold:
            return "close"
        elif distance >= self.sensor_config.far_threshold:
            return "far"
        else:
            return "normal"
    
    def _sensor_measurement_loop(self):
        """초음파 센서 측정 루프"""
        while not self._sensor_stop_event.is_set():
            try:
                distance = self._get_distance()
                if distance is not None:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    status = self._determine_status(distance)
                    
                    reading = SensorReading(
                        distance=distance,
                        timestamp=timestamp,
                        status=status
                    )
                    
                    with self._data_lock:
                        self._sensor_readings.append(reading)
                        if len(self._sensor_readings) > self.sensor_config.max_data_points:
                            self._sensor_readings.pop(0)
                    
                    # Socket.IO로 실시간 데이터 전송
                    self.socketio.emit('ultrasonic_data', asdict(reading))
                
                time.sleep(self.sensor_config.interval)
                
            except Exception as e:
                self.logger.error(f"❌ Sensor measurement error: {e}")
                time.sleep(1)
    
    def _start_sensor_measurement(self) -> bool:
        """초음파 센서 측정 시작"""
        if self._sensor_running:
            return True
        
        try:
            self._sensor_stop_event.clear()
            self._sensor_thread = threading.Thread(target=self._sensor_measurement_loop, daemon=True)
            self._sensor_thread.start()
            self._sensor_running = True
            self.logger.info("📡 Ultrasonic sensor measurement started")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to start sensor measurement: {e}")
            return False
    
    def _stop_sensor_measurement(self) -> bool:
        """초음파 센서 측정 중지"""
        if not self._sensor_running:
            return True
        
        try:
            self._sensor_stop_event.set()
            if self._sensor_thread and self._sensor_thread.is_alive():
                self._sensor_thread.join(timeout=2)
            self._sensor_running = False
            self.logger.info("📡 Ultrasonic sensor measurement stopped")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to stop sensor measurement: {e}")
            return False
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """애플리케이션 실행"""
        self.logger.info("🚀 Integrated Findee Dashboard Starting...")
        self.logger.info("🔧 Server starting on all network interfaces...")
        
        if self.robot_connected:
            self.logger.info(f"📡 Server will be available at: http://{self.robot.get_hostname()}:{port}")
            status = self.robot.get_status()
            self.logger.info(f"🤖 Robot status - Motor: {status.get('motor', False)}, Camera: {status.get('camera', False)}, Ultrasonic: {status.get('ultrasonic', False)}")
        else:
            self.logger.info(f"📡 Server will be available at: http://localhost:{port}")
        
        self.logger.info("🌐 Socket.IO for real-time control, MJPEG for camera streaming")
        self.logger.info("=" * 60)
        
        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Server shutdown requested...")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """정리 작업"""
        self.logger.info("🧹 Cleaning up...")
        
        # 센서 측정 중지
        self._stop_sensor_measurement()
        
        # 로봇 정리
        if self.robot_connected and self.robot:
            try:
                self.robot.cleanup()
                self.logger.info("✅ Robot cleanup completed")
            except Exception as e:
                self.logger.error(f"❌ Error during cleanup: {e}")
        
        self.logger.info("✅ Cleanup completed")

# 애플리케이션 인스턴스 생성
integrated_app = IntegratedFindeeFlask()

if __name__ == '__main__':
    integrated_app.run()
