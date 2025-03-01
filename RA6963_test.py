#!/usr/bin/env python
"""
    Marko Pinteric 2020

    RA6963 graphic LCD controller test
        - ultra fast parallel communication using C code
        - requires RA6963.py and parallel.so in the same folder
        - data for fast transfer have to be supplied in contiguous block of bytes
        - supports writing and reading, reading is optional

    for more information see: http://www.pinteric.com/displays.html
"""

from RA6963 import RA6963
import time
# used to form large contiguous block of bytes
import numpy
from ctypes import c_void_p

# 240x128 screen, reading disabled (rd=-1), backlight PWM power on GPIO18, backlight off on start
ra = RA6963(240,128,16,20,21,26,19,13,6,5,22,27,17,-1,18,backlight=0,pwm=True)
ra.clearall()

# times character, euro character
customchars=[0x00110A040A110000,0x07081E081E080700]
ra.definechars(customchars)

# display both graphics and text, graphics is used for text attributes (attribute mode)
ra.displaymode(True,True)
ra.modeset(4)

# turn on backlight
ra.setbacklight(1)
time.sleep(5)

# write text
ra.writetext("""
                              
                              
       240   128 DISPLAY      
                              
          RA6963 CHIP         
                              
        Raspberry Pi 3        
                              
 To learn more about using and
 programming the RA 6963 chip 
  in Python at Raspberry Pi,  
             visit            
                              
www.pinteric.com/displays.html
                              
                              
""")

# put a custom character for times between numbers (3rd row, 12th column)
ra.setaddress(ra.textaddress+2*30+11)
ra.writeincrement(128)

# make title bold (5th row, 11th column, 11 characters)
# send one datum a time
ra.setaddress(ra.graphicaddress+4*30+10)
for i in range (11):
    ra.writeincrement(ra.bold)

# make subtitle bold and blinking (7th row, 9th column, 14 characters)
# create contiguous data using string method and send everything in one go 
ra.setaddress(ra.graphicaddress+6*30+8)
temp = bytes([ra.bold | ra.blink]*14)
ra.writedata(temp, 14)

time.sleep(8)

