from findee import Findee, crop_image, image_to_ascii
import time

robot = Findee()

print("카메라 테스트 시작!")
time.sleep(1)

while True:
    frame = robot.camera.get_frame()
    cropped_frame = crop_image(frame, 0.5)
    ascii_image = image_to_ascii(cropped_frame, 100, 10, False)
    print(ascii_image)
    time.sleep(1)