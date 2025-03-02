/*
    Marko Pinteric 2020-2025
    GPIO communication based on Tiny GPIO Access on http://abyz.me.uk/rpi/pigpio/examples.html

    General purpose C library for parallel communications on Raspberry Pi
        - supports 6800 and 8080 protocols, both 4 bits and 8 bits
        - supports arbitrary GPIO pins from 0 to 27
        - supports writing and reading, reading is optional
        - supports objective oriented programming, initialisation returns the pointer to chip instance
        - all RPi data lines by default in read/input mode in order to avoid possible conflict and destruction of GPIO pins

    For more information see: https://github.com/marko-pi/parallel, http://www.pinteric.com/displays.html

    Version 2:
        - More precise timing;
        - Code streamlined by consolidating duplicates.

    To create C library execute 'make' (library in local directory) or 'make install' (shared library).
    To remove C library execute 'make clear' (library in local directory) or 'make uninstall' (shared library).
*/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>
#include <fcntl.h>
#include <stdbool.h>
#include <time.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>

/* TINY GPIO VARIABLES */

#define GPSET0 7
#define GPSET1 8

#define GPCLR0 10
#define GPCLR1 11

#define GPLEV0 13
#define GPLEV1 14

#define GPPUD     37
#define GPPUDCLK0 38
#define GPPUDCLK1 39

/* GPIO address */
volatile static uint32_t  *gpioReg = MAP_FAILED;

#define PI_BANK (gpio>>5)
#define PI_BIT  (1<<(gpio&0x1F))

/* gpio modes */

#define PI_INPUT  0
#define PI_OUTPUT 1
#define PI_ALT0   4
#define PI_ALT1   5
#define PI_ALT2   6
#define PI_ALT3   7
#define PI_ALT4   3
#define PI_ALT5   2

/* values for pull-ups/downs off, pull-down and pull-up */

#define PI_PUD_OFF  0
#define PI_PUD_DOWN 1
#define PI_PUD_UP   2

/* INTERNAL VARIABLES */

#define UNDEFINED 0xFFFF

/* 8 data lines, RS/CD EN/WR RW/RD control lines, protocol, 5 wait times */
struct chipdata
{
    unsigned d7, d6, d5, d4, d3, d2, d1, d0, rscd, enwr, rwrd, protocol, tsetup, tclock, tread, tproc, thold;
};

union chip
{
    struct chipdata data;
    unsigned pins[11];
};

/* VARIABLES SHARED BETWEEN DIFFERENT METHODS */

/* current chip data */
union chip *curchip;
/* time of the last execution */
struct timespec ttime;
/* time to wait for the next execution */
uint32_t timing;
/* GPIO clear/set buffers */
uint32_t clr, set;


/* TINY GPIO METHODS */

void gpioSetMode(unsigned gpio, unsigned mode)
{
    int reg, shift;

    reg   =  gpio/10;
    shift = (gpio%10) * 3;

    gpioReg[reg] = (gpioReg[reg] & ~(7<<shift)) | (mode<<shift);
}

int gpioGetMode(unsigned gpio)
{
    int reg, shift;

    reg   =  gpio/10;
    shift = (gpio%10) * 3;

    return (*(gpioReg + reg) >> shift) & 7;
}

void gpioSetPullUpDown(unsigned gpio, unsigned pud)
{
    *(gpioReg + GPPUD) = pud;
    usleep(20);
    *(gpioReg + GPPUDCLK0 + PI_BANK) = PI_BIT;
    usleep(20);
    *(gpioReg + GPPUD) = 0;
    *(gpioReg + GPPUDCLK0 + PI_BANK) = 0;
}

int gpioRead(unsigned gpio)
{
    if ((*(gpioReg + GPLEV0 + PI_BANK) & PI_BIT) != 0) return 1;
    else return 0;
}

void gpioWrite(unsigned gpio, unsigned level)
{
    if (level == 0) *(gpioReg + GPCLR0 + PI_BANK) = PI_BIT;
    else *(gpioReg + GPSET0 + PI_BANK) = PI_BIT;
}

int gpioInitialise(void)
{
    int fd;

    fd = open("/dev/gpiomem", O_RDWR | O_SYNC) ;
    if (fd < 0)
    {
        fprintf(stderr, "Failed to open /dev/gpiomem\n");
        return -1;
    }
    gpioReg = (uint32_t *)mmap(NULL, 0xB4, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);

    if (gpioReg == MAP_FAILED)
    {
        fprintf(stderr, "Bad, mmap failed\n");
        return -1;
    }
    return 0;
}

