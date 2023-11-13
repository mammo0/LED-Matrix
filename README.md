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


#### Build Alpine package
**A ready-to-use package can be downloaded from the [Releases page](https://github.com/mammo0/LED-Matrix/releases).** This package is built by a GitHub Actions workflow.

**Alternatively** you can also build it on your local PC by running the following `make` target:

```shell
make build-alpine-package
```

*NOTE: This requires a working Docker installation.*

After that you find the `apk`-package in the `dist` directory of this repository. This package is needed in step **3** of the **Installation** section.



## Installation
1. Enable write support on your SD card partition:
```shell
mount -o remount,rw /media/<sd_card>
```
You get the correct mount location form the `LBU_MEDIA` parameter in the `/etc/lbu/lbu.conf` file.

2. Enter the directory of the mount point:
```shell
cd /media/<sd_card>
```

3. Copy the `apk`-package (that was built or downloaded previously) from your local PC to the current directory on the Raspberry Pi, e.g. by using `scp`.

4. Install the package:
```shell
apk add --allow-untrusted <package_name>.apk
```

5. Edit the `/etc/led-matrix.ini` file to your needs. The available settings are documented in the file. **Don't forget step 9 after every change!**

6. Test the installation:
```shell
led-matrix --config-file /etc/led-matrix.ini
```
If everything runs without errors, stop the execution with `Ctrl-C`. *If there are errors, feel free to open an issue with an detailed error report on GitHub.*

7. Disable write support on the SD card again:
```shell
mount -o remount,ro /media/<sd_card>
```

8. Add this project to the autostart of Alpine Linux:
```shell
rc-update add led-matrix
```

9. Commit any change to the file system:
```shell
lbu commit -d
```


## Usage
If everything went well, there should be a web interface available under:

```
http://<ip-of-raspberry-pi>:<port-from-config.ini>
```

From there you can manage most of the settings of the LED matrix. And you can start/stop and schedule animations.
