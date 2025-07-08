from flask import Flask, render_template, Response, jsonify, request
from findee import Findee, FindeeFormatter


# Findee 인스턴스 생성
robot = Findee(safe_mode=True, camera_resolution=(640, 480))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Pathfinder-Findee'

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """비디오 스트리밍 엔드포인트"""
    if not robot.camera._is_available:
        return "Camera not available", 503

    # findee 모듈의 generate_frames 사용
    return Response(robot.camera.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/system_info')
def api_system_info():
    """시스템 정보 API"""
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
    status = robot.get_status()
    return jsonify({
        'running': True,
        'camera_available': status.get('camera', False),
        'motor_available': status.get('motor', False),
        'ultrasonic_available': status.get('ultrasonic', False),
        'current_resolution': robot.camera.get_current_resolution() if robot.camera._is_available else 'N/A'
    })

@app.route('/api/resolutions')
def api_resolutions():
    """사용 가능한 해상도 목록 API"""
    if not robot.camera._is_available:
        return jsonify({'error': 'Camera not available'}), 503

    resolutions = robot.camera.get_available_resolutions()
    current_resolution = robot.camera.get_current_resolution()

    return jsonify({
        'resolutions': resolutions,
        'current': current_resolution
    })

@app.route('/api/resolution', methods=['POST'])
def api_change_resolution():
    """해상도 변경 API"""
    if not robot.camera._is_available:
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

        # findee 모듈의 configure_resolution 사용
        robot.camera.configure_resolution(width, height)

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

if __name__ == '__main__':
    try:
        # 카메라 프레임 캡처 시작
        if robot.camera._is_available:
            robot.camera.start_frame_capture()
            print("카메라 프레임 캡처 시작됨")

        print(f"Flask 서버 시작 - http://{robot.get_hostname()}:5000")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
    finally:
        robot.cleanup()
