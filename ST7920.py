#!/usr/bin/env python
"""
    Marko Pinteric 2021

    ST7920 graphic LCD controller
        - fast parallel communication using C code
        - requires parallel.so in the same folder
        - data for fast transfer have to be supplied in contiguous block of bytes
        - supports writing and reading, reading is optional
        - controls backlight, PWM uses dtoverlay method
        - works only for common 128 x 64 screens, which splits original 256 x 32 in halfs

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
from ctypes import cdll, c_int, c_uint, c_uint8, c_uint32, c_ubyte, c_void_p

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

##### ST7925 CONSTANTS #####

LCD_CLEAR           = 0x01
LCD_HOME            = 0x02
LCD_ENTRY           = 0x04
LCD_DISPLAYSTATUS   = 0x08
LCD_SHIFT           = 0x10
LCD_FUNCTIONSET     = 0x20
LCD_CGRAMADDRESS    = 0x40 # char generation
LCD_DDRAMADDRESS    = 0x80 # char display
LCD_STANDBY         = 0x01
LCD_SCROLLRAM       = 0x02
LCD_REVERSE         = 0x04
LCD_IRAMADDRESS     = 0x40 # icon - UNKNOWN
LCD_GDRAMADDRESS    = 0x80 # graphic display

# LCD_ENTRY constants
LCD_ENTRYRIGHT      = 0x02
LCD_ENTRYDISPLAY    = 0x01
# LCD_DISPLAYSTATUS constants
LCD_DISPLAYON       = 0x04
LCD_CURSORON        = 0x02
LCD_BLINKON         = 0x01
# LCD_SHIFT constants
LCD_SHIFTDISPLAY    = 0x08
LCD_SHIFTRIGHT      = 0x04
# LCD_FUNCTIONSET constants
LCD_8BIT            = 0x10 # only done in beginning
LCD_EXTENDED        = 0x04
LCD_GRAPHICON       = 0x02
# LCD_SCROLLRAM constants
LCD_SCROLL          = 0x01

##### ST7920 FUNCTIONS #####

# initialise the chip, parameters:
#     D7, D6, D5, D4, D3, D2, D1, D0, RS, EN, RW (optional), RST (optional) lines GPIO pins
#     backlight power GPIO pin (optional)
#     starting backlight value (0-1)
#     backlight power GPIO pin PWM endabled
# GPIO pin value is out of range (0-27) -> option not used
class ST7920(object):
    def __init__(self, rst, d7, d6, d5, d4, d3, d2, d1, d0, rs, en, rw=-1, bl=-1, backlight=1.0, pwm=False):
        self._rst = rst
        self._pwm = pwm
        self._d0 = d0

        # default values
        self._entry         = 0x02
        self._displaystatus = 0x00
        self._functionset   = 0x10

        # writing track, first reading after writing returns dummy byte
        self._write = True

        # manual: tsetup, tclock, tread, tproc, thold = 10, 600, 360, 72000, 20
        self._dev = initialise(d7, d6, d5, d4, d3, d2, d1, d0, rs, en, rw, 6800, 10, 100, 360, 47000, 20)

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

        # initialize buffers for the whole graphic display and the whole char display
        self.bufferg=numpy.zeros((64, 16), dtype = 'uint8')
        self.bufferc=numpy.zeros((8, 16), dtype = 'uint8')

        self.startup()

    # startup procedure, can be used to reset the chip
    def startup(self):
        if (self._rst>=0 and self._rst<=27):
            gpioWrite(self._rst,1)
            time.sleep(0.1)
            gpioWrite(self._rst,0)
            time.sleep(0.1)
            gpioWrite(self._rst,1)
            time.sleep(0.1)

        if (self._d0>=0 and self._d0<=27):
            # 8 bit communication
            writecommand(self._dev, LCD_FUNCTIONSET | LCD_8BIT)
        else:
            # 4 bit communication
            self._functionset = 0x00
            # chip has problems into entering 4 bit mode
            for i in range(30):
                writecommand(self._dev, LCD_FUNCTIONSET & ~LCD_8BIT)
                time.sleep(0.001)

        self.clearchar()
        self.displayon(True);

    # close the chip
    def close(self):
        self.extendedon(False)
        self.clearchar()
        self.displayon(False);
        if (self._bl>=0 and self._bl<=27 and self._pwm==True):
            if os.path.isdir(self._path):
                with open(PWMPATH + '/unexport', 'w') as f: f.write('%d' % self._pwmchan)
        deinitialise(self._dev)


    # turn cursor blink on/off (useless for alphanumerical characters)
    def blinkon(self, value):
        if (self._functionset & 0x04)>0: print('Error: blinkon called when in extended mode.')
        if value: self._displaystatus = self._displaystatus | LCD_BLINKON
        else: self._displaystatus = self._displaystatus & ~LCD_BLINKON
        writecommand(self._dev, LCD_DISPLAYSTATUS | self._displaystatus)
        self._write=True

    # clear the char display and return to the first page
    def clearchar(self):
        if (self._functionset & 0x04)>0: print('Error: clearchar called when in extended mode.')
        writecommand(self._dev, LCD_CLEAR)
        self._write=True
        time.sleep(0.003)

    # clear the graphic display
    def cleargraphic(self):
        if (self._functionset & 0x04)==0: print('Error: cleargraphic called when in basic mode.')
        bufferz=numpy.zeros(32, dtype = 'uint8')
        for i in range(64):
            writecommand(self._dev, LCD_GDRAMADDRESS | i)
            writecommand(self._dev, LCD_GDRAMADDRESS | 0)
            writedata(self._dev, bufferz.ctypes.data_as(c_void_p), 32)
        self._write=True

    # turn cursor on/off (useless for alphanumerical characters)
    def cursoron(self, value):
        if (self._functionset & 0x04)>0: print('Error: cursoron called when in extended mode.')
        if value: self._displaystatus = self._displaystatus | LCD_CURSORON
        else: self._displaystatus = self._displaystatus & ~LCD_CURSORON
        writecommand(self._dev, LCD_DISPLAYSTATUS | self._displaystatus)
        self._write=True

    # turn display on/off
    def displayon(self, value):
        if (self._functionset & 0x04)>0: print('Error: displayon called when in extended mode.')
        if value: self._displaystatus = self._displaystatus | LCD_DISPLAYON
        else: self._displaystatus = self._displaystatus & ~LCD_DISPLAYON
        writecommand(self._dev, LCD_DISPLAYSTATUS | self._displaystatus)
        self._write=True

    # on entering new character, rotate text (useless with 128 x 64)
    def entrydisplay(self, value):
        if (self._functionset & 0x04)>0: print('Error: entrydisplay called when in extended mode.')
        if value: self._entry = self._entry | LCD_ENTRYDISPLAY
        else: self._entry = self._entry & ~LCD_ENTRYDISPLAY
        writecommand(self._dev, LCD_ENTRY | self._entry)
        self._write=True

    # on entering new character, shift cursor right/left
    def entryright(self, value):
        if (self._functionset & 0x04)>0: print('Error: entryright called when in extended mode.')
        if value: self._entry = self._entry | LCD_ENTRYRIGHT
        else: self._entry = self._entry & ~LCD_ENTRYRIGHT
        writecommand(self._dev, LCD_ENTRY | self._entry)
        self._write=True

    # turn extended commands on/off
    def extendedon(self, value):
        if value: self._functionset =  self._functionset | LCD_EXTENDED
        else: self._functionset =  self._functionset & ~LCD_EXTENDED
        writecommand(self._dev, LCD_FUNCTIONSET | self._functionset)
        self._write=True

    # turn graphic commands on/off
    def graphicon(self, value):
        if (self._functionset & 0x04)==0: print('Error: graphicon called when in basic mode.')
        if value: self._functionset =  self._functionset | LCD_GRAPHICON
        else: self._functionset =  self._functionset & ~LCD_GRAPHICON
        writecommand(self._dev, LCD_FUNCTIONSET | self._functionset)
        self._write=True

    # write a 16x16 px font ASCII text, parameter: text, alignment ('l', 'c', 'r'), first line
    def message_full(self, text, align, first = 0):
        lines=text.split("\n")
        for i in range(len(lines)):
            # put the text to line buffer
            temp = numpy.empty(2*len(lines[i]), dtype = 'uint8')
            for j in range(len(lines[i])):
                # each 16x16 px character has two bytes, the first byte for latin characters is 0xA3
                temp[2*j] = 0xA3
                temp[2*j+1] = ord(lines[i][j])
            # calculate front and end spaces
            add = 8-len(lines[i])
            if align=='l':
                addl = 0
                addr = add
            elif align=='r':
                addl = add
                addr = 0
            elif align=='c':
                addr = add//2
                addl = add-addr
            else:
                 print('Wrong alignment: ' + align)
            # put the text to buffer
            if add>=0:
                self.bufferc[i,0:2*addl].fill(0x20)
                numpy.copyto(self.bufferc[i,2*addl:16-2*addr],temp)
                self.bufferc[i,16-2*addr:16].fill(0x20)
            else:
                print ("Overflow text: " + lines[i])
                numpy.copyto(self.bufferc[i],numpy.frombuffer(temp[-2*addr:16-2*addr], dtype=numpy.uint8))
        # print buffer
        for i in range(len(lines)):
            self.setcharposition(0, first+i)
            writedata(self._dev, self.bufferc[i].ctypes.data_as(c_void_p), 16)
            self._write=True

    # write a 8x16 px font ASCII text, parameter: text, alignment ('l', 'c', 'r'), first line
    def message_half(self, text, align, first = 0):
        lines=text.split("\n")
        for i in range(len(lines)):
            # calculate front and end spaces
            add = 16-len(lines[i])
            if align=='l':
                addl = 0
                addr = add
            elif align=='r':
                addl = add
                addr = 0
            elif align=='c':
                addr = add//2
                addl = add-addr
            else:
                 print('Wrong alignment: ' + align)
            # put the text to buffer
            if add>=0:
                self.bufferc[i,0:addl].fill(0x20)
                numpy.copyto(self.bufferc[i,addl:16-addr],numpy.frombuffer(lines[i].encode('utf-8'), dtype=numpy.uint8))
                self.bufferc[i,16-addr:16].fill(0x20)
            else:
                print ("Overflow text: " + lines[i])
                numpy.copyto(self.bufferc[i],numpy.frombuffer(lines[i][-addr:16-addr].encode('utf-8'), dtype=numpy.uint8))
        # print buffer
        for i in range(len(lines)):
            self.setcharposition(0, first+i)
            writedata(self._dev, self.bufferc[i].ctypes.data_as(c_void_p), 16)
            self._write=True

    # read multiple data, parameters: pointer, length
    def readdata(self, datapos, datanum):
        # first reading after writing returns dummy byte
        if(self._write): readdata(self._dev, datapos, 1)
        readdata(self._dev, datapos, datanum)
        self._write=False

    # read status
    def readstatus(self):
        temp = readregister(self._dev)
        return(temp)

    # turn scrolling on/off
    def scrollon(self, value):
        if (self._functionset & 0x04)==0: print('Error: scrollon called when in basic mode.')
        if value: writecommand(self._dev, LCD_SCROLLRAM | LCD_SCROLL)
        else: writecommand(self._dev, LCD_SCROLLRAM & ~LCD_SCROLL)
        self._write=True

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

    # set memory pointer to char display to home
    def setcharhome(self):
        if (self._functionset & 0x04)>0: print('Error: setcharhome called when in extended mode.')
        writecommand(self._dev, LCD_HOME)
        self._write=True

    # DDRAM consists of 8 blocks per 16 bytes
    # |   0   |   2   |   1   |   3   |   4   |   6   |   5   |   7   |
    # set memory pointer to char display position: 0<=col<=7, 0<=row<=7
    def setcharposition(self, col, row):
        if (self._functionset & 0x04)>0: print('Error: setcharposition called when in extended mode.')
        writecommand(self._dev, LCD_DDRAMADDRESS | (((((row & 0x04)>>1) + (row & 0x01))<<4) + ((row & 0x02)<<2) + col))
        self._write=True

    # CGRAM consists of 4 blocks per 32 bytes for 16x16 characters: 0x0000, 0x0002, 0x0004, 0x0006
    # set memory pointer to character generation position: 0<=value<=63
    def setcgposition(self, value):
        if (self._functionset & 0x04)>0: print('Error: setcgposition called when in extended mode.')
        writecommand(self._dev, LCD_CGRAMADDRESS | value)
        self._write=True

    # scrolling disabled: set memory pointer to icon RAM position (unknown effect)
    # scrolling enabled: scrolling, parameter: 0<=value<=63
    def setiposition(self, value):
        if (self._functionset & 0x04)==0: print('Error: setiposition called when in basic mode.')
        writecommand(self._dev, LCD_IRAMADDRESS | value)
        self._write=True

    # GDRAM line consists of 256 blocks per 16 bytes
    # |   0   |   32  |   _   |  ...  |   _   |
    # |   1   |   33  |   _   |  ...  |   _   |
    #    ...     ...     ...     ...     ...
    # |  31   |   63  |   _   |  ...  |   _   |
    # |  64   |   96  |   _   |  ...  |   _   |
    # |  65   |   97  |   _   |  ...  |   _   |
    #    ...     ...     ...     ...     ...
    # |  95   |  127  |   _   |  ...  |   _   |
    # set memory pointer to graphic display position, parameters: 0<=x<=7, 0<=y<=127
    def setgraphicposition(self, x, y):
        if (self._functionset & 0x04)==0: print('Error: setgraphicposition called when in basic mode.')
        writecommand(self._dev, LCD_GDRAMADDRESS | (((y & 0x40)>>1) + (y & 0x1F)))
        writecommand(self._dev, LCD_GDRAMADDRESS | (((y & 0x20)>>2) + x))
        self._write=True

    # rotate text right/left (useless with 128 x 64)
    def shiftdisplayright(self, value):
        if (self._functionset & 0x04)>0: print('Error: shiftdisplayright called when in extended mode.')
        if value: writecommand(self._dev, LCD_SHIFT | LCD_SHIFTRIGHT | LCD_SHIFTDISPLAY)
        else: writecommand(self._dev, LCD_SHIFT | LCD_SHIFTDISPLAY)
        self._write=True

    # shift cursor right/left
    def shiftright(self, value):
        if (self._functionset & 0x04)>0: print('Error: shiftright called when in extended mode.')
        if value: writecommand(self._dev, LCD_SHIFT | LCD_SHIFTRIGHT)
        else: writecommand(self._dev, LCD_SHIFT)
        self._write=True

    # standby mode
    def standby(self):
        if (self._functionset & 0x04)==0: print('Error: standby called when in basic mode.')
        writecommand(self._dev, LCD_STANDBY)
        self._write=True

    # toggle reverse line, parameter: 0<=line<=1 (useless with 128 x 64)
    def togglereverse(self, line):
        if (self._functionset & 0x04)==0: print('Error: togglereverse called when in basic mode.')
        writecommand(self._dev, LCD_REVERSE | line)
        self._write=True

    # write data, parameter: array
    def writedata(self, data):
        if (len(data) % 2)==1: print('Error: writing odd number of bytes.')
        writedata(self._dev, data.ctypes.data_as(c_void_p), len(data))
        self._write=True
