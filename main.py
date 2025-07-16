from machine import Pin, PWM
from time import sleep, sleep_us, ticks_us, ticks_diff
import sys
import radar_display

trig = Pin(2, Pin.OUT)
echo = Pin(3, Pin.IN)

servo = PWM(Pin(15))
servo.freq(50)

MAX_DIST_CM = 30


radar_display.draw_radar_bg()

def measure_distance(timeout_us=30000):  # 最多等 30ms
    trig.low()
    sleep_us(2)
    trig.high()
    sleep_us(10)
    trig.low()

    start_wait = ticks_us()
    while echo.value() == 0:
        if ticks_diff(ticks_us(), start_wait) > timeout_us:
            return -1  # 超时
    start = ticks_us()

    while echo.value() == 1:
        if ticks_diff(ticks_us(), start) > timeout_us:
            return -1
    end = ticks_us()

    duration = ticks_diff(end, start)
    distance = (duration * 0.0343) / 2
    return distance



def set_angle(angle):
    min_us = 500
    max_us = 2500
    us = min_us + (max_us - min_us) * angle / 180
    duty = int(us * 65535 / 20000)
    servo.duty_u16(duty)

while True:
    for angle in range(30, 151, 2):
        set_angle(angle)
        distance = measure_distance()
        if distance <= MAX_DIST_CM:
            print(f"{angle},{distance:.1f}")
        else:
            print(f"{angle},0.0")
        #发给串口
        sleep(0.08)
        radar_display.draw_scan(angle, distance)
    for angle in range(150, 30, -2):
        set_angle(angle)
        distance = measure_distance()
        if distance <= MAX_DIST_CM:
            print(f"{angle},{distance:.1f}")
        else:
            print(f"{angle},0.0")
        sleep(0.08)
        radar_display.draw_scan(angle, distance)

   