/* INTERNAL METHODS */

#define WAIT() ({\
    ntime = ttime.tv_sec * (uint64_t)1000000000L + ttime.tv_nsec + timing;\
    clock_gettime(CLOCK_MONOTONIC,&ctime);\
    /* some of the code was delayed, before or after the last clock switch, so stretching clock for one timing value */\
    if (ctime.tv_sec * (uint64_t)1000000000L + ctime.tv_nsec >= ntime)\
    {\
        ttime = ctime;\
        ntime = ttime.tv_sec * (uint64_t)1000000000L + ttime.tv_nsec + timing;\
    }\
    while(1)\
    {\
        clock_gettime(CLOCK_MONOTONIC,&ctime);\
        if (ctime.tv_sec * (uint64_t)1000000000L + ctime.tv_nsec >= ntime) break;\
    }\
})

#define SET() ({\
    ttime.tv_nsec = ttime.tv_nsec + timing;\
    if(ttime.tv_nsec >= 1000000000L)\
    {\
        ttime.tv_nsec = ttime.tv_nsec - 1000000000L;\
        ttime.tv_sec = ttime.tv_sec + 1;\
    }\
})

/* read multiple data or a register */
/* clr/set must be set to command/data beforehand */
void readparallel(unsigned char *datapos, int datanum)
{
    int i, j, k;
    unsigned char value;
    uint32_t readings;
    uint32_t clk; /* bit for the clock line */
    int bpc; /* bits per cycle */
    struct timespec ctime;
    uint64_t ntime;
    bool otime;

    if(curchip->data.d0 == UNDEFINED) bpc=4;
    else bpc=8;

    /* the slave chip in read mode */
    if(curchip->data.protocol == 6800) set = set | (1 << curchip->data.rwrd);
    /* as late as possible so that the slave chip does not output */
    WAIT();
    *(gpioReg + GPCLR0) = clr;
    *(gpioReg + GPSET0) = set;
    SET();
    timing = curchip->data.tsetup;

    if(curchip->data.protocol == 6800) clk = 1 << curchip->data.enwr;
    if(curchip->data.protocol == 8080) clk = 1 << curchip->data.rwrd;

    for (i=0; i<datanum; i++)
    {
        value = 0;
        for (j=8/bpc; j>0; j--)
        {
            WAIT();
            if(curchip->data.protocol == 6800) *(gpioReg + GPSET0) = clk;
            if(curchip->data.protocol == 8080) *(gpioReg + GPCLR0) = clk;
            SET();
            timing = curchip->data.tread;

            WAIT();
            readings = *(gpioReg + GPLEV0);
            /* not refreshing time */
            timing = curchip->data.tclock;
            for (k=0; k<bpc; k++)
            {
                value = value << 1;
                if ((readings & (1 << curchip->pins[k])) > 0) value = (value | 0x01);
            }

            WAIT();
            if(curchip->data.protocol == 6800) *(gpioReg + GPCLR0) = clk;
            if(curchip->data.protocol == 8080) *(gpioReg + GPSET0) = clk;
            SET();
            if (j==1) timing = curchip->data.tproc;
            else timing = curchip->data.tclock;
            if (curchip->data.thold > timing) timing = curchip->data.thold;
        }
        datapos[i]=value;
    }

    clr = 0;
    set = 0;
    /* the chip in write mode */
    if(curchip->data.protocol == 6800) clr = clr | (1 << curchip->data.rwrd);
    /* as soon as possible so that the slave chip does not output */
    *(gpioReg + GPCLR0) = clr;
    *(gpioReg + GPSET0) = set;
}

