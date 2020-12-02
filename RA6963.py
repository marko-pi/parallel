#!/usr/bin/env python
"""
    Marko Pinteric 2020

    RA6963 graphic LCD controller
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

import os, numpy, time
from ctypes import cdll, c_ubyte, c_void_p, c_int, c_uint, c_uint8, c_uint16, c_uint64

##### WRAPPING C LIBRARY #####

parallel = cdll.LoadLibrary("./parallel.so")

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

##### RA6946 CONSTANTS #####

# Commands
LCD_SETCURSORPOINTER       = 0x21
LCD_SETOFFSETREGISTER      = 0x22
LCD_SETADDRESSPOINTER      = 0x24
LCD_SETTEXTHOMEADDRESS     = 0x40
LCD_SETTEXTAREA            = 0x41
LCD_SETGRAPHICHOMEADDRESS  = 0x42
LCD_SETGRAPHICAREA         = 0x43
LCD_MODESET                = 0x80
LCD_DISPLAYMODE            = 0x90
LCD_CURSORPATTERNSELECT    = 0xA0
LCD_DATAWRITEINCREMENT     = 0xC0
LCD_DATAREADINCREMENT      = 0xC1
LCD_DATAWRITEDECREMENT     = 0xC2
LCD_DATAEREADDECREMENT     = 0xC2
LCD_DATAWRITENONVARIABLE   = 0xC4
LCD_DATAREADNONVARIABLE    = 0xC4
LCD_SETDATAAUTOWRITE       = 0xB0
LCD_SETDATAAUTOREAD        = 0xB1
LCD_AUTORESET              = 0xB2
LCD_SCREENPEEK             = 0xE0
LCD_SCREENCOPY             = 0xE8
LCD_BITRESET               = 0xF0
LCD_BITSET                 = 0xF8
LCD_SCREENREVERSE          = 0xD0
LCD_BLINKTIME              = 0x50
LCD_CURSORAUTOMOVING       = 0x60
LCD_CGROMFONTSELECT        = 0x70

# LCD_MODESET options
LCD_OR                     = 0x00
LCD_EXOR                   = 0x01
LCD_AND                    = 0x03
LCD_TEXTATTRIBUTE          = 0x04
LCD_EXTERNALCGROM          = 0x08

# LCD_DISPLAYMODE options
LCD_CURSORBLINK            = 0x01
LCD_CURSORON               = 0x02
LCD_TEXTON                 = 0x04
LCD_GRAPHICON              = 0x08

##### RA6946 FUNCTIONS #####

# initialise the chip, parameters:
#     horizontal and vertical screen size
#     D7, D6, D5, D4, D3, D2, D1, D0, RST, CD, WR, RD (optional) lines GPIO pins
#     backlight power GPIO pin (optional)
#     starting backlight value (0-1)
#     backlight power GPIO pin PWM endabled
#     user specified home addresses for text, graphics and character generator (optional)
# GPIO pin value is out of range (0-27) -> option not used
class RA6963(object):
    def __init__(self, pixx, pixy, d7, d6, d5, d4, d3, d2, d1, d0, rst, cd, wr, rd=-1, bl=-1,  backlight=1.0, pwm=False, addr=None):
        self._pixx = pixx
        self._pixy = pixy
        self._rst = rst
        self._pwm = pwm
        self.addr = addr
        # screen attributes
        self.inhibit = 0x03
        self.reverse = 0x05
        self.bold = 0x07
        self.blink = 0x08
        # hardware default value
        self._displaymode = 0
        # software default value
        self._modeset = 0

        # manual: tsetup, tclock, tread, tproc, thold = 20, 80, 150, 80, 50
        self._dev = initialise(d7, d6, d5, d4, d3, d2, d1, d0, cd, wr, rd, 8080, 20, 2000, 300, 1000, 2000)

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

        # restart chip
        gpioWrite(self._rst, 1)
        gpioSetMode(self._rst, PI_OUTPUT)
        self.startup()

    # startup procedure, can be used to reset the chip
    def startup(self):
        # reset

        gpioWrite(self._rst, 0)
        gpioWrite(self._rst, 1)

        # text, graphics and character generator positions
        if self.addr==None:
            self.textaddress=0x0000
            self.graphicaddress=0x1000
            self.cgaddress=0x7800
        else:
            self.textaddress=self.addr[0]
            self.graphicaddress=self.addr[1]
            self.cgaddress=self.addr[2]

        temp = (c_uint16.__ctype_le__ *1) (self.textaddress)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETTEXTHOMEADDRESS)

        temp = (c_uint16.__ctype_le__ *1) (self._pixx//8)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETTEXTAREA)

        temp = (c_uint16.__ctype_le__ *1) (self.graphicaddress)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETGRAPHICHOMEADDRESS)

        temp = (c_uint16.__ctype_le__ *1) (self._pixx//8)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETGRAPHICAREA)

        if (self.cgaddress & 0x07FF) > 0:
            print('Specified CG address is wrong.  Rounding to lower correct address...')
            self.cgaddress = self.cgaddress & 0xF800
        temp = (c_uint16.__ctype_le__ *1) (self.cgaddress >> 11)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETOFFSETREGISTER)

    # close the chip
    def close(self):
        if (self._bl>=0 and self._bl<=27 and self._pwm==True):
            if os.path.isdir(self._path):
                with open(PWMPATH + '/unexport', 'w') as f: f.write('%d' % self._pwmchan)
        deinitialise(self._dev)

    # reset a bit at current pointer address, parameter: 0-7
    def bitreset(self,num):
        writecommand(self._dev, LCD_BITRESET | num)

    # set a bit at current pointer address, parameter: 0-7
    def bitset(self,num):
        writecommand(self._dev, LCD_BITSET | num)

    # speed of blinking, parameter: 0-7
    def blinktime(self,num):
        temp = (c_uint16.__ctype_le__ *1) (num)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_BLINKTIME)

    # put pointer to character generator home and return the address
    def cghome(self):
        temp = (c_uint16.__ctype_le__ *1) (self.cgaddress)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETADDRESSPOINTER)
        return(self.cgaddress)

    # pick CGROM font, parameter: 1-2
    def cgromfont(self, num):
        if num==1: temp = (c_uint16.__ctype_le__ *1) (0x0002)
        else: temp = (c_uint16.__ctype_le__ *1) (0x0003)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_CGROMFONTSELECT)

    # clear graphic, text and character generator memories
    def clearall(self):
        self.graphichome()
        temp = numpy.zeros(shape=(self._pixx*self._pixy//8,), dtype=numpy.int8)
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        writedata(self._dev, temp.ctypes.data_as(c_void_p), self._pixx*self._pixy//8)
        writecommand(self._dev, LCD_AUTORESET)
        self.texthome()
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        writedata(self._dev, temp.ctypes.data_as(c_void_p), self._pixx*self._pixy//64)
        writecommand(self._dev, LCD_AUTORESET)
        self.cghome()
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        writedata(self._dev, temp.ctypes.data_as(c_void_p), 2048)
        writecommand(self._dev, LCD_AUTORESET)

    # change cursor blink, parameter: boolean
    def cursorblink(self, blink):
        if blink: self._displaymode = self._displaymode | LCD_CURSORBLINK
        else: self._displaymode = self._displaymode & ~LCD_CURSORBLINK
        writecommand(self._dev, LCD_DISPLAYMODE | self._displaymode)

    # change cursor display, parameter: boolean
    def cursordisplay(self, display):
        if display: self._displaymode = self._displaymode | LCD_CURSORON
        else: self._displaymode = self._displaymode & ~LCD_CURSORON
        writecommand(self._dev, LCD_DISPLAYMODE | self._displaymode)

    # change cursor move, parameter: boolean
    def cursormove(self, move):
        if move: self._displaymode = writecommand(self._dev, LCD_CURSORAUTOMOVING | 0x00)
        else: self._displaymode = writecommand(self._dev, LCD_CURSORAUTOMOVING | 0x01)

    # select cursor pattern, parameter: 0-7
    def cursorpattern(self, patt):
        writecommand(self._dev, LCD_CURSORPATTERNSELECT | patt)

    # write custom characters (first 128 are predefined), parameters: list of c_uint64, location of the first character
    def definechars(self, chars, location = 0):
        self.setaddress(self.cgaddress+128*8 + location*8)
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        for i in chars:
            temp = (c_uint64.__ctype_be__ *1) (i)
            writedata(self._dev, temp, 8)
        writecommand(self._dev, LCD_AUTORESET)

    # change display mode, parameters: boolean (text), boolean (graphic)
    def displaymode(self, text, graphic):
        if text: self._displaymode = self._displaymode | LCD_TEXTON
        else: self._displaymode = self._displaymode & ~LCD_TEXTON
        if graphic: self._displaymode = self._displaymode | LCD_GRAPHICON
        else: self._displaymode = self._displaymode & ~LCD_GRAPHICON
        writecommand(self._dev, LCD_DISPLAYMODE | self._displaymode)

    # use external character generator, parameter: boolean
    def externalcg(self, bool):
        if bool: self._modeset = self._modeset | LCD_EXTERNALCGROM
        else: self._modeset = self._modeset & ~LCD_EXTERNALCGROM
        writecommand(self._dev, LCD_MODESET | self._modeset)

    # put pointer to graphics home and return the address
    def graphichome(self):
        temp = (c_uint16.__ctype_le__ *1) (self.graphicaddress)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETADDRESSPOINTER)
        return(self.graphicaddress)

    # change mode set, parameter: 1-4 (OR, EXOR, AND, text attribute)
    def modeset(self, mode):
        self._modeset = self._modeset & ~(LCD_OR | LCD_EXOR | LCD_AND | LCD_TEXTATTRIBUTE)
        if mode==1: self._modeset = self._modeset | LCD_OR
        if mode==2: self._modeset = self._modeset | LCD_EXOR
        if mode==3: self._modeset = self._modeset | LCD_AND
        if mode==4: self._modeset = self._modeset | LCD_TEXTATTRIBUTE
        writecommand(self._dev, LCD_MODESET | self._modeset)

    # read multiple data, parameters: pointer, length
    def readdata(self, datapos, datanum):
        writecommand(self._dev, LCD_SETDATAAUTOREAD)
        readdata(self._dev, datapos, datanum)
        writecommand(self._dev, LCD_AUTORESET)

    # read a datum, decrement pointer position
    def readdecrement(self):
        temp = (c_uint8 *1) ()
        writecommand(self._dev, LCD_DATAREADDECREMENT)
        readdata(self._dev, temp, 1)
        return(temp[0])

    # read a datum, increment pointer position
    def readincrement(self):
        temp = (c_uint8 *1) ()
        writecommand(self._dev, LCD_DATAREADINCREMENT)
        readdata(self._dev, temp, 1)
        return(temp[0])

    # read status
    def readstatus(self):
        temp = readregister(self._dev)
        return(temp)

    # read a datum, don't change pointer position
    def readonvariable(self):
        temp = (c_uint8 *1) ()
        writecommand(self._dev, LCD_DATAREADNONVARIABLE)
        readdata(self._dev, temp, 1)
        return(temp[0])

    # copy a single raster line of data to the graphic area - available in single-mode
    def screencopy(self):
        writecommand(self._dev, LCD_SCREENCOPY)

    # peek position on the screen - available when hardware column number and software column number are the same
    def screenpeek(self):
        temp = (c_uint8 *1) ()
        writecommand(self._dev, LCD_SCREENPEEK)
        readdata(self._dev, temp, 1)
        return(temp[0])

    # reverse screen, parameter: boolean
    def screenreverse(self,bool):
        if bool: writecommand(self._dev, LCD_SCREENREVERSE,1,1)
        else: writecommand(self._dev, LCD_SCREENREVERSE,1,0)

    # set current pointer address
    def setaddress(self, value):
        temp = (c_uint16.__ctype_le__ *1) (value)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETADDRESSPOINTER)

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

    # set current pointer address
    def setcursor(self, xaddr, yaddr):
        temp = (c_uint16.__ctype_le__ *2) (256 * yaddr + xaddr)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETCURSORPOINTER)

    # change text home, parameter: 0x0000 - 0xFFFF
    def settexthome(self, value):
        self.textaddress=value
        temp = (c_uint16.__ctype_le__ *1) (value)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETTEXTHOMEADDRESS)

    # change graphic home, parameter: 0x0000 - 0xFFFF
    def setgraphichome(self, value):
        self.graphicaddress=value
        temp = (c_uint16.__ctype_le__ *1) (value)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETGRAPHICHOMEADDRESS)

    # put pointer to text home and return the address
    def texthome(self):
        temp = (c_uint16.__ctype_le__ *1) (self.textaddress)
        writedata(self._dev, temp, 2)
        writecommand(self._dev, LCD_SETADDRESSPOINTER)
        return(self.textaddress)

    # write data: parameters: pointer, length
    def writedata(self, datapos, datanum):
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        writedata(self._dev, datapos, datanum)
        writecommand(self._dev, LCD_AUTORESET)

    # write a datum, decrement pointer position
    def writedecrement(self, value):
        temp = (c_uint8 *1) (value)
        writedata(self._dev, temp, 1)
        writecommand(self._dev, LCD_DATAWRITEDECREMENT)

    # write a datum, increment pointer position
    def writeincrement(self, value):
        temp = (c_uint8 *1) (value)
        writedata(self._dev, temp, 1)
        writecommand(self._dev, LCD_DATAWRITEINCREMENT)

    # write a datum, don't change pointer position
    def writeonvariable(self, value):
        temp = (c_uint8 *1) (value)
        writedata(self._dev, temp, 1)
        writecommand(self._dev, LCD_DATAWRITENONVARIABLE)

    # write a full screen ASCII text, parameter: pointer
    def writetext(self, text):
        temp=bytearray(text.replace("\n", ""))
        for i in range(len(temp)):
            temp[i] = temp[i] - 32
        text = str(temp)
        self.texthome()
        writecommand(self._dev, LCD_SETDATAAUTOWRITE)
        writedata(self._dev, text, len(text))
        writecommand(self._dev, LCD_AUTORESET)
