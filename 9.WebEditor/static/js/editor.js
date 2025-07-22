// Findee Web Code Editor - 메인 파일
// 전역 변수 및 초기화

// 전역 변수
let socket;
let editor;
let currentSpeed = 60;
let isConnected = false;
let activeDirection = null;
let codeRunning = false;
let currentFileName = '';
let ultrasonicRunning = false;
let editorFocused = false; // 에디터 포커스 상태 추가
let currentMotorCommand = '명령 없음'; // 현재 모터 명령 상태 추가

// 키보드 중첩 처리를 위한 변수들 추가
let pressedKeys = new Set();
let keyPressOrder = [];

// 코드 예제
const codeExamples = {
    motor_test: `# 모터 테스트 코드
print("🚗 모터 테스트 시작")

# Findee 로봇 초기화
robot = Findee()
print("로봇 초기화 완료")

# 전진
print("전진 중...")
robot.motor.move_forward(60)
time.sleep(2)

# 정지
print("정지")
robot.motor.stop()
time.sleep(1)

# 좌회전
print("좌회전 중...")
robot.motor.turn_left(50)
time.sleep(1.5)

# 정지
print("정지")
robot.motor.stop()

print("✅ 모터 테스트 완료")`,

    ultrasonic_test: `# 초음파 센서 테스트 코드
print("📏 초음파 센서 테스트 시작")

# Findee 로봇 초기화
robot = Findee()

for i in range(10):
    distance = robot.ultrasonic.get_distance()
    print(f"측정 {i+1}: {distance:.1f} cm")
    time.sleep(0.5)

print("✅ 초음파 센서 테스트 완료")`,

    camera_test: `# 카메라 테스트 코드
print("📹 카메라 테스트 시작")

# Findee 로봇 초기화
robot = Findee()

# 카메라 정보 출력
print(f"현재 해상도: {robot.camera.get_current_resolution()}")
print(f"FPS: {robot.camera.fps}")

# 사용 가능한 해상도 목록
resolutions = robot.camera.get_available_resolutions()
print(f"사용 가능한 해상도: {resolutions}")

print("✅ 카메라 테스트 완료")`,

    autonomous: `# 자율 주행 예제
print("🤖 자율 주행 시작")

# Findee 로봇 초기화
robot = Findee()

try:
    while True:
        # 거리 측정
        distance = robot.ultrasonic.get_distance()
        print(f"현재 거리: {distance:.1f} cm")
        
        if distance < 20:
            # 장애물 감지 - 정지 후 우회전
            print("⚠️ 장애물 감지! 정지 후 우회전")
            robot.motor.stop()
            time.sleep(0.5)
            robot.motor.turn_right(60)
            time.sleep(1)
        else:
            # 전진
            robot.motor.move_forward(50)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("🛑 자율 주행 중지")
    robot.motor.stop()

print("✅ 자율 주행 완료")`,

    infinite_loop: `# 무한루프 예제 (타임아웃으로 중지됨)
print("♾️ 무한루프 예제 시작")

# Findee 로봇 초기화
robot = Findee()

counter = 0
while True:
    counter += 1
    print(f"카운터: {counter}")
    
    if counter % 10 == 0:
        print("10초마다 메시지 출력")
    
    time.sleep(1)

# 이 코드는 30초 후 자동으로 중지됩니다
print("이 메시지는 출력되지 않습니다 (무한루프)")`,

    basic_usage: `# 기본 사용법 예제
print("🔧 Findee 기본 사용법")

# 1. Findee 로봇 초기화 (변수명은 자유롭게 사용 가능)
robot = Findee()
print("✅ 로봇 초기화 완료")

# 2. 로봇 상태 확인
status = robot.get_status()
print(f"모터 상태: {status['motor_status']}")
print(f"카메라 상태: {status['camera_status']}")
print(f"초음파 센서 상태: {status['ultrasonic_status']}")

# 3. 모터 제어
print("모터 테스트...")
robot.motor.move_forward(50)
time.sleep(1)
robot.motor.stop()

# 4. 초음파 센서 사용
distance = robot.ultrasonic.get_distance()
print(f"현재 거리: {distance:.1f} cm")

# 5. 카메라 정보
print(f"카메라 해상도: {robot.camera.get_current_resolution()}")

print("✅ 기본 사용법 테스트 완료")`,

    variable_names: `# 다양한 변수명 사용 예제
print("🎯 다양한 변수명으로 Findee 사용하기")

# 어떤 변수명을 사용해도 됩니다!
a = Findee()
my_robot = Findee()
findee = Findee()
bot = Findee()

print("✅ 4개의 Findee 인스턴스 생성 완료")

# 각각 다른 변수명으로 제어 가능
print("a 변수로 모터 제어...")
a.motor.move_forward(30)
time.sleep(0.5)
a.motor.stop()

print("my_robot 변수로 초음파 센서 사용...")
distance = my_robot.ultrasonic.get_distance()
print(f"my_robot으로 측정한 거리: {distance:.1f} cm")

print("findee 변수로 카메라 정보 확인...")
resolution = findee.camera.get_current_resolution()
print(f"findee 카메라 해상도: {resolution}")

print("bot 변수로 상태 확인...")
status = bot.get_status()
print(f"bot 상태: {status}")

print("✅ 다양한 변수명 테스트 완료")`
};

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeMonacoEditor();
    initializeSocket();
    initializeControls();
    loadFileList();
    loadCameraResolutions(); // 카메라 해상도 목록 로드 추가
    updateTime();
    setInterval(updateTime, 1000);
    
    // 시스템 정보 업데이트 시작
    startSystemInfoUpdates();
}); 