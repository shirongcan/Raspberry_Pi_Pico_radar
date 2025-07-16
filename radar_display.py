from st7735 import TFT, TFTColor
from machine import SPI, Pin
import math
import time
# 屏幕参数
CENTER_X, CENTER_Y = 80, 127  # 圆心在底边中点
RADIUS = 80
MAX_DIST_CM = 30

# 初始化TFT
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11))
tft = TFT(spi, 13, 12, 14)  # DC=13, RESET=12, CS=14
tft.initr()  # 红色tab，如为蓝色/绿色请改为initb()/initg()
tft.rotation(1)
tft.fill(TFT.BLACK)

# 记录上一次扫描线的角度
_last_angle = None
_active_dots = []  # 存 (x, y, timestamp_ms)

def sample_background(xc, yc, rad_dot=3):
    """在(xc,yc)半径rad_dot范围内采样背景色，返回[(x,y,color),…]"""
    pts = []
    for dx in range(-rad_dot, rad_dot+1):
        for dy in range(-rad_dot, rad_dot+1):
            if dx*dx + dy*dy <= rad_dot*rad_dot:
                x = xc + dx
                y = yc + dy
                # 计算相对极坐标
                dx0 = x - CENTER_X
                dy0 = CENTER_Y - y      # 屏幕y反向
                dist = int(math.sqrt(dx0*dx0 + dy0*dy0) + 0.5)
                ang = math.degrees(math.atan2(dy0, dx0))
                # 判断是否落在背景的“圆弧”或“刻度线上”
                if 0 <= ang <= 180 and dist % 20 == 0:
                    color = TFTColor(0, 255, 0)   # 圆弧
                elif abs((ang % 30)) < 0.5 and dist <= RADIUS:
                    color = TFTColor(0, 255, 0)   # 刻度线
                else:
                    color = TFT.BLACK             # 空白
                pts.append((x, y, color))
    return pts
def draw_radar_bg():
    tft.fill(TFT.BLACK)
    # 画半圆
    for r in range(0, RADIUS+1, 20):
        for deg in range(0, 181, 2):  # 只画半圆
            rad = math.radians(deg)
            x = int(CENTER_X + r * math.cos(rad))
            y = int(CENTER_Y - r * math.sin(rad))  # y轴向上
            tft.pixel((x, y), TFTColor(0, 255, 0))
    # 画刻度线
    for a in range(0, 181, 30):
        rad = math.radians(a)
        x = int(CENTER_X + RADIUS * math.cos(rad))
        y = int(CENTER_Y - RADIUS * math.sin(rad))
        tft.line((CENTER_X, CENTER_Y), (x, y), TFTColor(0, 255, 0))
        
def erase_scan(angle):
    """擦除前一条扫描线，并恢复这条线穿过的背景像素"""
    rad = math.radians(angle)
    x_end = int(CENTER_X + RADIUS * math.cos(rad))
    y_end = int(CENTER_Y - RADIUS * math.sin(rad))
    # 1) 用黑线抹掉
    tft.line((CENTER_X, CENTER_Y), (x_end, y_end), TFT.BLACK)
    # 2) 恢复背景：是刻度线就整线恢复，否则只恢复圆弧上的点
    if angle % 30 == 0:
        # 刻度线
        tft.line((CENTER_X, CENTER_Y), (x_end, y_end), TFTColor(0, 255, 0))
    else:
        # 圆弧(r=0,10,20...RADIUS)
        for r in range(0, RADIUS+1, 20):
            xr = int(CENTER_X + r * math.cos(rad))
            yr = int(CENTER_Y - r * math.sin(rad))
            tft.pixel((xr, yr), TFTColor(0, 255, 0))
            
def erase_expired_dots():
    """把过期（一秒以上）的点区域还原成原背景色"""
    now = time.ticks_ms()
    new_list = []
    for bg_pts, ts in _active_dots:
        if time.ticks_diff(now, ts) > 1000:
            # 还原背景
            for x, y, color in bg_pts:
                tft.pixel((x, y), color)
        else:
            new_list.append((bg_pts, ts))
    _active_dots[:] = new_list



def draw_scan(angle, distance):
    global _last_angle, _active_dots

    # 1. 清理过期的红点，恢复背景
    erase_expired_dots()

    # 2. 擦除上一条扫描线（同前的 erase_scan）
    if _last_angle is not None:
        erase_scan(_last_angle)

    # 3. 画本次扫描线
    rad = math.radians(angle)
    x1 = int(CENTER_X + RADIUS * math.cos(rad))
    y1 = int(CENTER_Y - RADIUS * math.sin(rad))
    tft.line((CENTER_X, CENTER_Y), (x1, y1), TFTColor(255, 255, 0))

    # 4. 如果有障碍物，则先采样背景，再画红点并记录
    if 0 < distance <= MAX_DIST_CM:
        r = int(distance / MAX_DIST_CM * RADIUS)
        xp = int(CENTER_X + r * math.cos(rad))
        yp = int(CENTER_Y - r * math.sin(rad))

        bg_pts = sample_background(xp, yp, rad_dot=3)
        tft.fillcircle((xp, yp), 3, TFTColor(255, 0, 0))
        _active_dots.append((bg_pts, time.ticks_ms()))

    _last_angle = angle