/* write multiple data or a command */
/* clr/set must be set to command/data beforehand */
void writeparallel(unsigned char *datapos, int datanum)
{
    int reg, shift;
    uint32_t gpioBuf[3]; /* GPIO status buffer */
    int i, j, k;
    uint32_t clk; /* bit for the clock line */
    int bpc; /* bits per cycle */
    unsigned char datum; /* datum to be sent */
    struct timespec ctime;
    uint64_t ntime;
    bool otime;

    if(curchip->data.d0 == UNDEFINED) bpc=4;
    else bpc=8;

    /* the RPi data lines in write/output mode */
    gpioBuf[0] = gpioReg[0];
    gpioBuf[1] = gpioReg[1];
    gpioBuf[2] = gpioReg[2];
    for (i=0; i<bpc; i++)
    {
        reg   =  curchip->pins[i]/10;
        shift = (curchip->pins[i]%10) * 3;
        gpioBuf[reg] = (gpioBuf[reg] & ~(7<<shift)) | (PI_OUTPUT<<shift);
    }
    /* as late as possible so that the RPi does not output */
    WAIT();
    gpioReg[0] = gpioBuf[0];
    gpioReg[1] = gpioBuf[1];
    gpioReg[2] = gpioBuf[2];

    *(gpioReg + GPCLR0) = clr;
    *(gpioReg + GPSET0) = set;
    SET();
    timing = curchip->data.tsetup;

    clk = 1 << curchip->data.enwr;

    for (i=0; i<datanum; i++)
    {
        datum = datapos[i];
        for (j=8/bpc; j>0; j--)
            {
            clr = 0;
            set = 0;
            if(curchip->data.protocol == 6800) set = clk;
            if(curchip->data.protocol == 8080) clr = clk;
            for (k=0; k<bpc; k++)
            {
                if ((datum & 0x80) > 0) set = set | (1 << curchip->pins[k]);
                else clr = clr | (1 << curchip->pins[k]);
                datum = datum << 1;
            }

            WAIT();
            /* make sure that the clock line setting goes last */
            if(curchip->data.protocol == 6800)
            {
                *(gpioReg + GPCLR0) = clr;
                *(gpioReg + GPSET0) = set;
            }
            if(curchip->data.protocol == 8080)
            {
                *(gpioReg + GPSET0) = set;
                *(gpioReg + GPCLR0) = clr;
            }

            SET();
            timing = curchip->data.tclock;

            WAIT();
            if(curchip->data.protocol == 6800) *(gpioReg + GPCLR0) = clk;
            if(curchip->data.protocol == 8080) *(gpioReg + GPSET0) = clk;
            SET();
            if (j==1) timing = curchip->data.tproc;
            else timing = curchip->data.tclock;
        }
    }

    /* the RPi data pins in read/input mode */
    for (i=0; i<bpc; i++)
    {
        reg   =  curchip->pins[i]/10;
        shift = (curchip->pins[i]%10) * 3;
        gpioBuf[reg] = (gpioBuf[reg] & ~(7<<shift)) | (PI_INPUT<<shift);
    }
    /* as soon as possible so that the RPi does not output */
    gpioReg[0] = gpioBuf[0];
    gpioReg[1] = gpioBuf[1];
    gpioReg[2] = gpioBuf[2];
}

/* EXTERNAL METHODS */

/* gets: 8 data lines, RS/CD EN/WR RW/RD control lines, protocol, 5 wait times */
/* returns: the pointer to chip instance */
/* GPIO number out of range -> undefined line; D3/D2/D1/D0 undefined -> 4 bit communication; RWRD undefined -> write to chip only */
/* initialise communications */
union chip *initialise(int d7, int d6, int d5, int d4, int d3, int d2, int d1, int d0, int rscd, int enwr, int rwrd, int protocol, int tsetup, int tclock, int tread, int tproc, int thold)
{
    uint32_t gpioBuf[3]; /* GPIO status buffer */
    int i;
    int reg, shift;

    union chip *tempchip = malloc(sizeof(union chip));

    if (gpioInitialise() < 0) return(NULL);
    gpioBuf[0] = gpioReg[0];
    gpioBuf[1] = gpioReg[1];
    gpioBuf[2] = gpioReg[2];

    tempchip->data.d7 = (unsigned)d7;
    tempchip->data.d6 = (unsigned)d6;
    tempchip->data.d5 = (unsigned)d5;
    tempchip->data.d4 = (unsigned)d4;
    if((d3>27) || (d3<0)) tempchip->data.d3 = UNDEFINED;
    else tempchip->data.d3 = (unsigned)d3;
    if((d2>27) || (d2<0)) tempchip->data.d2 = UNDEFINED;
    else tempchip->data.d2 = (unsigned)d2;
    if((d1>27) || (d1<0)) tempchip->data.d1 = UNDEFINED;
    else tempchip->data.d1 = (unsigned)d1;
    if((d0>27) || (d0<0)) tempchip->data.d0 = UNDEFINED;
    else tempchip->data.d0 = (unsigned)d0;
    tempchip->data.rscd = (unsigned)rscd;
    tempchip->data.enwr = (unsigned)enwr;
    if((rwrd>27) || (rwrd<0)) tempchip->data.rwrd = UNDEFINED;
    else tempchip->data.rwrd = (unsigned)rwrd;
    tempchip->data.protocol = (unsigned)protocol;
    tempchip->data.tsetup = (unsigned)tsetup;
    tempchip->data.tclock = (unsigned)tclock;
    tempchip->data.tread = (unsigned)tread;
    tempchip->data.tproc = (unsigned)tproc;
    tempchip->data.thold = (unsigned)thold;

