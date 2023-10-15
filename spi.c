/*
   Marko Pinteric 2020
   GPIO communication based on Tiny GPIO Access on http://abyz.me.uk/rpi/pigpio/examples.html

   Create shared object with: gcc -o spi.so -shared -fPIC spi.c
*/

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <fcntl.h>
#include <stdbool.h> 
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>

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
static volatile uint32_t  *gpioReg = MAP_FAILED;

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

/* values for pull-ups/downs off, pull-down && pull-up */

#define PI_PUD_OFF  0
#define PI_PUD_DOWN 1
#define PI_PUD_UP   2

/* LOCAL VARIABLES */

int fd_spi;
struct spi_ioc_transfer spi;

struct chip
{
   unsigned sda;
   unsigned scl;
   unsigned ldac;
   unsigned address;
   unsigned bus;
};

/* communication initialised */
bool init_gpio=false, init_spi=false;

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
   int fd_gpio;

   fd_gpio = open("/dev/gpiomem", O_RDWR | O_SYNC) ;
   if (fd_gpio < 0)
   {
      fprintf(stderr, "failed to open /dev/gpiomem\n");
      return -1;
   }
   gpioReg = (uint32_t *)mmap(NULL, 0xB4, PROT_READ|PROT_WRITE, MAP_SHARED, fd_gpio, 0);
   close(fd_gpio);

   if (gpioReg == MAP_FAILED)
   {
      fprintf(stderr, "Bad, mmap failed\n");
      return -1;
   }
   return 0;
}


/* SPI METHODS */

/* initialise communications */
/* parameters: SPI bus number, frequency */
int spiInitialise(int dev, uint32_t frequency)
{
   char filename[20];

   snprintf(filename, 20, "/dev/spidev%d.0", dev);
   fd_spi = open(filename, O_RDWR);
   if (fd_spi < 0) fprintf(stderr, "Failed to open the spi%d bus", dev);

   spi.delay_usecs = 0;
   spi.speed_hz = frequency;
   spi.bits_per_word = 8;
   return(fd_spi);
}

/* write to SPI bus */
void spiWrite(uint8_t data[], int len)
{
  spi.tx_buf =(unsigned long)data;
  spi.rx_buf =(unsigned long)NULL;
  spi.len = len;
  ioctl(fd_spi, SPI_IOC_MESSAGE(1), &spi);
}
