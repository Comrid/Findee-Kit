"""
Findee Camera Flask Web Application

카메라 모니터링 전용 웹 애플리케이션
- Flask를 사용한 카메라 스트리밍
- RESTful API를 통한 시스템 정보 및 카메라 제어
- Findee 모듈을 통한 하드웨어 제어
"""

from dataclasses import dataclass
import os
import sys
import logging
import threading
import time
from findee import Findee, FindeeFormatter

from flask import Flask, render_template, request, Response, jsonify
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
    CAMERA_RESOLUTION = (640, 480)
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
    logger.info("📹 카메라 프레임 캡처 시작됨")

robot_connected = True
logger.info(FlaskMessage.robot_init_success)


class Info(BaseModel):
    connected: bool = robot_connected
    running: bool = robot_connected
    camera_status: bool = robot_status['camera_status']
    motor_status: bool = robot_status['motor_status']
    ultrasonic_status: bool = robot_status['ultrasonic_status']
    camera_fps: int = 0
    current_resolution: str = "N/A"

def get_info_data() -> dict:
    if not robot_connected or not robot:
        return Info(
            connected=False,
            running=False,
            camera_status=False,
            motor_status=False,
            ultrasonic_status=False,
            camera_fps=0,
            current_resolution="N/A"
        ).model_dump()

    current_status = robot.get_status()
    return Info(
        connected=robot_connected,
        running=robot_connected,
        camera_status=current_status['camera_status'],
        motor_status=current_status['motor_status'],
        ultrasonic_status=current_status['ultrasonic_status'],
        camera_fps=int(robot.camera.get_fps()) if current_status['camera_status'] else 0,
        current_resolution=robot.camera.get_current_resolution() if current_status['camera_status'] else "N/A"
    ).model_dump()


# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY


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

        # 추가적인 Findee 상태 정보
        system_info.update({
            'hostname': robot.get_hostname(),
            'camera_fps': robot.camera.get_fps() if current_status['camera_status'] else 0,
            'current_resolution': robot.camera.get_current_resolution() if current_status['camera_status'] else 'N/A',
            'camera_status': current_status['camera_status'],
            'motor_status': current_status['motor_status'],
            'ultrasonic_status': current_status['ultrasonic_status']
        })

        return jsonify(system_info)
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
        return jsonify(resolutions)
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
            'status': 'success',
            'resolution': f"{width}x{height}",
            'message': f'해상도가 {width}x{height}로 변경되었습니다.'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': '해상도 변경 중 오류가 발생했습니다.'
        }), 500


def run_server():
    address = robot.get_hostname() if robot_connected else "localhost"
    logger.info(f"📡 Camera server available at: http://{address}:{Config.PORT}")
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
