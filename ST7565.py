#!/usr/bin/env python
"""
    Marko Pinteric 2021

    ST7565 graphic LCD controller
        - fast SPI communication using C code
        - requires spi.so in the same folder
        - data for fast transfer have to be supplied in contiguous block of bytes
        - controls backlight, PWM uses dtoverlay method

    PWM dtoverlay mathod
        - put "dtoverlay=pwm,pin=<pin>,func=<func>" to "/boot/config.txt"

        GPIO pin    PWM chan    func        comment
        12          0           4 (ALT0)
        13          1           4 (ALT0)
        18          0           2 (ALT5)    works on all Raspberry Pis
        19          1           2 (ALT5)

    for more information see: http://www.pinteric.com/displays.html
"""

import os, numpy, time
from ctypes import cdll, c_int, c_uint, c_uint32, c_ubyte, c_void_p

##### WRAPPING C LIBRARY (local directory or shared) #####
try:
    parallel = cdll.LoadLibrary("./spi.so")
except OSError:
    try:
        parallel = cdll.LoadLibrary("libspi.so")
    except OSError:
        print('Library \'spi\' not available.  Execute \'make\' or \'make install\'.')
        exit()

"""
gpioInitialise()

Initialise GPIO bus.
"""
gpioInitialise =  spi.gpioInitialise

"""
gpioSetMode(gpio, mode)

Set the GPIO mode.
"""
PI_OUTPUT = 1
PI_ALT0 = 4
PI_ALT5 = 2
gpioSetMode = spi.gpioSetMode
gpioSetMode.argtypes = [c_uint, c_uint]

"""
gpioWrite(gpio, level)

Write to GPIO.
"""
gpioWrite = spi.gpioWrite
gpioWrite.argtypes = [c_uint, c_uint]

"""
spiInitialise()

Initialise SPI bus.
"""
spiInitialise = spi.spiInitialise
spiInitialise.argtypes = [c_int, c_uint32]

"""
spiWrite()

Write to SPI.
"""
spiWrite = spi.spiWrite
spiWrite.argtypes = [c_void_p, c_int]

# PWM constants
PWMPATH = '/sys/class/pwm/pwmchip0'
PWMPER = 100000 # period in nanoseconds, 10kHz

##### ST7565 CONSTANTS #####

LCD_DISPLAYON             = 0xAE
LCD_SETDISPLAYSTARTLINE   = 0x40
LCD_SETPAGEADDRESS        = 0xB0
LCD_SETCOLUMNADDRESSUPPER = 0x10
LCD_SETCOLUMNADDRESSLOWER = 0x00
LCD_ADCREVERSE            = 0xA0
LCD_DISPLAYREVERSE        = 0xA6
LCD_DISPLAYALLPOINTS      = 0xA4
LCD_SETLCDBIAS            = 0xA2
LCD_READMODIFYWRITESTART  = 0xE0
LCD_READMODIFYWRITESTOP   = 0xEE
LCD_RESET                 = 0xE2
LCD_COMMONOUTPUTREVERSE   = 0xC0
LCD_SETPOWERCONTROL       = 0x28
LCD_SETRESISTORRATIO      = 0x20
LCD_SETELECTRONICVOLUME   = 0x81
LCD_STATICINDICATORON     = 0xAC
# LCD_SETBOOSTERRATIO       = 0xF8

##### VARIABLE WIDTH FONT #####

