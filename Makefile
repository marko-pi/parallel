
all: compile

install:
	gcc -o libparallel.so -shared -fPIC parallel.c
	gcc -o libspi.so -shared -fPIC spi.c
	sudo mv libparallel.so /usr/local/lib
	sudo mv libspi.so /usr/local/lib
	sudo ldconfig

uninstall:
	sudo rm -f /usr/local/lib/libparallel.so
	sudo rm -f /usr/local/lib/libspi.so
	sudo ldconfig

compile:
	gcc -o parallel.so -shared -fPIC parallel.c
	gcc -o spi.so -shared -fPIC spi.c

clean:
	rm -f parallel.so
	rm -f spi.so
