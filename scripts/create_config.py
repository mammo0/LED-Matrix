#!/usr/bin/env python
import argparse
from configparser import ConfigParser
from pathlib import Path
import sys


CONFIG_TEXT = """[MAIN]
# The display defines where the animations should be showed.
# There are two possible values here:
#     - 'APA102'   [Default]
#       The actual LED hardware addressed via SPI.
#     - 'COMPUTER'
#       This is for developing on a PC. It opens a virtual LED matrix via 'pygame'.
Hardware = APA102

# Set the number of LEDs for width and height of your matrix
DisplayWidth = 15
DisplayHeight = 12

# (De-)Activate the server interfaces that control the matrix.
# Available servers:
#     - HttpServer [Default: true]: TCP 8080
#     - RestServer [Default: true]: TCP 8081
#     - TPM2NetServer [Default: false]: UDP 65506
HttpServer = true
RestServer = true
TPM2NetServer = false


[DEFAULTANIMATION]
# Default animation that is displayed on start/idle
# The value is equal to the name of the Python module in the 'animation' directory.
# Default start animation is 'clock'.
Animation = clock

# The possible variants can be checked in the Python module of the corresponding animation.
# Default for animation 'clock' is variant 'digital'.
Variant = digital

# Sometimes a variant needs a parameter.
# If multiple parameters are needed, a JSON-like dictionary can be entered after the equal sign.
# Multiline is supported but every line must have an indention.
Parameter = {
    "background_color": [0, 0, 0],
    "divider_color": [255, 255, 255],
    "hour_color": [255, 0, 0],
    "minute_color": [255, 255, 255]
    }

# This integer defines, how many times an animation gets repeated.
#     0: no repeat [Default]
#    -1: forever
# x > 0: x-times
Repeat = 0


[APA102]
# This section contains variables that describe how the LED matrix is built up.

# Specify the color type of the used LEDs:
#     - '1': RGB
#     - '2': RBG
#     - '3': GRB
#     - '4': GBR
#     - '5': BGR [Default]
#     - '6': BRG
ColorType = 5

# Specify how the LED strip is wired to form a matrix:
#     - '1': line by line
#     - '2': zig zag      [Default]
WireMode = 2

# Specify how the matrix dimensions (form [MAIN] section) should be interpreted:
#     - '1': horizontally [Default]
#     - '2': vertically
Orientation = 1

# The position of the first controlled LED on the matrix:
#     - '1': top left     [Default]
#     - '2': top right
#     - '3': bottom left
#     - '4': bottom right
Origin = 1


[COMPUTER]
# This sections variables for the computer display.

# Number of pixels that defines the space between single (virtual) LEDs.
Margin = 5

# Size of the square that represents a (virtual) LED on the matrix.
LEDSize = 30
"""


if __name__ == '__main__':
    # cli parser
    parser = argparse.ArgumentParser(description="Create or Update the configuration file.")
    parser.add_argument("CONFIG_FILE_PATH", type=Path,
                        help="The path of the configuration file.")

    # get config path
    args = parser.parse_args(sys.argv[1:])
    config_file_path = args.CONFIG_FILE_PATH

    if config_file_path.exists() and not config_file_path.is_file():
        raise ValueError("'%s' is not the path of a file!" % str(config_file_path))
    elif config_file_path.exists() and config_file_path.is_file():
        # update the configuration file
        print("The configuration file '%s' already exists." % str(config_file_path))
        print("Updating it...")

        # read the old (existing) config file
        old_config = ConfigParser()
        old_config.optionxform = lambda option: option
        with open(config_file_path, "r") as f:
            old_config.read_file(f)

        # load the new configuration
        new_config = ConfigParser(delimiters='=', comment_prefixes='•', allow_no_value=True)
        new_config.optionxform = lambda option: option
        new_config.read_string(CONFIG_TEXT)

        # use old values for the new configuration
        for section in old_config.sections():
            if new_config.has_section(section):
                for option in old_config.options(section):
                    if new_config.has_option(section, option):
                        new_config.set(section, option, old_config.get(section, option))

        # write the new configuration to file
        with open(config_file_path, "w") as f:
            new_config.write(f)
    else:
        # create the configuration file
        config = ConfigParser(delimiters='=', comment_prefixes='•', allow_no_value=True)
        config.optionxform = lambda option: option
        config.read_string(CONFIG_TEXT)
        with open(config_file_path, "w+") as f:
            config.write(f)
        print("The configuration file '%s' was created." % str(config_file_path))
