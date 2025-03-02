#!/usr/bin/env python
"""
    Marko Pinteric 2020

    HD44780 character LCD controller
        - ultra fast parallel communication using C code
        - requires parallel.so in the same folder
        - data for fast transfer have to be supplied in contiguous block of bytes
        - supports writing and reading, reading is optional
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

import os, time
from ctypes import cdll, c_ubyte, c_void_p, c_int, c_uint, c_uint8, c_uint64

##### WRAPPING C LIBRARY (local directory or shared) #####
try:
    parallel = cdll.LoadLibrary("./parallel.so")
except OSError:
    try:
        parallel = cdll.LoadLibrary("libparallel.so")
    except OSError:
        print('Library \'parallel\' not available.  Execute \'make\' or \'make install\'.')
        exit()

"""
deinitialise(object)

Remove an instance of the chip.  Recommended but not mandatory at the end of the program.
Gets: the pointer to chip instance
"""
deinitialise = parallel.deinitialise
deinitialise.argtypes = [c_void_p]

"""
object = initialise(d7, d6, d5, d4, d3, d2, d1, d0, rscd, enwr, rwrd, protocol, tsetup, tclock, tread, tproc, thold)

Create an instance of the device.
Gets: 8 data lines, RS/CD EN/WR RW/RD control lines, protocol, 5 wait times
Returns: the pointer to chip instance
GPIO number out of range -> undefined line; D3/D2/D1/D0 undefined -> 4 bit communication; RWRD undefined -> write to chip only
"""
initialise = parallel.initialise
initialise.restype = c_void_p
initialise.argtypes = [c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int, c_int]

"""
readdata(object, [datapos], datanum)

Read multiple data.
Gets: the pointer to chip instance, the pointer to data array, the number of data to read
POINTER(c_ubyte), c_char_p -> c_void_p
"""
readdata = parallel.readdata
readdata.argtypes = [c_void_p, c_void_p, c_int]

"""
readregister(object)

Read register.
Gets: the pointer to chip instance
Returns: register value
"""
readregister = parallel.readregister
readregister.argtypes = [c_void_p]

"""
writecommand(object, datacom)

Write command.
Gets: the pointer to chip instance, command value
"""
writecommand = parallel.writecommand
writecommand.argtypes = [c_void_p, c_ubyte]

"""
writedata(object, [datapos], datanum)

Write a large set of data.
Gets: the pointer to chip instance, the pointer to data array, the number of data to read
"""
writedata = parallel.writedata
writedata.argtypes = [c_void_p, c_void_p, c_int]

"""
gpioSetMode(gpio, mode)

Set the GPIO mode.
"""
PI_OUTPUT = 1
PI_ALT0 = 4
PI_ALT5 = 2
gpioSetMode = parallel.gpioSetMode
gpioSetMode.argtypes = [c_uint, c_uint]

"""
gpioWrite(gpio, level)

