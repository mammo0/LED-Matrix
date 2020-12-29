#!/bin/sh

read -d '' CONFIG_TEXT << EOT
[MAIN]
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


[APA102]
# This section contains variables that describe how the LED matrix is built up.

# Specify the color type of the used LEDs.
# Possible values are:
#     - '1': RGB
#     - '2': RBG
#     - '3': GRB
#     - '4': GBR
#     - '5': BGR [Default]
#     - '6': BRG
ColorType = 5

# Specify how the LED strip is wired to form a matrix.
# Possible values are:
#     - '1': line by line
#     - '2': zig zag      [Default]
WireMode = 2

# Specify how the matrix dimensions (form [MAIN] section) should be interpreted.
# Possible values are:
#     - '1': horizontally [Default]
#     - '2': vertically
Orientation = 1

# The position of the first controlled LED on the matrix.
# Possible values are:
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

EOT


if [ -z "$1" ]; then
    echo "Usage: $(basename $0) CONFIG_FILE_PATH"
    exit 1
fi
CONFIG_FILE="$1"


if [ -f "$CONFIG_FILE" ]; then
    echo "The configuration file '$CONFIG_FILE' already exists."
    echo "Nothing has changed!"
else
    echo "$CONFIG_TEXT" > "$CONFIG_FILE"
    echo "The configuration file '$CONFIG_FILE' was created."
fi