ASCII = {
' ': numpy.array([0x00,0x00,0x00], dtype = 'uint8'),
'!': numpy.array([0xFA], dtype = 'uint8'),
'"': numpy.array([0xC0,0x00,0xC0], dtype = 'uint8'),
'#': numpy.array([0x58,0x70,0xD8,0x70,0xD0], dtype = 'uint8'),
'$': numpy.array([0x64,0x92,0xFF,0x92,0x4C], dtype = 'uint8'),
'%': numpy.array([0x60,0x96,0xF8,0x3C,0xD2,0x0C], dtype = 'uint8'),
'&': numpy.array([0x0C,0x52,0xA2,0x52,0x0C,0x12], dtype = 'uint8'),
'\'': numpy.array([0xC0], dtype = 'uint8'),
'(': numpy.array([0x3C,0x42,0x81], dtype = 'uint8'),
')': numpy.array([0x81,0x42,0x3C], dtype = 'uint8'),
'*': numpy.array([0x48,0x30,0xE0,0x30,0x48], dtype = 'uint8'),
'+': numpy.array([0x10,0x10,0x7C,0x10,0x10], dtype = 'uint8'),
',': numpy.array([0x01,0x06], dtype = 'uint8'),
'-': numpy.array([0x10,0x10,0x10,0x10], dtype = 'uint8'),
'.': numpy.array([0x02], dtype = 'uint8'),
'/': numpy.array([0x03,0x0C,0x30,0xC0], dtype = 'uint8'),
'0': numpy.array([0x7C,0x8A,0x92,0xA2,0x7C], dtype = 'uint8'),
'1': numpy.array([0x40,0xFE], dtype = 'uint8'),
'2': numpy.array([0x42,0x86,0x8A,0x92,0x62], dtype = 'uint8'),
'3': numpy.array([0x84,0x92,0xB2,0xD2,0x8C], dtype = 'uint8'),
'4': numpy.array([0x18,0x28,0x48,0xFE,0x08], dtype = 'uint8'),
'5': numpy.array([0xE4,0xA2,0xA2,0xA2,0x9C], dtype = 'uint8'),
'6': numpy.array([0x3C,0x52,0x92,0x92,0x0C], dtype = 'uint8'),
'7': numpy.array([0x80,0x80,0x8E,0xB0,0xC0], dtype = 'uint8'),
'8': numpy.array([0x6C,0x92,0x92,0x92,0x6C], dtype = 'uint8'),
'9': numpy.array([0x60,0x92,0x92,0x94,0x78], dtype = 'uint8'),
':': numpy.array([0x22], dtype = 'uint8'),
';': numpy.array([0x01,0x26], dtype = 'uint8'),
'<': numpy.array([0x10,0x28,0x44], dtype = 'uint8'),
'=': numpy.array([0x28,0x28,0x28,0x28,0x28], dtype = 'uint8'),
'>': numpy.array([0x44,0x28,0x10], dtype = 'uint8'),
'?': numpy.array([0x40,0x8A,0x90,0x60], dtype = 'uint8'),
'@': numpy.array([0x3C,0x5A,0xA5,0xBD,0x44,0x38], dtype = 'uint8'),
'A': numpy.array([0x0E,0x38,0xC8,0x38,0x0E], dtype = 'uint8'),
'B': numpy.array([0xFE,0x92,0x92,0x92,0x6C], dtype = 'uint8'),
'C': numpy.array([0x7C,0x82,0x82,0x82,0x44], dtype = 'uint8'),
'D': numpy.array([0xFE,0x82,0x82,0x44,0x38], dtype = 'uint8'),
'E': numpy.array([0xFE,0x92,0x92,0x82], dtype = 'uint8'),
'F': numpy.array([0xFE,0x90,0x90,0x80], dtype = 'uint8'),
'G': numpy.array([0x7C,0x82,0x82,0x92,0x5C], dtype = 'uint8'),
'H': numpy.array([0xFE,0x10,0x10,0x10,0xFE], dtype = 'uint8'),
'I': numpy.array([0xFE], dtype = 'uint8'),
'J': numpy.array([0x0C,0x02,0x02,0x02,0xFC], dtype = 'uint8'),
'K': numpy.array([0xFE,0x10,0x28,0x44,0x82], dtype = 'uint8'),
'L': numpy.array([0xFE,0x02,0x02,0x02], dtype = 'uint8'),
'M': numpy.array([0xFE,0x40,0x20,0x40,0xFE], dtype = 'uint8'),
'N': numpy.array([0xFE,0xC0,0x30,0x0C,0xFE], dtype = 'uint8'),
'O': numpy.array([0x7C,0x82,0x82,0x82,0x7C], dtype = 'uint8'),
'P': numpy.array([0xFE,0x90,0x90,0x90,0x60], dtype = 'uint8'),
'Q': numpy.array([0x7C,0x82,0x86,0x83,0x7C], dtype = 'uint8'),
'R': numpy.array([0xFE,0x90,0x98,0x94,0x62], dtype = 'uint8'),
'S': numpy.array([0x64,0x92,0x92,0x92,0x4C], dtype = 'uint8'),
'T': numpy.array([0x80,0x80,0xFE,0x80,0x80], dtype = 'uint8'),
'U': numpy.array([0xFC,0x02,0x02,0x02,0xFC], dtype = 'uint8'),
'V': numpy.array([0xE0,0x18,0x06,0x18,0xE0], dtype = 'uint8'),
'W': numpy.array([0xF0,0x0E,0x30,0x0E,0xF0], dtype = 'uint8'),
'X': numpy.array([0xC6,0x28,0x10,0x28,0xC6], dtype = 'uint8'),
'Y': numpy.array([0xC0,0x20,0x1E,0x20,0xC0], dtype = 'uint8'),
'Z': numpy.array([0x8E,0x92,0xA2,0xC2], dtype = 'uint8'),
'[': numpy.array([0xFF,0x81], dtype = 'uint8'),
'\\': numpy.array([0xC0,0x30,0x0C,0x03], dtype = 'uint8'),
']': numpy.array([0x81,0xFF], dtype = 'uint8'),
'^': numpy.array([0x40,0x80,0x40], dtype = 'uint8'),
'_': numpy.array([0x01,0x01,0x01,0x01,0x01,0x01], dtype = 'uint8'),
'`': numpy.array([0x12,0x7E,0x92,0x82,0x04], dtype = 'uint8'),
'a': numpy.array([0x04,0x2A,0x2A,0x1E], dtype = 'uint8'),
'b': numpy.array([0xFE,0x22,0x22,0x1C], dtype = 'uint8'),
'c': numpy.array([0x1C,0x22,0x22,0x14], dtype = 'uint8'),
'd': numpy.array([0x1C,0x22,0x22,0xFE], dtype = 'uint8'),
'e': numpy.array([0x1C,0x2A,0x2A,0x18], dtype = 'uint8'),
'f': numpy.array([0x20,0x7E,0xA0,0x80], dtype = 'uint8'),
'g': numpy.array([0x18,0x25,0x25,0x3E], dtype = 'uint8'),
'h': numpy.array([0xFE,0x20,0x20,0x1E], dtype = 'uint8'),
'i': numpy.array([0xBE], dtype = 'uint8'),
'j': numpy.array([0x01,0x01,0xBE], dtype = 'uint8'),
'k': numpy.array([0xFE,0x08,0x14,0x22], dtype = 'uint8'),
'l': numpy.array([0xFC,0x02], dtype = 'uint8'),
'm': numpy.array([0x3E,0x20,0x1E,0x20,0x1E], dtype = 'uint8'),
'n': numpy.array([0x3E,0x20,0x20,0x1E], dtype = 'uint8'),
'o': numpy.array([0x1C,0x22,0x22,0x1C], dtype = 'uint8'),
'p': numpy.array([0x3F,0x24,0x24,0x18], dtype = 'uint8'),
'q': numpy.array([0x18,0x24,0x24,0x3F], dtype = 'uint8'),
'r': numpy.array([0x3E,0x10,0x20,0x20], dtype = 'uint8'),
's': numpy.array([0x12,0x2A,0x2A,0x24], dtype = 'uint8'),
't': numpy.array([0x20,0xFC,0x22], dtype = 'uint8'),
'u': numpy.array([0x3C,0x02,0x02,0x3C], dtype = 'uint8'),
'v': numpy.array([0x20,0x18,0x06,0x18,0x20], dtype = 'uint8'),
'w': numpy.array([0x38,0x06,0x08,0x06,0x38], dtype = 'uint8'),
'x': numpy.array([0x22,0x14,0x08,0x14,0x22], dtype = 'uint8'),
'y': numpy.array([0x21,0x19,0x06,0x18,0x20], dtype = 'uint8'),
'z': numpy.array([0x26,0x2A,0x32,0x22], dtype = 'uint8'),
'{': numpy.array([0x10,0x6E,0x81], dtype = 'uint8'),
'|': numpy.array([0xE7], dtype = 'uint8'),
'}': numpy.array([0x81,0x6E,0x10], dtype = 'uint8'),
'~': numpy.array([0x40,0x80,0xC0,0x40,0x80], dtype = 'uint8')
}

