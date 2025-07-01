from findee import Findee
import time

robot = Findee()

print("전후진 테스트 시작!")
robot.motor.move_forward(100, 1)
robot.motor.move_backward(100, 1)
time.sleep(1)

print("제자리 회전 테스트 시작!")
robot.motor.turn_left(100, 1)
robot.motor.turn_right(100, 1)
time.sleep(1)

print("커브 테스트 시작!")
robot.motor.curve_left(100, 60, 1)
robot.motor.curve_right(100, 60, 1)
time.sleep(1)

print("테스트 완료!")