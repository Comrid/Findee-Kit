"""
Findee Ultrasonic Flask Web Application

초음파 센서 모니터링 전용 웹 애플리케이션
- Flask를 사용한 실시간 거리 측정 대시보드
- RESTful API를 통한 센서 제어 및 데이터 관리
- Findee 모듈을 통한 하드웨어 제어
"""

from dataclasses import dataclass
import os
import sys
import logging
import threading
import time
from datetime import datetime
from typing import Optional, List
from findee import Findee, FindeeFormatter

from flask import Flask, render_template, request, jsonify
from pydantic import BaseModel


@dataclass
class FlaskMessage:
    robot_init_start: str = "로봇 초기화 시작"
    robot_init_success: str = "로봇 초기화 성공"
    robot_init_failure: str = "로봇 초기화 실패: {error}"


@dataclass
class SensorReading:
    """센서 읽기 데이터 클래스"""
    distance: float
    timestamp: str
    status: str


class Config:
    SECRET_KEY = 'Pathfinder-Findee'
    PORT = 5000
    DEFAULT_INTERVAL = 1.0
    DEFAULT_CLOSE_THRESHOLD = 10.0
    DEFAULT_FAR_THRESHOLD = 100.0
    MAX_DATA_POINTS = 50
    UPDATE_INTERVAL = 1  # 실시간 업데이트 주기 (초)

#-Findee Logger Initialization-#
logger = FindeeFormatter().get_logger()
FindeeFormatter.disable_flask_logger()


#-Findee Robot Initialization-#
logger.info(FlaskMessage.robot_init_start)
robot = Findee(safe_mode=True)

robot_status = robot.get_status()

if robot_status['ultrasonic_status']:
    robot.ultrasonic.start_distance_measurement(interval=Config.DEFAULT_INTERVAL)

robot_connected = True
logger.info(FlaskMessage.robot_init_success)


# 실시간 업데이트를 위한 전역 변수
update_thread = None
update_running = False

# 센서 설정 및 데이터 저장
sensor_config = {
    'interval': Config.DEFAULT_INTERVAL,
    'close_threshold': Config.DEFAULT_CLOSE_THRESHOLD,
    'far_threshold': Config.DEFAULT_FAR_THRESHOLD
}

sensor_readings: List[SensorReading] = []
data_lock = threading.Lock()
is_measuring = False


class Info(BaseModel):
    connected: bool = robot_connected
    running: bool = robot_connected
    motor_status: bool = robot_status['motor_status']
    camera_status: bool = robot_status['camera_status']
    ultrasonic_status: bool = robot_status['ultrasonic_status']
    is_measuring: bool = False
    data_count: int = 0

def get_info_data() -> dict:
    if not robot_connected or not robot:
        return Info(
            connected=False,
            running=False,
            motor_status=False,
            camera_status=False,
            ultrasonic_status=False,
            is_measuring=False,
            data_count=0
        ).model_dump()

    current_status = robot.get_status()
    with data_lock:
        data_count = len(sensor_readings)

    return Info(
        connected=robot_connected,
        running=robot_connected,
        motor_status=current_status['motor_status'],
        camera_status=current_status['camera_status'],
        ultrasonic_status=current_status['ultrasonic_status'],
        is_measuring=is_measuring,
        data_count=data_count
    ).model_dump()


def determine_status(distance: float) -> str:
    """거리에 따른 상태 결정"""
    if distance < sensor_config['close_threshold']:
        return 'close'
    elif distance > sensor_config['far_threshold']:
        return 'far'
    else:
        return 'normal'


def measurement_loop():
    """측정 루프 (별도 스레드에서 실행)"""
    global is_measuring, sensor_readings

    logger.info("📏 초음파 센서 측정 루프 시작")

    while is_measuring:
        try:
            if robot_connected and robot and robot_status['ultrasonic_status']:
                distance = robot.ultrasonic.get_distance()

                if distance is not None:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    status = determine_status(distance)

                    reading = SensorReading(
                        distance=distance,
                        timestamp=timestamp,
                        status=status
                    )

                    with data_lock:
                        sensor_readings.append(reading)

                        # 최대 데이터 포인트 수 제한
                        if len(sensor_readings) > Config.MAX_DATA_POINTS:
                            sensor_readings.pop(0)

                    logger.debug(f"📏 측정값: {distance:.1f}cm, 상태: {status}")

            # 설정된 간격만큼 대기
            time.sleep(sensor_config['interval'])

        except Exception as e:
            logger.error(f"❌ 측정 루프 중 오류: {e}")
            time.sleep(1.0)  # 오류 시 1초 대기

    logger.info("📏 초음파 센서 측정 루프 종료")


def start_measurement() -> bool:
    """측정 시작"""
    global is_measuring

    if is_measuring:
        logger.warning("⚠️ 이미 측정이 진행 중입니다.")
        return False

    try:
        is_measuring = True
        measurement_thread = threading.Thread(target=measurement_loop, daemon=True)
        measurement_thread.start()
        logger.info("✅ 초음파 센서 측정이 시작되었습니다.")
        return True
    except Exception as e:
        logger.error(f"❌ 측정 시작 실패: {e}")
        is_measuring = False
        return False