##### ST7565 FUNCTIONS #####

# initialise the chip, parameters:
#     horizontal and vertical screen size
#     starting column from the left and right side (horizontal normal and reverse)
#     A0, RST lines GPIO pins
#     backlight power GPIO pin (optional)
#     starting backlight value (0-1)
#     backlight power GPIO pin PWM endabled
#     SPI bus number (optional)
#     SPI frequency (optional)
# GPIO pin value is out of range (0-27) -> option not used
# note: program does not control chip select line!
class ST7565(object):
    def __init__(self, pixx, pixy, lstart, rstart, a0, rst, bl=-1, backlight=1.0, pwm=False, dev=0, frequency=20000000):
        self._pixx = pixx
        self._pixy = pixy
        self._lstart = lstart
        self._rstart = rstart
        self._a0  = a0
        self._rst = rst
        self._pwm = pwm

        # default horizontal normal
        self._start = lstart

        # Initialise GPIO
        gpioInitialise()
        gpioSetMode(a0, PI_OUTPUT)
        gpioSetMode(rst, PI_OUTPUT)

        # Initialise SPI
        spiInitialise(dev, frequency)

        # backlight power setup
        if (bl>=0 and bl<=27):
            if pwm == False: gpioSetMode(bl, PI_OUTPUT)
            else:
                if not os.path.isdir(PWMPATH):
                    print('PWM not initialised.')
                    bl = -1
                if (bl==12 or bl==18): self._pwmchan = 0
                elif (bl==13 or bl==19): self._pwmchan = 1
                else:
                    print('GPIO%d not PWM hardware pin.' % bl)
                    bl = -1
                if (bl != -1):
                    if (bl==12 or bl==13): gpioSetMode(bl, PI_ALT0)
                    if (bl==18 or bl==19): gpioSetMode(bl, PI_ALT5)
                    self._path = PWMPATH + '/pwm%d' % self._pwmchan
                    if not os.path.isdir(self._path):
                        with open(PWMPATH + '/export', 'w') as f: f.write('%d' % self._pwmchan)
                    time.sleep(0.1) # wait to stabilise
                    with open(self._path + '/period', 'w') as f: f.write('%d' % PWMPER)
        self._bl=bl
        if (bl>=0 and bl<=27):
            self.setbacklight(backlight)

        # Initialize buffers for the whole screen, one line, two byte command and three byte command
        self.buffer=numpy.zeros((self._pixy//8, self._pixx), dtype = 'uint8')
        self.bufferl=numpy.empty(2*self._pixx, dtype = 'uint8')
        self.buffer2=numpy.empty(2, dtype = 'uint8')
        self.buffer3=numpy.empty(3, dtype = 'uint8')

        gpioWrite(self._rst,1)
        self.startup()

    # startup procedure, can be used to reset the chip
    def startup(self):
        gpioWrite(self._rst,0)
        time.sleep(.5)
        gpioWrite(self._rst,1)
        self.setlcdbias(9)
        self.verticalreverse(False)
        self.horizontalreverse(False)
        self.setdisplaystartline(0x00)
        # turn on voltage converter (VC=1, VR=0, VF=0)
        self.writecommands(numpy.array([LCD_SETPOWERCONTROL | 0x4]))
        time.sleep(0.05)
        # turn on voltage regulator (VC=1, VR=1, VF=0)
        self.writecommands(numpy.array([LCD_SETPOWERCONTROL | 0x6]))
        time.sleep(0.05)
        # turn on voltage follower (VC=1, VR=1, VF=1)
        self.writecommands(numpy.array([LCD_SETPOWERCONTROL | 0x7]))
        time.sleep(0.01)
        # set lcd operating voltage (regulator resistor, ref voltage resistor)
        self.writecommands(numpy.array([LCD_SETRESISTORRATIO | 0x4]))
        self.displayon(True)
        self.displayallpoints(False)
        self.setcontrast(0x19)
        self.cleardisplay()

    # close the chip
    def close(self):
        self.cleardisplay()
        self.sleepmode()

    # clear the display
    def cleardisplay(self):
        for page in range(self._pixy//8):
            self.movecursor(0, page)
            self.writedata(numpy.zeros(self._pixx, dtype = 'uint8'))

    # turn all dots on the display on (used for sleep and standby modes)
    def displayallpoints(self, set):
        if set: self.writecommands(numpy.array([LCD_DISPLAYALLPOINTS | 0x01]))
        else: self.writecommands(numpy.array([LCD_DISPLAYALLPOINTS & ~0x01]))

    # turn display on/off
    def displayon(self, set):
        if set: self.writecommands(numpy.array([LCD_DISPLAYON | 0x01]))
        else: self.writecommands(numpy.array([LCD_DISPLAYON & ~0x01]))

    # reverse dots on the display
    def displayreverse(self, set):
        if set: self.writecommands(numpy.array([LCD_DISPLAYREVERSE | 0x01]))
        else: self.writecommands(numpy.array([LCD_DISPLAYREVERSE & ~0x01]))

    # reverse the display horizontally, refresh the screen
    def horizontalreverse(self, set):
        if set: self.writecommands(numpy.array([LCD_COMMONOUTPUTREVERSE | 0x08]))
        else: self.writecommands(numpy.array([LCD_COMMONOUTPUTREVERSE & ~0x08]))

    # move cursor to certain position, parameters: column, page
    def movecursor(self, x, page):
        if ( x >= self._pixx | x < 0 ):
            return
        if ( page >= self._pixy//8 | page < 0 ):
            return
        x = x + self._start
        self.buffer3[0] = LCD_SETPAGEADDRESS | 7-page
        self.buffer3[1] = LCD_SETCOLUMNADDRESSLOWER | (x & 0xf)
        self.buffer3[2] = LCD_SETCOLUMNADDRESSUPPER | ((x >> 4) & 0xf)
        self.writecommands(self.buffer3)

    # change the screen mode to normal, oposite: sleepmode(), standbymode()
    def normalmode(self):
        self.displayallpoints(False)
        self.displayon(True)
        self.staticindicatoron(True)

    # on starting save the current position, on ending return to the saved position
    def readmodifywrite(self, set):
        if set: self.writecommands(numpy.array([LCD_READMODIFYWRITESTART]))
        else: self.writecommands(numpy.array([LCD_READMODIFYWRITESTOP]))

    # change backlight setting
    def setbacklight(self, backlight):
        if (self._bl>=0 and self._bl<=27):
            if self._pwm == False:
                if(backlight>0): gpioWrite(self._bl, 1)
                else: gpioWrite(self._bl, 0)
            else:
                if backlight> 0:
                    with open(self._path + '/duty_cycle', 'w') as f: f.write('%d' % int(backlight*PWMPER))
                    with open(self._path + '/enable', 'w') as f: f.write('1')
                else:
                    with open(self._path + '/enable', 'w') as f: f.write('0')

    # set contrast, parameter: 0-63
    def setcontrast(self, level):
        self.buffer2[0] = LCD_SETELECTRONICVOLUME
        self.buffer2[1] = level & 0x3F
        self.writecommands(self.buffer2)

    # set display start line, parameter: 0-63
    def setdisplaystartline(self, line):
        self.writecommands(numpy.array([LCD_SETDISPLAYSTARTLINE | (line & 0x3F)]))

    # unknown function, parameter: 7 or 9
    def setlcdbias(self, set):
        if(set == 9): self.writecommands(numpy.array([LCD_SETLCDBIAS & ~0x01]))
        elif(set == 7): self.writecommands(numpy.array([LCD_SETLCDBIAS | 0x01]))
        else: print('Bias error.')

    # change the screen mode to sleep, oposite: normalmode()
    def sleepmode(self):
        self.staticindicatoron(False)
        self.displayon(False)
        self.displayallpoints(True)

    # change the screen mode to standby, oposite: normalmode()
    def standbymode(self):
        self.staticindicatoron(True)
        self.displayon(False)
        self.displayallpoints(True)

    # set screen blink,, also used for sleep/standby modes - not tested
    def staticindicatoron(self, set, register=0x03):
        if set:
            self.buffer2[0] = LCD_STATICINDICATORON | 0x01
            self.buffer2[1] = register
            self.writecommands(self.buffer2)
        else:
            self.writecommands(numpy.array([LCD_STATICINDICATORON & ~0x01]))

    # reverse the display horizontally, do not refresh the screen
    def verticalreverse(self, set):
        if set:
            self.writecommands(numpy.array([LCD_ADCREVERSE | 0x01]))
            self._start=self._rstart
        else:
            self.writecommands(numpy.array([LCD_ADCREVERSE & ~0x01]))
            self._start=self._lstart

    # write data, parameter: array
    def writedata(self, data):
        gpioWrite(self._a0,1)
        spiWrite(data.ctypes.data_as(c_void_p),len(data))

    # write commands, parameter: array
    def writecommands(self, commands):
        gpioWrite(self._a0,0)
        spiWrite(commands.ctypes.data_as(c_void_p),len(commands))

    # write a variable width font ASCII text, parameter: text, alignment ('l', 'c', 'r'), first line
    def message(self, text, align, first = 0):
        # adapt the text
        lines=text.split("\n")
        for i in range(len(lines)):
            # put the text to line buffer
            lstr=0
            lend=0
            for j in range(len(lines[i])):
                lend=lstr+len(ASCII[lines[i][j]])
                numpy.copyto(self.bufferl[lstr:lend],ASCII[lines[i][j]])
                self.bufferl[lend] = 0
                lstr = lend + 1
            # calculate front and end spaces
            add = self._pixx-lend
            if align=='l':
                addl = 0
                addr = add
            elif align=='r':
                addl = add
                addr = 0
            elif align=='c':
                addr = add//2
                addl = add-addr
            else: print('Wrong alignment: ' + align)
            # put the text to buffer
            if add>=0:
                self.buffer[i,0:addl].fill(0)
                numpy.copyto(self.buffer[i,addl:self._pixx-addr],self.bufferl[0:lend])
                self.buffer[i,self._pixx-addr:self._pixx].fill(0)
            else:
                print ("Overflow text: " + lines[i])
                numpy.copyto(self.buffer[i],self.bufferl[-addr:self._pixx-addr])
        # print buffer
        for i in range(len(lines)):
            self.movecursor(0, first+i)
            self.writedata(self.buffer[i])

    # write a monospaced font ASCII text, parameter: text, alignment ('l', 'c', 'r'), first line
    def message_m(self, text, align, first = 0):
        # adapt the text
        lines=text.split("\n")
        for i in range(len(lines)):
            # calculate front and end spaces
            add = self._pixx//8-len(lines[i])
            if align=='l':
                addl = 0
                addr = add
            elif align=='r':
                addl = add
                addr = 0
            elif align=='c':
                addr = add//2
                addl = add-addr
            else: print('Wrong alignment: ' + align)
            # put the text to line buffer
            lstr=0
            for j in range(len(lines[i])):
                numpy.copyto(self.bufferl[lstr:lstr+8],ASCII_M[lines[i][j]])
                lstr = lstr + 8
            # put the text to buffer
            if add>=0:
                self.buffer[i,0:8*addl].fill(0)
                numpy.copyto(self.buffer[i,8*addl:self._pixx-8*addr],self.bufferl[0:8*len(lines[i])])
                self.buffer[i,self._pixx-8*addr:self._pixx].fill(0)
            else:
                print ("Overflow text: " + lines[i])
                numpy.copyto(self.buffer[i],self.bufferl[-8*addr:self._pixx-8*addr])
        # print buffer
        for i in range(len(lines)):
            self.movecursor(0, first+i)
            self.writedata(self.buffer[i])