# create contiguous data for the dog picture using numpy method
dogpicture = numpy.array([0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000007FF,0xFFE00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000001,0xFFFFFFF8,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000FFFFF,0xFFFE0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000003F,0xFFFFE07F,0x80000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x007F8003,0xC00FC000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000000FC,0x00038003,0xE0000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x03F00003,0x8001F000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000007E0,0x00038000,0xF8000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000003F,0xFFC00003,0xC0003C00,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x03FFFF00,0x0001E000,0x3C000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000007FF,0xFC000001,0xE0001C00,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0FFFC000,0x0000F000,0x1C000000,0x00000000,0x01FFC000,0x00000000,0x00000000,0x00000F00,0x00000000,0xF0001C00,0x00000000,0x00007FFF,0xFF000000,0x00000000,0x00000000,0x0E000000,0x00007000,0x1E000000,0x00000003,0xFFFFFFF0,0x00000000,0x00000000,0x00000E00,0x00000000,0x78003F80,0x00000000,0x003FFFFF,0xFFFE0000,0x00000000,0x00000000,0x0E000000,0x00007800,0x3FC00000,0x000001FF,0xE00001FF,0x80000000,0x00000000,0x00000E00,0x00000000,0x38003FF0,0x00000000,0x0FFE0000,0x001FE000,0x00000000,0x00000000,0x0E000000,0x00003800,0x79FFFFFF,0xF8007FF0,0x00000003,0xF8000000,0x00000000,0x00000E00,0x00000000,0x3C0078FF,0xFFFFFFFF,0xFF800000,0x0000FC00,0x00000000,0x00000000,0x0E000000,0x00003C00,0x703FFFFF,0xFFFFFC00,0x00000000,0x7F000000,0x00000000,0x00000F00,0x00000000,0x3C00F007,0xF0003FFF,0xE0000000,0x00001F80,0x00000000,0x00000000,0x0F000000,0x00001C01,0xE0000000,0x007E0000,0x00000000,0x0FC00000,0x00000000,0x00000700,0x00000000,0x1E01E000,0x00000000,0x00000000,0x000007F0,0x00000000,0x00000000,0x07800000,0x00001E03,0xC0000000,0x00000000,0x00000000,0x01FE0000,0x00000000,0x000007C0,0x00000000,0x0F07C000,0x00000000,0x00000000,0x000000FF,0xFFFC0000,0x00000000,0x03F00000,0x00000F8F,0x80000000,0x00000000,0x00000000,0x003FFFFF,0x80000000,0x000001FC,0x00000000,0x07FF0000,0x00000000,0x00000000,0x00000007,0xFFFFE000,0x00000000,0x007F8000,0x000003FE,0x00000000,0x00000000,0x00000000,0x00000007,0xF8000000,0x0000003F,0xF0000000,0x01F80000,0x00000000,0x00000000,0x00000000,0x0001FF00,0x00000000,0x0007FE00,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x3FC00000,0x00000001,0xFFC00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000FF0,0x00000000,0x00003FFC,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x03FE0000,0x00000000,0x07FFC000,0x00000000,0x00000000,0x00000000,0x00000000,0x000000FF,0xC0000000,0x000000FF,0xF8000000,0x00000000,0x00000000,0x00000000,0x00000000,0x001FF800,0x00000000,0x000FFF00,0x00000000,0x00000000,0x00000000,0x00000000,0x03FE0007,0xFFE00000,0x00000000,0xFFE00000,0x00000000,0x00000000,0x00000000,0x00003FFF,0xE000FFFF,0xFFC00000,0x00001FFC,0x00000000,0x00000000,0x00000000,0x00000000,0x7FFFF800,0x1FFFFFF0,0x00000000,0x01FF0000,0x00000000,0x00000000,0x00000000,0x0000FF8F,0xFE0000FF,0xFFF00000,0x0000003F,0x80000000,0x00000000,0x00000000,0x00000000,0xF0007FC0,0x000001F0,0x00000000,0x000FC000,0x00000000,0x00000000,0x00000000,0x0000F000,0x1FFC0000,0x01F00000,0x00000003,0xE0000000,0x00000000,0x00000000,0x00000000,0xE00007FF,0xFC007FE0,0x00000000,0x0001F000,0x00000000,0x00000000,0x00000000,0x0000E000,0x00FFFFFF,0xFFC00000,0x00000000,0xF8000000,0x00000000,0x00000000,0x00000000,0xE000000F,0xFFFFFF00,0x00000000,0x00007800,0x00000000,0x00000000,0x00000000,0x0001E000,0x00003FFF,0xF0000000,0x00000000,0x3C000000,0x00000000,0x00000000,0x00000001,0xE0000000,0x00000000,0x00000000,0x00003E00,0x00000000,0x00000000,0x00000000,0x0001E000,0x00000000,0x00000000,0x00000000,0x1E000000,0x00000000,0x00000000,0x00000001,0xE0000000,0x00000000,0x00000000,0x00000F00,0x00000000,0x00000000,0x00000000,0x0001E000,0x00000000,0x00000000,0x00000000,0x0F000000,0x00000000,0x00000000,0x00000001,0xE0000000,0x00000000,0x00000000,0x00000780,0x00000000,0x00000000,0x00000000,0x0001C000,0x00000000,0x00000000,0x00000000,0x03C00000,0x00000000,0x00000000,0x00000001,0xC0000000,0x00000000,0x00000000,0x000003C0,0x00000000,0x00000002,0x00000000,0x0003C000,0x00000000,0x00000000,0x00000000,0x01E00000,0x00000000,0x00070000,0x00000003,0xC0000000,0x00000000,0x00000000,0x000001E0,0x00000000,0x0000000F,0x80000000,0x00078000,0x00000000,0x00000000,0x00000000,0x00F00000,0x00000000,0x000F0000,0x00000007,0x80000000,0x00000000,0x00000000,0x00000078,0x00000000,0x0000001E,0x00000000,0x000F0000,0x00000000,0x00000000,0x00000000,0x00780000,0x00000000,0x001E0000,0x0000001F,0x00000000,0x00000000,0x00000000,0x0000003C,0x00000000,0x0000003C,0x00000000,0x001E0000,0x00000000,0x00000000,0x00000000,0x003E0000,0x00000000,0x003C0000,0x0000003C,0x00000000,0x00000000,0x00000000,0x0000001E,0x00000000,0x00000038,0x00000000,0x00F80000,0x00000000,0x00000000,0x00000000,0x000F0000,0x00000000,0x00380000,0x000001F8,0x00000000,0x00000000,0x00000000,0x0000000F,0x80000000,0x00000078,0x00000000,0x03E00000,0x00000000,0x00000000,0x00000000,0x00078000,0x00000000,0x00780000,0x000007C0,0x00000000,0x00000000,0x00000000,0x00000003,0xC0000000,0x00000078,0x00000000,0x0F800000,0x00000000,0x00000000,0x00000000,0x0003C000,0x00000000,0x00780000,0x00003F00,0x00000000,0x00000000,0x00000000,0x00000001,0xE0000000,0x00000078,0x00000000,0x7E000000,0x00000000,0x00000000,0x00000000,0x0000F000,0x00000000,0x00780000,0x0000F800,0x00000000,0x00000000,0x00000000,0x00000000,0xF8000000,0x00000078,0x00000003,0xF0000000,0x00000000,0x00000000,0x00000000,0x00007C00,0x00000000,0x00780000,0x0007E000,0x00000000,0x00000000,0x00000000,0x00000000,0x3E000000,0x00000078,0x0000001F,0x80000000,0x00000000,0x00000000,0x00000000,0x00001F00,0x00000000,0x00380000,0x003F0000,0x00000000,0x00000000,0x00000000,0x00000000,0x0F800000,0x00000038,0x0000007E,0x00000000,0x00000000,0x00000000,0x00000000,0x000007C0,0x00000000,0x00380000,0x00F80000,0x00000000,0x00000000,0x00000000,0x00000000,0x03E00000,0x0000003C,0x000001F0,0x00000000,0x00000000,0x00000000,0x00000000,0x000001F8,0x00000000,0x003C0000,0x03E00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00FE0000,0x0000001C,0x000003C0,0x00000000,0x00000000,0x00000000,0x00000000,0x0000003F,0xC0000000,0x03DE0000,0x07800000,0x00000000,0x00000000,0x00000000,0x00000000,0x001FF800,0x00000FFE,0x00000780,0x00000000,0x00000000,0x00000000,0x00000000,0x00000007,0xFF000000,0x0FFF0000,0x07000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0001FFE0,0x00000FFF,0x00000700,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0xFFFC0000,0x0F3F8000,0x0F000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000E3FF,0x80000F0F,0x80000F00,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0xF03FE000,0x0783C000,0x0F000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000F00F,0xF8000783,0xC0000700,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x7001FC00,0x03C1E000,0x07000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00007000,0xFF0001E0,0xF0000780,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x7000FF80,0x01E0F000,0x07800000,0x00000000,0x00000000,0x00000000,0x00000000,0x00007800,0xEFC000F0,0x78000380,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x7801E3E0,0x00787800,0x03C00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00007801,0xE1F00078,0x3C0003C0,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x3801C0F8,0x003C1C00,0x03C00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00003803,0xC07C001E,0x3C0003C0,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x3803C03E,0x001E3C00,0x07800000,0x00000000,0x00000000,0x00000000,0x00000000,0x00003803,0x801F000F,0x78000F80,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x3803801F,0x8007F800,0x1F000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00003C07,0x807FC007,0xF0007E00,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x3C0787FF,0xF003E000,0xFC000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00003C07,0xFFF9F807,0xC001F000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x1C07FFE0,0xFC0F8007,0xE0000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00001C01,0xFF003E1F,0x000FC000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x1C000000,0x1FBE003F,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00001E00,0x00003FFC,0x007E0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x1E000003,0xFFF001F8,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00001E00,0x007FFFE0,0x03F00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0F800FFF,0xFFC007E0,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000FFF,0xFFFF0F80,0x1F800000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x07FFFFE0,0x1F003F80,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x000001FF,0xFE007E00,0xFFC00000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x001E0003,0xFC01FBF0,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0007F803,0xF1F80000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000001F,0xE00FC0FC,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x001F001F,0x803E0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000003C,0x007FC01E,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x003C00FF,0xC00F0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000003C,0x03F9C007,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x003C0FE1,0xE0070000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000001F,0x3F81E007,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x001FFF00,0xE0070000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000000F,0xFC00E00F,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0003F000,0xFFFF0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x0000FFFE,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x7FFE0000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000FF0,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000], dtype='>u4')

# display both graphics and text, overlapping pixels deactivated (EXOR mode)
ra.modeset(2)

# send the dog picture to the screen
ra.graphichome()
ra.writedata(dogpicture.ctypes.data_as(c_void_p), 240*128//8)

time.sleep(3)

# display only graphics
ra.displaymode(False,True)

# change backlight brightness
time.sleep(1)
for i in range(4):
    ra.setbacklight(0.5)
    time.sleep(0.25)
    ra.setbacklight(1)
    time.sleep(0.25)

# clear memory after the picture
# create contiguous data of zeros using string method and send everything in one go 
ra.setaddress(ra.graphicaddress + 240*128//8)
temp = bytes([0]*(240*128//8))
ra.writedata(temp, 240*128//8)

# slowly move picture from the screen, by moving graphics area into cleared memory
for i in range(128):
    ra.setgraphichome(ra.graphicaddress +30)
    time.sleep(0.03)

time.sleep(3)

# close the chip
ra.setbacklight(0)
ra.close()
