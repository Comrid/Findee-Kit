from findee import Findee
import time

robot = Findee()

print("초음파 센서 테스트 시작!")

for i in range(10):
    distance = robot.ultrasonic.get_distance()
    print(f"측정한 거리: {distance} cm")
    time.sleep(0.1)

print("테스트 완료!")