# LED-Matrix

This project is based on the work of [stahlfabrik](https://github.com/stahlfabrik)'s https://github.com/stahlfabrik/RibbaPi.

And the additions made by [ElectiveRob](https://github.com/ElectiveRob).

Many thanks to you two.



## What is this project about?
This project brings an old study project of mine back to life. Together with some collegues I built a simple LED matarix with APA102 LEDs that are controlled by a Raspberry Pi 1.

After some years of inactivity I had some time to re-activate this project and found the repository of [stahlfabrik](https://github.com/stahlfabrik), who has also built a LED matrix with similar hardware. So I continued his work.

If you have also built such an LED matrix, this project may help you to do some cool stuff with it.



## Preparations
This project is designed to be used in conjunction with an Alpine Linux installation on a Raspberry Pi.

To install Alpine Linux on a Raspberry Pi please stick to the official documentation: https://wiki.alpinelinux.org/wiki/Raspberry_Pi


#### Install dependencies
After Alpine Linux is running on your Raspberry Pi, install these dependencies:

```shell
apk add git \
        make \
        python3 \
        py3-numpy \
        py3-pillow \
        py3-bottle \
        py3-six
```


#### Build the Python virtual environment (On local PC)
This project uses Pipenv to manage it's dependencies. Unfortunately some of these dependencies require building of external libraries. Normally that wouldn't be a problem. But running Alpine Linux in diskless mode on a Raspberry Pi 1 means, that you have only a few 100MB of available 'disk' space. This is not enough to build all dependencies.

As a workaround you can build these dependencies on your local PC with the help of Docker. Therefore this repository contains a `Dockerfile` that creates and builds the virual Python environment with all dependencies.

**A pre-packed archive containing the virtual environment can be downloaded from the [Releases page](https://github.com/mammo0/LED-Matrix/releases).** This archive is built by a GitHub Actions workflow.

**Alternatively** you can also build it on your local PC by running the following `make` target:

```shell
make build-alpine-venv
```

After that you find an `tar`-archive in the `resources` directory of this repository, that contains the virtual environment for your Alpine Linux installation. This archive is needed in step **4** of the **Installation** section.



## Installation (On Raspberry Pi)
1. Enable write support on your SD card partition:
```shell
mount -o remount,rw /media/<sd_card>
```
You get the correct mount location form the `LBU_MEDIA` parameter in the `/etc/lbu/lbu.conf` file.

2. Enter the directory of the mount point:
```shell
cd /media/<sd_card>
```

3. Clone this repository:
```shell
git clone https://github.com/mammo0/LED-Matrix.git
cd LED-Matrix
```

4. Copy the `tar`-archive containing the virtual environment from your local PC to the `resources` directory on the Raspberry Pi, e.g. by using `scp`.

5. Install the virtual environment:
```shell
make install-alpine-venv
```

6. Generate the `config.ini` file:
```shell
make config
```

7. *(Optional)* Edit the `config.ini` file to your needs.

8. Test the installation:
```shell
make run
```
If everything runs without errors and you see the default animation (clock) on your LED matrix, stop the execution with `Ctrl-C`. *If there are errors, feel free to open an issue with an detailed error report on GitHub.*

9. Disable write support on the SD card again:
```shell
mount -o remount,ro /media/<sd_card>
```

10. Add this project to the autostart of Alpine Linux:
```shell
make install
```


## Usage
If everything went well, there should be a web interface available under:

```
http://<ip-of-raspberry-pi>:<port-from-config.ini>
```

From there you can manage most of the settings of the LED matrix. And you can start/stop and schedule animations.
