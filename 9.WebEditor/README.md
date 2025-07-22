# Findee Web Code Editor

Findee 로봇을 위한 웹 기반 Python 코드 에디터입니다. 실시간 코드 편집, 실행, 디버깅이 가능하며, 카메라, 모터, 초음파 센서를 직접 제어할 수 있습니다.

## 🚀 주요 기능

### 📝 코드 에디터
- **Monaco Editor** 기반의 고급 코드 에디터
- Python 문법 하이라이팅
- 자동 완성 및 오류 검사
- 실시간 코드 편집

### 🤖 로봇 제어
- **모터 제어**: 9방향 제어 패드 (전진, 후진, 좌회전, 우회전, 대각선 이동)
- **카메라 스트리밍**: 실시간 MJPEG 비디오 피드
- **초음파 센서**: 거리 측정 및 장애물 감지
- **키보드 제어**: 화살표키로 모터 조작

### 💻 코드 실행
- **실시간 실행**: 웹에서 직접 Python 코드 실행
- **무한루프 지원**: 타임아웃으로 안전한 무한루프 실행
- **실시간 출력**: 코드 실행 결과를 실시간으로 확인
- **오류 처리**: 실행 오류 및 예외 처리

### 📁 파일 관리
- **코드 저장/로드**: 작업공간에 Python 파일 저장
- **예제 코드**: 미리 준비된 다양한 예제 코드
- **파일 브라우저**: 저장된 파일 목록 및 관리

### 📊 시스템 모니터링
- **실시간 상태**: CPU, 메모리, 온도, IP 주소
- **하드웨어 상태**: 모터, 카메라, 초음파 센서 연결 상태
- **실행 상태**: 코드 실행 진행 상황

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
python app.py
```

### 3. 웹 브라우저 접속
```
http://localhost:5000
```

## 📖 사용법

### 기본 조작
- **모터 제어**: 방향 패드 버튼 클릭 또는 화살표키 사용
- **속도 조절**: 슬라이더로 20%~100% 속도 설정
- **키보드 단축키**:
  - `↑↓←→`: 기본 방향 제어
  - `Space`: 정지
  - `+/-`: 속도 조절

### 코드 작성 및 실행
1. **코드 작성**: Monaco 에디터에서 Python 코드 작성
2. **실행**: "실행" 버튼 클릭 또는 `Ctrl+Enter`
3. **중지**: "중지" 버튼 클릭으로 실행 중단
4. **출력 확인**: 하단 출력 패널에서 실행 결과 확인

### 파일 관리
- **새 파일**: "새 파일" 버튼으로 빈 파일 생성
- **저장**: "저장" 버튼으로 현재 코드를 파일로 저장
- **로드**: 파일 선택 드롭다운에서 저장된 파일 로드

### 예제 코드
사이드바의 "코드 예제" 패널에서 다양한 예제를 선택할 수 있습니다:
- **모터 테스트**: 기본 모터 동작 테스트
- **초음파 테스트**: 거리 측정 테스트
- **카메라 테스트**: 카메라 정보 및 설정 확인
- **자율 주행**: 장애물 회피 자율 주행 예제
- **무한루프**: 무한루프 실행 예제

## 🔧 사용 가능한 객체

코드에서 다음 객체들을 직접 사용할 수 있습니다:

### `robot`
- 전체 로봇 객체
- `robot.get_status()`: 하드웨어 상태 확인
- `robot.get_system_info()`: 시스템 정보 조회
- `robot.get_hostname()`: 호스트명 조회

### `motor`
- 모터 제어 객체
- `motor.move_forward(speed)`: 전진
- `motor.move_backward(speed)`: 후진
- `motor.turn_left(speed)`: 좌회전
- `motor.turn_right(speed)`: 우회전
- `motor.curve_left(speed, angle)`: 곡선 좌회전
- `motor.curve_right(speed, angle)`: 곡선 우회전
- `motor.stop()`: 정지

### `camera`
- 카메라 제어 객체
- `camera.get_current_resolution()`: 현재 해상도
- `camera.get_available_resolutions()`: 사용 가능한 해상도 목록
- `camera.configure_resolution((width, height))`: 해상도 설정
- `camera.fps`: 현재 FPS

### `ultrasonic`
- 초음파 센서 객체
- `ultrasonic.get_distance()`: 거리 측정 (cm)

### `time`
- Python time 모듈
- `time.sleep(seconds)`: 지연 시간

## 📝 예제 코드

### 기본 모터 테스트
```python
print("🚗 모터 테스트 시작")

# 전진
print("전진 중...")
motor.move_forward(60)
time.sleep(2)

# 정지
print("정지")
motor.stop()
time.sleep(1)

# 좌회전
print("좌회전 중...")
motor.turn_left(50)
time.sleep(1.5)

# 정지
print("정지")
motor.stop()

print("✅ 모터 테스트 완료")
```

### 자율 주행 예제
```python
print("🤖 자율 주행 시작")

try:
    while True:
        # 거리 측정
        distance = ultrasonic.get_distance()
        print(f"현재 거리: {distance:.1f} cm")
        
        if distance < 20:
            # 장애물 감지 - 정지 후 우회전
            print("⚠️ 장애물 감지! 정지 후 우회전")
            motor.stop()
            time.sleep(0.5)
            motor.turn_right(60)
            time.sleep(1)
        else:
            # 전진
            motor.move_forward(50)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("🛑 자율 주행 중지")
    motor.stop()

print("✅ 자율 주행 완료")
```

## ⚙️ 설정

### 타임아웃 설정
- **기본 타임아웃**: 30초
- **무한루프 타임아웃**: 300초
- **최대 코드 길이**: 10,000자

### 카메라 설정
- **기본 해상도**: 640x480
- **스트리밍 품질**: 80%
- **FPS**: 자동 조정

## 🔒 안전 기능

### 코드 실행 안전장치
- **타임아웃**: 무한루프 자동 감지 및 중지
- **모터 정지**: 코드 실행 중지 시 자동 모터 정지
- **연결 해제**: 클라이언트 연결 해제 시 안전 정지
- **오류 처리**: 실행 오류 시 자동 복구

### 하드웨어 보호
- **안전 모드**: 기본적으로 안전 모드로 실행
- **속도 제한**: 최대 100% 속도 제한
- **상태 모니터링**: 실시간 하드웨어 상태 확인

## 🐛 문제 해결

### 일반적인 문제
1. **연결 실패**: Findee 하드웨어 연결 확인
2. **카메라 오류**: 카메라 권한 및 드라이버 확인
3. **모터 응답 없음**: 모터 연결 및 전원 확인
4. **코드 실행 실패**: Python 문법 오류 확인

### 로그 확인
- 서버 콘솔에서 상세한 로그 확인 가능
- 웹 브라우저 개발자 도구에서 클라이언트 로그 확인

## 📁 파일 구조

```
findee_kit/9.WebEditor/
├── app.py                 # Flask 서버 메인 파일
├── requirements.txt       # Python 의존성
├── README.md             # 이 파일
├── templates/
│   └── index.html        # 메인 HTML 템플릿
└── static/
    ├── css/
    │   └── style.css     # 스타일시트
    ├── js/
    │   └── editor.js     # JavaScript 로직
    └── workspace/        # 코드 저장 디렉토리
```

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙏 감사의 말

- **Monaco Editor**: Microsoft의 웹 기반 코드 에디터
- **Flask**: Python 웹 프레임워크
- **Socket.IO**: 실시간 양방향 통신
- **Findee**: 로봇 하드웨어 플랫폼

---

**Findee Web Code Editor**로 로봇 프로그래밍을 시작해보세요! 🚀 