Write to GPIO.
"""
gpioWrite = parallel.gpioWrite
gpioWrite.argtypes = [c_uint, c_uint]

# PWM constants
PWMPATH = '/sys/class/pwm/pwmchip0'
PWMPER = 100000 # period in nanoseconds, 10kHz

##### HD44780 CONSTANTS #####

# Commands
LCD_CLEARDISPLAY        = 0x01
LCD_RETURNHOME          = 0x02
LCD_ENTRYMODESET        = 0x04
LCD_DISPLAYCONTROL      = 0x08
LCD_CURSORDISPLAYSHIFT  = 0x10
LCD_FUNCTIONSET         = 0x20
LCD_SETCGRAMADDR        = 0x40
LCD_SETDDRAMADDR        = 0x80

# LCD_ENTRYMODESET options
LCD_ENTRYSHIFT          = 0x01
LCD_ENTRYRIGHT          = 0x02

# LCD_DISPLAYCONTROL options
LCD_DISPLAYON           = 0x04
LCD_CURSORON            = 0x02
LCD_BLINKON             = 0x01

# LCD_CURSORDISPLAYSHIFT options
LCD_DISPLAYMOVE         = 0x08
LCD_CURSORMOVE          = 0x00
LCD_MOVERIGHT           = 0x04

# LCD_FUNCTIONSET options
LCD_8BITMODE            = 0x10
LCD_4BITMODE            = 0x00
LCD_2LINE               = 0x08
#LCD_1LINE               = 0x00
#LCD_5x10DOTS            = 0x04
LCD_5x8DOTS             = 0x00

# Offset for up to 4 rows.
LCD_ROW_OFFSETS         = (0x00, 0x40, 0x20, 0x60)

##### RA6946 FUNCTIONS #####

# initialise the chip, parameters:
#     horizontal and vertical screen size
#     D7, D6, D5, D4, D3, D2, D1, D0, RS, EN, RW (optional) lines GPIO pins
#     backlight power GPIO pin (optional)
#     starting backlight value (0-1)
#     backlight power GPIO pin PWM endabled
# GPIO pin value is out of range (0-27) -> option not used
class HD44780(object):
    def __init__(self, cols, rows, d7, d6, d5, d4, d3, d2, d1, d0, rs, en, rw=-1, bl=-1,
                    backlight=1.0, pwm=False):
        self._cols = cols
        self._rows = rows
        self._pwm = pwm

        # manual: tsetup, tclock, tread, tproc, thold = 60, 500, 360, 37000, 5
        self._dev = initialise(d7, d6, d5, d4, d3, d2, d1, d0, rs, en, rw, 6800, 60, 600, 200, 60000, 0)

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

        self.startup()

    # startup procedure, can be used to reset the chip
    def startup(self):
        # three 8BITMODE put display in 8bit mode regardless of initial state, one 4BITMODE puts display in 4bit mode
        writecommand(self._dev, (LCD_FUNCTIONSET | LCD_8BITMODE) | ((LCD_FUNCTIONSET | LCD_8BITMODE) >> 4)) # 0b00110011
        writecommand(self._dev, (LCD_FUNCTIONSET | LCD_8BITMODE) | ((LCD_FUNCTIONSET | LCD_4BITMODE) >> 4)) # 0b00110010

        # default settings
        writecommand(self._dev, LCD_FUNCTIONSET | LCD_4BITMODE | LCD_2LINE | LCD_5x8DOTS)
        self.displaycontrol = LCD_DISPLAYON & ~LCD_CURSORON & ~LCD_BLINKON
        writecommand(self._dev, LCD_DISPLAYCONTROL | self.displaycontrol)
        self.entrymodeset = LCD_ENTRYRIGHT & ~LCD_ENTRYSHIFT
        writecommand(self._dev, LCD_ENTRYMODESET | self.entrymodeset)
        self.clear()

    # close the chip
    def close(self):
        if (self._bl>=0 and self._bl<=27 and self._pwm==True):
            if os.path.isdir(self._path):
                with open(PWMPATH + '/unexport', 'w') as f: f.write('%d' % self._pwmchan)
        deinitialise(self._dev)

    # set shifting display on writing a char
    def autoscroll(self, autoscroll):
        if autoscroll:
            self.entrymodeset |= LCD_ENTRYSHIFT
        else:
            self.entrymodeset &= ~LCD_ENTRYSHIFT
        writecommand(self._dev, LCD_ENTRYMODESET | self.entrymodeset)

    # set cursor blinking
    def blink(self, blink):
        if blink:
            self.displaycontrol |= LCD_BLINKON
        else:
            self.displaycontrol &= ~LCD_BLINKON
        writecommand(self._dev, LCD_DISPLAYCONTROL | self.displaycontrol)

    # clear the display
    def clear(self):
        writecommand(self._dev, LCD_CLEARDISPLAY)
        time.sleep(0.002)      # execution time is 1.52ms

    # write custom characters, parameters: list of c_uint64, location of the first character
    def definechars(self, chars, location=0):
        location &= 0x7
        writecommand(self._dev, LCD_SETCGRAMADDR | (location << 3))
        for i in chars:
            temp = (c_uint64.__ctype_be__ *1) (i)
            writedata(self._dev, temp, 8)

    # turn on/of the display
    def enable_display(self, enable):
        if enable:
            self.displaycontrol |= LCD_DISPLAYON
        else:
            self.displaycontrol &= ~LCD_DISPLAYON
        writecommand(self._dev, LCD_DISPLAYCONTROL | self.displaycontrol)

    # put cursor to home address
    def home(self):
        writecommand(self._dev, LCD_RETURNHOME)
        time.sleep(0.002)      # execution time is 1.52ms

    # write a multiline message, EOL puts text in a new line
    def message(self, text):
        row = 0
#        col = 0 if self.entrymodeset & LCD_ENTRYRIGHT > 0 else self._cols-1
        self.home()
        for i in range(len(text)):
            if (text[i] == '\n') and (text[i-1] == '\r') and (i>0):
                continue
            if (text[i] == '\r') and (text[i+1] == '\n') and (i<len(text)-1):
                # new line
                row = row+1
                col = 0 if self.entrymodeset & LCD_ENTRYRIGHT > 0 else self._cols-1
                self.set_cursor(col, row)
            else:
                # write the character
                uint = (c_ubyte)(*ord(text[i])) # character has to be trasferred in the C compatible array
                writedata(self._dev, uint, 1)

    # move cursor left
    def move_cursorleft(self):
        writecommand(self._dev, LCD_CURSORDISPLAYSHIFT | LCD_CURSORMOVE & ~LCD_MOVERIGHT)

    # move cursor right
    def move_cursorright(self):
        writecommand(self._dev, LCD_CURSORDISPLAYSHIFT | LCD_CURSORMOVE | LCD_MOVERIGHT)

    # move display left
    def move_displayleft(self):
        self.writebyte(LCD_CURSORDISPLAYSHIFT | LCD_DISPLAYMOVE & ~LCD_MOVERIGHT)

    # move display right
    def move_displayright(self):
        writecommand(self._dev, LCD_CURSORDISPLAYSHIFT | LCD_DISPLAYMOVE | LCD_MOVERIGHT)

    # read multiple data, parameters: pointer, length
    def readdata(self, str, len):
        dat = readdata(self._dev, str, len)
        return(dat)

    # read status
    def readstatus(self):
        dat = readregister(self._dev)
        return(dat)

    # set cursor to specified column and row
    def set_cursor(self, col, row):
        if row >= self._rows:
            row = row % self._rows
        writecommand(self._dev, LCD_SETDDRAMADDR | (col + LCD_ROW_OFFSETS[row]))

    # sets character writing left to right
    def set_left_to_right(self):
        self.entrymodeset |= LCD_ENTRYRIGHT
        writecommand(self._dev, LCD_ENTRYMODESET | self.entrymodeset)

    # sets character writing right to left
    def set_right_to_left(self):
        self.entrymodeset &= ~LCD_ENTRYRIGHT
        writecommand(self._dev, LCD_ENTRYMODESET | self.entrymodeset)

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

    # show cursor
    def show_cursor(self, show):
        if show:
            self.displaycontrol |= LCD_CURSORON
        else:
            self.displaycontrol &= ~LCD_CURSORON
        writecommand(self._dev, LCD_DISPLAYCONTROL | self.displaycontrol)

    # write a full line of text: parameter
    def text(self, text):
        writedata(self._dev, text, self._cols)

    # write data: parameters: pointer, length
    def writedata(self, str, len):
        dat = writedata(self._dev, str, len)
