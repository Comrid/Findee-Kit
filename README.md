# Findee-Kit 🚗🛠️

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Zero%202%20W-red.svg)](https://www.raspberrypi.org/)

**Findee-Kit**은 [Findee](https://github.com/Comrid/findee) 라이브러리를 기반으로 한 확장된 로보틱스 개발 툴킷입니다. Flask 웹 인터페이스, 통합 테스트 환경, 그리고 실시간 제어 시스템을 제공하여 자율주행 차량 프로젝트를 더욱 쉽게 개발하고 테스트할 수 있습니다.

## ✨ 주요 기능

- 🌐 **Flask 웹 인터페이스**: 실시간 차량 제어 및 모니터링
- 🧪 **통합 테스트 환경**: 모터, 카메라, 센서 개별 및 통합 테스트
- 📊 **실시간 데이터 스트리밍**: 웹 브라우저에서 센서 데이터 및 영상 확인
- 🔧 **모듈화된 구조**: 각 하드웨어 컴포넌트별 독립적인 테스트 및 개발
- 🎯 **통합 플랫폼**: Findee 라이브러리와 완벽 호환

## 🏗️ 프로젝트 구조

```
Findee-Kit/
├── findee/                     # 핵심 Findee 라이브러리
├── 0.Component_Test/           # 개별 컴포넌트 테스트
│   ├── camera_test.py          # 카메라 테스트
│   ├── motor_test.py           # 모터 테스트
│   └── sonic_test.py           # 초음파 센서 테스트
├── 1.Flask_Test/               # Flask 웹 인터페이스
│   ├── A_Motor_Flask/          # 모터 웹 제어
│   ├── B_Camera_Flask/         # 카메라 웹 스트리밍
│   └── C_Ultrasonic_Flask/     # 센서 웹 모니터링
└── LICENSE                     # MIT 라이선스
```

## 🔧 하드웨어 요구사항

### 기본 하드웨어 (Findee 호환)
- **라즈베리파이 제로 2 W**
- **라즈베리파이 카메라 모듈 V2** 또는 호환 카메라
- **DC 모터 2개** (바퀴용)
- **L298N 모터 드라이버**
- **HC-SR04 초음파 센서**
- **점퍼 와이어** 및 **브레드보드**

### 추가 요구사항 (웹 인터페이스용)
- **Wi-Fi 연결** (웹 인터페이스 접근용)
- **충분한 전원 공급** (5V 2A 이상 권장)

## 📦 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/Comrid/Findee-Kit.git
cd Findee-Kit
```

### 2. Findee 라이브러리 설치
```bash
pip install findee
```

### 3. 필수 라이브러리 설치
```bash
pip install flask opencv-python RPi.GPIO picamera2
pip install flask-socketio eventlet
```

### 4. 권한 설정 (라즈베리파이에서)
```bash
sudo usermod -a -G gpio,spi,i2c pi
```

## 🚀 사용법

### 1. 개별 컴포넌트 테스트

#### 모터 테스트
```bash
cd 0.Component_Test
python motor_test.py
```

#### 카메라 테스트
```bash
python camera_test.py
```

#### 초음파 센서 테스트
```bash
python sonic_test.py
```

### 2. Flask 웹 인터페이스 사용

#### 모터 웹 제어
```bash
cd 1.Flask_Test/A_Motor_Flask
python app.py
```
브라우저에서 `http://라즈베리파이IP:5000` 접속

#### 카메라 웹 스트리밍
```bash
cd 1.Flask_Test/B_Camera_Flask
python app.py
```
브라우저에서 실시간 영상 스트리밍 확인

#### 센서 웹 모니터링
```bash
cd 1.Flask_Test/C_Ultrasonic_Flask
python app.py
```
실시간 거리 센서 데이터 모니터링

### 3. 통합 테스트 시스템
```bash
cd tests
python flask_camera_test.py
```

## 🌐 웹 인터페이스 기능

### 모터 제어 패널
- **방향 제어**: 전진, 후진, 좌회전, 우회전
- **속도 조절**: 실시간 속도 슬라이더
- **긴급 정지**: 즉시 모터 정지 버튼

### 카메라 스트리밍
- **실시간 영상**: 웹 브라우저에서 실시간 영상 확인
- **해상도 조절**: 다양한 해상도 설정
- **캡처 기능**: 특정 순간 이미지 저장

### 센서 모니터링
- **실시간 거리 표시**: 그래프 및 숫자로 표시
- **알림 시스템**: 임계값 설정 및 경고 알림
- **데이터 로깅**: 센서 데이터 CSV 저장

## 🧪 테스트 가이드

### 단계별 테스트 프로세스

1. **개별 컴포넌트 테스트**
   ```bash
   # 각 하드웨어가 정상 작동하는지 확인
   python 0.Component_Test/motor_test.py
   python 0.Component_Test/camera_test.py
   python 0.Component_Test/sonic_test.py
   ```

2. **Flask 웹 인터페이스 테스트**
   ```bash
   # 웹 인터페이스를 통한 제어 확인
   cd 1.Flask_Test/A_Motor_Flask && python app.py
   ```

3. **통합 테스트**
   ```bash
   # 모든 컴포넌트가 함께 작동하는지 확인
   cd tests && python flask_camera_test.py
   ```

## 📖 API 문서

### Findee 라이브러리 API
Findee-Kit은 기본적으로 [Findee 라이브러리](https://github.com/Comrid/findee)의 모든 API를 지원합니다.

```python
from findee import Findee

# Findee 객체 생성
robot = Findee()

# 기본 제어
robot.motor.move_forward(50)    # 전진
robot.motor.turn_right(30)      # 우회전
robot.motor.stop()              # 정지

# 센서 데이터
distance = robot.ultrasonic.get_distance()
frame = robot.camera.get_frame()
```

## 🛠️ 트러블슈팅

### 일반적인 문제

#### 카메라 연결 오류
```bash
# 카메라 모듈이 활성화되었는지 확인
sudo raspi-config
# Interface Options > Camera > Enable
```

#### GPIO 권한 오류
```bash
# 사용자를 gpio 그룹에 추가
sudo usermod -a -G gpio $USER
```

#### Flask 앱 외부 접근 불가
```python
# app.py에서 host 설정 확인
app.run(host='0.0.0.0', port=5000, debug=True)
```

### 성능 최적화

#### 메모리 사용량 최적화
```python
# 카메라 해상도 조절
camera_config = {
    'width': 640,
    'height': 480,
    'framerate': 30
}
```

#### CPU 사용량 모니터링
```bash
htop  # 실시간 시스템 리소스 모니터링
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원 및 문의

### 이슈 리포트
버그나 기능 요청은 [GitHub Issues](https://github.com/Comrid/Findee-Kit/issues)를 이용해주세요.

### 관련 프로젝트
- **Findee Library**: [https://github.com/Comrid/findee](https://github.com/Comrid/findee)
- **PyPI Package**: [https://pypi.org/project/findee/](https://pypi.org/project/findee/)

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👥 제작자

- **Pathfinder** - *초기 개발* - [Comrid](https://github.com/Comrid)

## 🎯 로드맵

### v1.1.0 (예정)
- [ ] 모바일 친화적 웹 인터페이스
- [ ] 실시간 데이터 차트 및 분석
- [ ] 자동화된 경로 계획 기능

### v1.2.0 (예정)
- [ ] 머신러닝 기반 객체 인식
- [ ] 클라우드 데이터 저장
- [ ] 다중 로봇 제어 시스템

## 🙏 감사의 말

- 라즈베리파이 재단의 훌륭한 하드웨어
- Flask 커뮤니티의 지원
- 오픈소스 커뮤니티의 기여

---

**즐거운 로보틱스 개발 되세요!** 🚀🛠️