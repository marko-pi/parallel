# parallel

This repository is dedicated to fast parallel communications on Raspberry Pi.  The speed is essential when communicating with large liquid crystal displays, as a lot of data has to be transferred for a single full screen picture.

## Main library

### parallel.c

General purpose C library for parallel communications on Raspberry Pi
   - supports 6800 and 8080 protocols, both 4 bits and 8 bits
   - supports arbitrary GPIO pins from 0 to 27
   - supports writing and reading, reading is optional
   - supports objective oriented programming, initialisation returns the pointer to chip instance
   - all RPi data lines by default in read/input mode in order to avoid possible conflict and destruction of GPIO pins

![Times](/times.png)

\* on writing between two half-bytes (4 bits protocol): *t*<sub>clock</sub>; on writing after full byte: *t*<sub>proc</sub>; on reading between two half-bytes (4 bits protocol): larger of *t*<sub>clock</sub> and *t*<sub>hold</sub>; on reading after full byte: larger of *t*<sub>proc</sub> and *t*<sub>hold</sub>.

[More information of parallel protocols](http://www.pinteric.com/displays.html#par)

### parallel.so

C library compiled for use with Python

## Examples of use: HD44780

### HD44780.py

Python library for HD44780 controller chip (requires parallel.so)

### HD44780_test.py

Python test file for the Python Library (reqires HD44780.py)

[The result](https://youtu.be/9l0SO73js7g)

**Note:** If you don't want to control backlight from the program, set <code>bl=-1</code>.  If you are not interested in backlight PWM, set <code>pwm=False</code>.  If there are problems, try to make waiting times longer.

## Examples of use: RA6963

### RA6963.py

Python library for RA6963 controller chip (requires parallel.so)

### RA6963_test.py

Python test file for the Python Library (reqires RA6963.py)

[The result](https://youtu.be/7CxnJM1tHzU)

**Note:** If you don't want to control backlight from the program, set <code>bl=-1</code>.  If you are not interested in backlight PWM, set <code>pwm=False</code>.  If there are problems, try to make waiting times longer.
