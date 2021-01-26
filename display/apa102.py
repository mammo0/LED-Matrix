"""
This module implements a display consisting of APA102 leds.
"""
from enum import Enum

import spidev

from common.config import Config
from display.abstract import AbstractDisplay
import numpy as np


class ColorType(Enum):
    rgb = 1
    rbg = 2
    grb = 3
    gbr = 4
    bgr = 5
    brg = 6


class WireMode(Enum):
    line_by_line = 1
    zig_zag = 2


class Orientation(Enum):
    horizontally = 1
    vertically = 2


class Origin(Enum):
    top_left = 1
    top_right = 2
    bottom_left = 3
    bottom_right = 4


SPI_MAX_SPEED_HZ = 16000000  # 500000 is library default as it seems
MAX_BRIGHTNESS = 31
DEFAULT_GAMMA = 2.22


class Apa102(AbstractDisplay):
    def __init__(self, width, height, brightness, config):
        super().__init__(width, height, brightness, config)

        self.set_brightness(brightness)

        # init SPI interface
        self.__spi = spidev.SpiDev()
        self.__spi.open(0, 1)
        self.__spi.max_speed_hz = SPI_MAX_SPEED_HZ

        # setup hardware and wiring related parameters
        self.__color_type = ColorType(self._config.get(Config.APA102.ColorType))
        self.__wire_mode = WireMode(self._config.get(Config.APA102.WireMode))
        self.__origin = Origin(self._config.get(Config.APA102.Origin))
        self.__orientation = Orientation(self._config.get(Config.APA102.Orientation))

        # setup apa102 protocol stuff
        self.__start_frame = [0] * 4
        # end frame is >= (n/2) bits of 1, where n is the number of LEDs
        self.__end_frame = [0xff] * ((self._num_pixels + 15) // (2 * 8))
        self.__led_frame_start = 0b11100000

        # setup datastructures for fast lookup of led
        # led index for given coordinate
        (self.__pixel_coord_to_led_index,
         self.__virtual_to_physical_byte_indices) = \
            self.__create_pixel_to_led_index_datastructures()

        # create gamma correction values
        gamma = DEFAULT_GAMMA
        self.__gamma8 = self.__get_gamma8_array(gamma)

        self.show()

    @staticmethod
    def __get_gamma8_array(gamma):
        gamma8 = np.zeros((256,), dtype=np.uint8)
        for i in np.arange(256, dtype=np.uint8):
            gamma8[i] = (255 * ((i/255)**gamma) + 0.5).astype(np.uint8)
        return gamma8

    def __create_pixel_to_led_index_datastructures(self):
        pixel_coord_to_led_index = np.zeros((self._height, self._width),
                                            dtype=np.int)
        virtual_to_physical_byte_indices = np.zeros((self._height,
                                                     self._width,
                                                     4), dtype=np.int)

        outer, inner = (self._height, self._width) if \
            self.__orientation == Orientation.horizontally else \
                       (self._width, self._height)
        current_outer_count = 0
        outer_range = range(outer)
        if (self.__orientation == Orientation.horizontally and
           (self.__origin == Origin.bottom_left or
                self.__origin == Origin.bottom_right)) \
                or \
           (self.__orientation == Orientation.vertically and
           (self.__origin == Origin.top_right or
                self.__origin == Origin.bottom_right)):
            outer_range = reversed(outer_range)
        for i in outer_range:
            current_inner_count = 0
            for j in range(inner):
                mod = (0 if self.__orientation == Orientation.horizontally and
                       ((self.__origin == Origin.bottom_left and
                        outer % 2 == 0) or
                        (self.__origin == Origin.bottom_right and
                        outer % 2 == 1) or
                        self.__origin == Origin.top_right)
                       or
                       self.__orientation == Orientation.vertically and
                       ((self.__origin == Origin.top_right and
                        outer % 2 == 0) or
                        (self.__origin == Origin.bottom_right and
                         outer % 2 == 1) or
                        self.__origin == Origin.bottom_left)
                       else 1)
                if (self.__wire_mode == WireMode.zig_zag and i % 2 == mod) or \
                   (self.__wire_mode == WireMode.line_by_line and
                       ((self.__orientation == Orientation.horizontally and
                           (self.__origin == Origin.bottom_right or
                            self.__origin == Origin.top_right))
                        or
                        (self.__orientation == Orientation.vertically and
                            (self.__origin == Origin.bottom_left or
                             self.__origin == Origin.bottom_right)))):
                    j = (inner - 1) - current_inner_count
                led_index = j + current_outer_count * inner
                coordinate = (i, current_inner_count) if \
                    self.__orientation == Orientation.horizontally else \
                             (current_inner_count, i)
                pixel_coord_to_led_index[coordinate] = led_index
                current_inner_count += 1
            current_outer_count += 1

        if self.__color_type == ColorType.rgb:
            red, green, blue = 1, 2, 3
        elif self.__color_type == ColorType.rbg:
            red, green, blue = 1, 3, 2
        elif self.__color_type == ColorType.grb:
            red, green, blue = 2, 1, 3
        elif self.__color_type == ColorType.gbr:
            red, green, blue = 3, 1, 2
        elif self.__color_type == ColorType.bgr:
            red, green, blue = 3, 2, 1
        elif self.__color_type == ColorType.brg:
            red, green, blue = 2, 3, 1

        for pixel_index in range(self._height * self._width):
                # for each pixel in buffer
                # calulate byte indices of pixel
                pixel_index_spread = pixel_index * 4  # room for byte led,r,g,b
                pixel_bytes_indices = [pixel_index_spread,
                                       pixel_index_spread + red,
                                       pixel_index_spread + green,
                                       pixel_index_spread + blue]

                # get coordinate of ith pixel
                pixel_row = pixel_index // self._width
                pixel_col = pixel_index - pixel_row * self._width

                # get led index of led at pixel coordinate
                led_index = pixel_coord_to_led_index[(pixel_row, pixel_col)]

                # get coordinate of ith led
                led_row = led_index // self._width
                led_col = led_index - led_row * self._width

                # set the transformation matrix accordingly
                virtual_to_physical_byte_indices[(led_row, led_col)] = \
                    pixel_bytes_indices

        return pixel_coord_to_led_index, virtual_to_physical_byte_indices

    def __str__(self):
        header = "APA102-matrix configuration: width: {} height: {} "\
                 "colortype: {} wiremode: {} origin: {} orientation {}\n"\
                 "".format(self._width,
                           self._height,
                           self.__color_type,
                           self.__wire_mode,
                           self.__origin,
                           self.__orientation)
        ret = header + "-"*len(header) + "\n"
        ret += '\t' + '\t'.join(map(str, list(range(self._width)))) + "\n"
        for i in range(self._height):
            ret += "{}\t".format(i)
            for j in range(self._width):
                ret += "{}\t".format(self.__pixel_coord_to_led_index[i, j])
            ret += "\n"
        return ret

    def __get_brightness_array(self):
        led_frame_first_byte = \
            (self._brightness & ~self.__led_frame_start) | self.__led_frame_start
        ret = np.array([led_frame_first_byte] * self._num_pixels,
                       dtype=np.uint8)
        return ret.reshape((self._height, self._width, 1))

    def __gamma_correct_buffer(self):
        for x in np.nditer(self._buffer,
                           op_flags=['readwrite'],
                           flags=['external_loop', 'buffered'],
                           order='F'):
            x[...] = self.__gamma8[x]

    def set_brightness(self, brightness):
        # set the brightness level for the LEDs
        self._brightness = int((brightness / 100) * MAX_BRIGHTNESS)

    def show(self, gamma=False):
        if gamma:
            self.__gamma_correct_buffer()
        apa102_led_frames = np.concatenate((self.__get_brightness_array(),
                                            self._buffer), axis=2)
        reindexed_frames = apa102_led_frames.take(
                                       self.__virtual_to_physical_byte_indices)
        to_send = \
            self.__start_frame \
            + reindexed_frames.flatten().tolist() \
            + self.__end_frame
        self.__spi.writebytes(to_send)
