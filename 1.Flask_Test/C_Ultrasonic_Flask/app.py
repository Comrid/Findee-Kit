#!/usr/bin/env python3
"""
Flask 초음파 센서 대시보드 애플리케이션

이 모듈은 Findee 초음파 센서를 사용하여 실시간 거리 측정 대시보드를 제공합니다.
FindeeUltrasonicFlask 클래스를 통해 재사용 가능한 구조로 설계되었습니다.
"""

from __future__ import annotations
import sys
import os
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from flask import Flask, render_template, jsonify, request

# Findee 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../findee'))

try:
    from findee.findee import Findee
except ImportError as e:
    print(f"Findee 모듈을 가져올 수 없습니다: {e}")
    print("Windows 환경에서는 시뮬레이션 모드로 동작합니다.")
    Findee = None


@dataclass
class SensorReading:
    """센서 읽기 데이터 클래스"""
    distance: float
    timestamp: str
    status: str


@dataclass
class SensorConfig:
    """센서 설정 데이터 클래스"""
    interval: float = 1.0
    close_threshold: float = 10.0
    far_threshold: float = 100.0
    max_data_points: int = 50
    moving_average_window: int = 5


class FindeeUltrasonicFlask:
    """
    Findee 초음파 센서와 Flask 웹 서버를 통합한 클래스
    
    재사용 가능하고 확장 가능한 구조로 설계되었으며,
    실시간 거리 측정 및 웹 대시보드 기능을 제공합니다.
    """
    
    def __init__(self, app: Optional[Flask] = None, config: Optional[SensorConfig] = None):
        """
        FindeeUltrasonicFlask 초기화
        
        Args:
            app: Flask 애플리케이션 인스턴스 (None인 경우 새로 생성)
            config: 센서 설정 (None인 경우 기본값 사용)
        """
        self.app = app or Flask(__name__)
        self.config = config or SensorConfig()
        
        # 로깅 설정 (가장 먼저)
        self._setup_logging()
        
        # 상태 관리
        self._is_running: bool = False
        self._measurement_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 데이터 저장
        self._readings: List[SensorReading] = []
        self._data_lock = threading.Lock()
        
        # Findee 인스턴스
        self._findee: Optional[Findee] = None
        self._is_simulation_mode: bool = False
        
        # Flask 설정
        self._setup_flask()
        self._register_routes()
        self._initialize_sensor()
    
    def _setup_flask(self) -> None:
        """Flask 애플리케이션 설정"""
        self.app.config.update({
            'SECRET_KEY': 'ultrasonic-sensor-dashboard',
            'JSON_AS_ASCII': False,
            'JSONIFY_PRETTYPRINT_REGULAR': True
        })
    
    def _setup_logging(self) -> None:
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_sensor(self) -> None:
        """센서 초기화"""
        try:
            if Findee is not None:
                self._findee = Findee(safe_mode=True)
                if self._findee.get_status().get('ultrasonic', False):
                    self.logger.info("초음파 센서 초기화 성공")
                else:
                    self.logger.warning("초음파 센서를 사용할 수 없습니다. 시뮬레이션 모드로 전환합니다.")
                    self._is_simulation_mode = True
            else:
                self.logger.info("Findee 모듈을 사용할 수 없습니다. 시뮬레이션 모드로 동작합니다.")
                self._is_simulation_mode = True
        except Exception as e:
            self.logger.error(f"센서 초기화 실패: {e}")
            self._is_simulation_mode = True
    
    def _register_routes(self) -> None:
        """Flask 라우트 등록"""
        
        @self.app.route('/')
        def index():
            """메인 대시보드 페이지"""
            return render_template('index.html')
        
        @self.app.route('/api/start', methods=['POST'])
        def start_measurement():
            """측정 시작 API"""
            try:
                success = self.start_measurement()
                return jsonify({
                    'success': success,
                    'message': '측정이 시작되었습니다.' if success else '측정 시작에 실패했습니다.',
                    'is_running': self._is_running
                })
            except Exception as e:
                self.logger.error(f"측정 시작 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}',
                    'is_running': False
                }), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def stop_measurement():
            """측정 중지 API"""
            try:
                success = self.stop_measurement()
                return jsonify({
                    'success': success,
                    'message': '측정이 중지되었습니다.' if success else '측정 중지에 실패했습니다.',
                    'is_running': self._is_running
                })
            except Exception as e:
                self.logger.error(f"측정 중지 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}',
                    'is_running': self._is_running
                }), 500
        
        @self.app.route('/api/clear', methods=['POST'])
        def clear_data():
            """데이터 초기화 API"""
            try:
                self.clear_data()
                return jsonify({
                    'success': True,
                    'message': '데이터가 초기화되었습니다.',
                    'data_count': 0
                })
            except Exception as e:
                self.logger.error(f"데이터 초기화 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/data')
        def get_data():
            """실시간 데이터 조회 API"""
            try:
                with self._data_lock:
                    data = [asdict(reading) for reading in self._readings]
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'is_running': self._is_running,
                    'config': asdict(self.config)
                })
            except Exception as e:
                self.logger.error(f"데이터 조회 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/latest')
        def get_latest():
            """최신 측정값 조회 API"""
            try:
                with self._data_lock:
                    latest = self._readings[-1] if self._readings else None
                
                if latest:
                    return jsonify({
                        'success': True,
                        'data': asdict(latest),
                        'is_running': self._is_running
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '측정 데이터가 없습니다.',
                        'is_running': self._is_running
                    })
            except Exception as e:
                self.logger.error(f"최신 데이터 조회 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def handle_config():
            """설정 조회/변경 API"""
            if request.method == 'GET':
                return jsonify({
                    'success': True,
                    'config': asdict(self.config)
                })
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'message': '요청 데이터가 없습니다.'
                    }), 400
                
                # 설정 업데이트
                if 'interval' in data:
                    self.config.interval = float(data['interval'])
                if 'close_threshold' in data:
                    self.config.close_threshold = float(data['close_threshold'])
                if 'far_threshold' in data:
                    self.config.far_threshold = float(data['far_threshold'])
                
                # 측정 중인 경우 재시작
                if self._is_running:
                    self.stop_measurement()
                    time.sleep(0.1)
                    self.start_measurement()
                
                return jsonify({
                    'success': True,
                    'message': '설정이 업데이트되었습니다.',
                    'config': asdict(self.config)
                })
            except Exception as e:
                self.logger.error(f"설정 변경 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
        
        @self.app.route('/api/status')
        def get_status():
            """시스템 상태 조회 API"""
            try:
                sensor_status = 'simulation' if self._is_simulation_mode else 'hardware'
                if self._findee:
                    findee_status = self._findee.get_status()
                else:
                    findee_status = {}
                
                return jsonify({
                    'success': True,
                    'system': {
                        'is_running': self._is_running,
                        'sensor_mode': sensor_status,
                        'data_count': len(self._readings),
                        'findee_status': findee_status
                    },
                    'config': asdict(self.config)
                })
            except Exception as e:
                self.logger.error(f"상태 조회 중 오류: {e}")
                return jsonify({
                    'success': False,
                    'message': f'오류가 발생했습니다: {str(e)}'
                }), 500
    
    def _get_distance(self) -> Optional[float]:
        """거리 측정 (실제 센서 또는 시뮬레이션)"""
        if self._is_simulation_mode:
            # 시뮬레이션 모드: 사인파 기반 가상 데이터 생성
            import math
            base_distance = 50 + math.sin(time.time() / 5) * 40
            noise = (hash(str(time.time())) % 1000 - 500) / 100  # -5 ~ 5 범위의 노이즈
            return max(5, min(300, base_distance + noise))
        else:
            # 실제 센서 모드
            if self._findee and self._findee.ultrasonic._is_available:
                return self._findee.ultrasonic.get_distance()
            return None
    
    def _determine_status(self, distance: float) -> str:
        """거리에 따른 상태 결정"""
        if distance < self.config.close_threshold:
            return 'close'
        elif distance > self.config.far_threshold:
            return 'far'
        else:
            return 'normal'
    
    def _measurement_loop(self) -> None:
        """측정 루프 (별도 스레드에서 실행)"""
        self.logger.info("측정 루프 시작")
        
        while not self._stop_event.is_set():
            try:
                distance = self._get_distance()
                
                if distance is not None:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    status = self._determine_status(distance)
                    
                    reading = SensorReading(
                        distance=distance,
                        timestamp=timestamp,
                        status=status
                    )
                    
                    with self._data_lock:
                        self._readings.append(reading)
                        
                        # 최대 데이터 포인트 수 제한
                        if len(self._readings) > self.config.max_data_points:
                            self._readings.pop(0)
                    
                    self.logger.debug(f"측정값: {distance:.1f}cm, 상태: {status}")
                
                # 설정된 간격만큼 대기
                self._stop_event.wait(self.config.interval)
                
            except Exception as e:
                self.logger.error(f"측정 루프 중 오류: {e}")
                self._stop_event.wait(1.0)  # 오류 시 1초 대기
        
        self.logger.info("측정 루프 종료")
    
    def start_measurement(self) -> bool:
        """측정 시작"""
        if self._is_running:
            self.logger.warning("이미 측정이 진행 중입니다.")
            return False
        
        try:
            self._stop_event.clear()
            self._measurement_thread = threading.Thread(
                target=self._measurement_loop,
                daemon=True
            )
            self._measurement_thread.start()
            self._is_running = True
            self.logger.info("측정이 시작되었습니다.")
            return True
        except Exception as e:
            self.logger.error(f"측정 시작 실패: {e}")
            return False
    
    def stop_measurement(self) -> bool:
        """측정 중지"""
        if not self._is_running:
            self.logger.warning("측정이 진행되지 않고 있습니다.")
            return False
        
        try:
            self._stop_event.set()
            if self._measurement_thread and self._measurement_thread.is_alive():
                self._measurement_thread.join(timeout=2.0)
            
            self._is_running = False
            self.logger.info("측정이 중지되었습니다.")
            return True
        except Exception as e:
            self.logger.error(f"측정 중지 실패: {e}")
            return False
    
    def clear_data(self) -> None:
        """저장된 데이터 초기화"""
        with self._data_lock:
            self._readings.clear()
        self.logger.info("데이터가 초기화되었습니다.")
    
    def get_readings(self) -> List[SensorReading]:
        """현재 저장된 모든 측정값 반환"""
        with self._data_lock:
            return self._readings.copy()
    
    def get_latest_reading(self) -> Optional[SensorReading]:
        """최신 측정값 반환"""
        with self._data_lock:
            return self._readings[-1] if self._readings else None
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
        """Flask 서버 실행"""
        try:
            self.logger.info(f"서버 시작: http://{host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except KeyboardInterrupt:
            self.logger.info("서버 종료 요청")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """리소스 정리"""
        self.logger.info("애플리케이션 정리 시작")
        
        # 측정 중지
        if self._is_running:
            self.stop_measurement()
        
        # Findee 인스턴스 정리
        if self._findee:
            try:
                self._findee.cleanup()
            except Exception as e:
                self.logger.error(f"Findee 정리 중 오류: {e}")
        
        self.logger.info("애플리케이션 정리 완료")


def create_app(config: Optional[SensorConfig] = None) -> Flask:
    """Flask 애플리케이션 팩토리 함수"""
    flask_app = FindeeUltrasonicFlask(config=config)
    return flask_app.app


if __name__ == '__main__':
    # 설정 생성
    sensor_config = SensorConfig(
        interval=1.0,
        close_threshold=10.0,
        far_threshold=100.0,
        max_data_points=50,
        moving_average_window=5
    )
    
    # 애플리케이션 생성 및 실행
    ultrasonic_app = FindeeUltrasonicFlask(config=sensor_config)
    
    try:
        ultrasonic_app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n서버가 중단되었습니다.")
    finally:
        ultrasonic_app.cleanup()