    /* chip by default in write mode */
    if((tempchip->data.protocol == 6800) && (tempchip->data.rwrd != UNDEFINED)) *(gpioReg + GPCLR0) = (1 << tempchip->data.rwrd);
    /* RPi control lines default states */
    if(tempchip->data.protocol == 6800) *(gpioReg + GPCLR0) = (1 << tempchip->data.enwr);
    if((tempchip->data.protocol == 8080) && (tempchip->data.rwrd != UNDEFINED)) *(gpioReg + GPSET0) = (1 << tempchip->data.rwrd);
    if(tempchip->data.protocol == 8080) *(gpioReg + GPSET0) = (1 << tempchip->data.enwr);

    /* RPi data lines by default in read/input mode */
    for (i=0; i<8; i++) if (tempchip->pins[i] != UNDEFINED)
    {
        reg   =  tempchip->pins[i]/10;
        shift = (tempchip->pins[i]%10) * 3;
        gpioBuf[reg] = (gpioBuf[reg] & ~(7<<shift)) | (PI_INPUT<<shift);
    }
    /* RPi control lines in write/output mode */
    for (i=8; i<11; i++) if (tempchip->pins[i] != UNDEFINED)
    {
        reg   =  tempchip->pins[i]/10;
        shift = (tempchip->pins[i]%10) * 3;
        gpioBuf[reg] = (gpioBuf[reg] & ~(7<<shift)) | (PI_OUTPUT<<shift);
    }
    gpioReg[0] = gpioBuf[0];
    gpioReg[1] = gpioBuf[1];
    gpioReg[2] = gpioBuf[2];

    clock_gettime(CLOCK_MONOTONIC,&ttime);
    timing = 0;
    return(tempchip);
}

/* gets: the pointer to chip instance */
/* deinitialise communications */
int deinitialise(union chip *tempchip)
{
    free(tempchip);
    return(0);
}

/* gets: the pointer to chip instance, the pointer to data array, the number of data to read */
/* read multiple data */
int readdata(union chip *tempchip, unsigned char *datapos, int datanum)
{
    curchip=tempchip;

    if (tempchip->data.rwrd == UNDEFINED) return(-1);

    clr = 0;
    set = 0;
    /* chip in data mode */
    if(curchip->data.protocol == 6800) set = set | (1 << curchip->data.rscd);
    if(curchip->data.protocol == 8080) clr = clr | (1 << curchip->data.rscd);

    readparallel(datapos, datanum);

    return(0);
}

/* gets: the pointer to chip instance */
/* returns: register value */
/* read register */
int readregister(union chip *tempchip)
{
    unsigned char datareg;

    curchip=tempchip;

    if (tempchip->data.rwrd == UNDEFINED) return(-1);

    clr = 0;
    set = 0;
    /* chip in command mode */
    if(curchip->data.protocol == 6800) clr = clr | (1 << curchip->data.rscd);
    if(curchip->data.protocol == 8080) set = set | (1 << curchip->data.rscd);

    readparallel(&datareg, 1);

    return((int)datareg);
}

/* gets: the pointer to chip instance, the pointer to data array, the number of data to write */
/* write multiple data */
void writedata(union chip *tempchip, unsigned char *datapos, int datanum)
{
    curchip=tempchip;

    clr = 0;
    set = 0;
    /* chip in data mode */
    if(curchip->data.protocol == 6800) set = set | (1 << curchip->data.rscd);
    if(curchip->data.protocol == 8080) clr = clr | (1 << curchip->data.rscd);

    writeparallel(datapos, datanum);
}

/* gets: the pointer to chip instance, command value */
/* write command */
void writecommand(union chip *tempchip, unsigned char datacom)
{
    curchip=tempchip;

    clr = 0;
    set = 0;
    /* chip in command mode */
    if(curchip->data.protocol == 6800) clr = clr | (1 << curchip->data.rscd);
    if(curchip->data.protocol == 8080) set = set | (1 << curchip->data.rscd);

    writeparallel(&datacom, 1);
}