def stop_measurement() -> bool:
    """측정 중지"""
    global is_measuring

    if not is_measuring:
        logger.warning("⚠️ 측정이 진행되지 않고 있습니다.")
        return False

    try:
        is_measuring = False
        logger.info("🛑 초음파 센서 측정이 중지되었습니다.")
        return True
    except Exception as e:
        logger.error(f"❌ 측정 중지 실패: {e}")
        return False


def clear_data() -> None:
    """저장된 데이터 초기화"""
    global sensor_readings

    with data_lock:
        sensor_readings.clear()
    logger.info("🗑️ 센서 데이터가 초기화되었습니다.")


# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY


@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def api_start_measurement():
    """측정 시작 API"""
    try:
        success = start_measurement()
        return jsonify({
            'success': success,
            'message': '측정이 시작되었습니다.' if success else '측정 시작에 실패했습니다.',
            'is_running': is_measuring
        })
    except Exception as e:
        logger.error(f"❌ 측정 시작 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}',
            'is_running': False
        }), 500


@app.route('/api/stop', methods=['POST'])
def api_stop_measurement():
    """측정 중지 API"""
    try:
        success = stop_measurement()
        return jsonify({
            'success': success,
            'message': '측정이 중지되었습니다.' if success else '측정 중지에 실패했습니다.',
            'is_running': is_measuring
        })
    except Exception as e:
        logger.error(f"❌ 측정 중지 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}',
            'is_running': is_measuring
        }), 500


@app.route('/api/clear', methods=['POST'])
def api_clear_data():
    """데이터 초기화 API"""
    try:
        clear_data()
        return jsonify({
            'success': True,
            'message': '데이터가 초기화되었습니다.',
            'data_count': 0
        })
    except Exception as e:
        logger.error(f"❌ 데이터 초기화 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/data')
def api_get_data():
    """실시간 데이터 조회 API - 최신 데이터만 전송"""
    try:
        with data_lock:
            # 최신 데이터만 전송 (성능 최적화)
            latest_data = None
            if sensor_readings:
                latest = sensor_readings[-1]
                latest_data = {
                    'distance': latest.distance,
                    'timestamp': latest.timestamp,
                    'status': latest.status
                }
        
        return jsonify({
            'success': True,
            'data': latest_data,  # 최신 1개만
            'count': len(sensor_readings),
            'is_running': is_measuring,
            'config': sensor_config
        })
    except Exception as e:
        logger.error(f"❌ 데이터 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/data/all')
def api_get_all_data():
    """전체 데이터 조회 API - 초기 로드 시에만 사용"""
    try:
        with data_lock:
            data = [
                {
                    'distance': reading.distance,
                    'timestamp': reading.timestamp,
                    'status': reading.status
                }
                for reading in sensor_readings
            ]
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'is_running': is_measuring,
            'config': sensor_config
        })
    except Exception as e:
        logger.error(f"❌ 전체 데이터 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/latest')
def api_get_latest():
    """최신 측정값 조회 API"""
    try:
        with data_lock:
            latest = sensor_readings[-1] if sensor_readings else None

        if latest:
            return jsonify({
                'success': True,
                'data': {
                    'distance': latest.distance,
                    'timestamp': latest.timestamp,
                    'status': latest.status
                },
                'is_running': is_measuring
            })
        else:
            return jsonify({
                'success': False,
                'message': '측정 데이터가 없습니다.',
                'is_running': is_measuring
            })
    except Exception as e:
        logger.error(f"❌ 최신 데이터 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/config', methods=['GET', 'POST'])
def api_handle_config():
    """설정 조회/변경 API"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': sensor_config
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
            sensor_config['interval'] = float(data['interval'])
        if 'close_threshold' in data:
            sensor_config['close_threshold'] = float(data['close_threshold'])
        if 'far_threshold' in data:
            sensor_config['far_threshold'] = float(data['far_threshold'])

        # 측정 중인 경우 재시작
        if is_measuring:
            stop_measurement()
            time.sleep(0.1)
            start_measurement()

        return jsonify({
            'success': True,
            'message': '설정이 업데이트되었습니다.',
            'config': sensor_config
        })
    except Exception as e:
        logger.error(f"❌ 설정 변경 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/api/status')
def api_get_status():
    """시스템 상태 조회 API"""
    try:
        sensor_mode = 'simulation' if not robot_status['ultrasonic_status'] else 'hardware'

        return jsonify({
            'success': True,
            'system': {
                'is_running': is_measuring,
                'sensor_mode': sensor_mode,
                'data_count': len(sensor_readings),
                'findee_status': robot.get_status() if robot_connected else {}
            },
            'config': sensor_config
        })
    except Exception as e:
        logger.error(f"❌ 상태 조회 중 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500


def run_server():
    address = robot.get_hostname() if robot_connected else "localhost"
    logger.info(f"📡 Ultrasonic server available at: http://{address}:{Config.PORT}")
    logger.info("=" * 60)

    try:
        app.run(host='0.0.0.0', port=Config.PORT, debug=True, threaded=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server shutdown requested...")
    finally:
        if robot_connected and robot:
            robot.cleanup()


if __name__ == '__main__':
    run_server()
