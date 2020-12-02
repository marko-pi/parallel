
import time
from HD44780 import HD44780

# initialize the chips
lcd=[]
lcd.append(HD44780(40, 2, 5, 6, 13, 19, -1, -1, -1, -1, 16, 20, 12, 18, backlight=0, pwm=True))
lcd.append(HD44780(40, 2, 5, 6, 13, 19, -1, -1, -1, -1, 16, 21, 12, 18, backlight=0, pwm=True))

# times and euro characters (positions 0 and 1)
customchars=[0x00110A040A110000,0x07081E081E080700]
for i in lcd:
    i.definechars(customchars)

# turn on backlight
time.sleep(5)
lcd[0].setbacklight(0.5)

# write the first text
lcd[0].set_cursor(0,0)
lcd[0].text(b'             40 '+chr(0)+' 4 DISPLAY             ')
lcd[0].set_cursor(0,1)
lcd[0].text(b'              HD44780 CHIP              ')
lcd[1].set_cursor(0,0)
lcd[1].text(b'                                        ')
lcd[1].set_cursor(0,1)
lcd[1].text(b'             Raspberry Pi 3             ')

time.sleep(1)

# blinking brightness
time.sleep(2)
for i in range(5):
    time.sleep(0.5)
    lcd[0].setbacklight(0.75)
    time.sleep(0.5)
    lcd[0].setbacklight(0.5)

# write the second text
lcd[0].set_cursor(0,0)
lcd[0].text('      To learn more about using and     ')
lcd[0].set_cursor(0,1)
lcd[0].text('      programming the HD44780 chip      ')
lcd[1].set_cursor(0,0)
lcd[1].text('    in Python at Rasbperry Pi, visit    ')
lcd[1].set_cursor(0,1)
lcd[1].text('  http://www.pinteric.com/displays.html ')
time.sleep(5)

# turn off backlight
lcd[0].setbacklight(0)

# close the chips
for i in lcd:
    i.close()
