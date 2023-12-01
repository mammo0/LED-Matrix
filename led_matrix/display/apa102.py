"""
This module implements a display consisting of APA102 leds.
"""
# the following works only on linux
import sys

if sys.platform == "linux":
    import math
    from collections.abc import Iterable
    from typing import Final

    import numpy as np
    from numpy.typing import NDArray
    from spidev import SpiDev

    from led_matrix.config.settings import Settings
    from led_matrix.config.types import (LEDColorType, LEDOrientation,
                                         LEDOrigin, LEDWireMode)
    from led_matrix.display.abstract import AbstractDisplay


    SPI_MAX_SPEED_HZ: Final[int] = 16000000  # 500000 is library default as it seems
    MAX_BRIGHTNESS: Final[int] = 31
    DEFAULT_GAMMA: Final[float] = 2.22


    class Apa102(AbstractDisplay):
        def __init__(self, config: Settings) -> None:
            super().__init__(config=config)

            # init SPI interface
            self.__spi: SpiDev = SpiDev()
            self.__spi.open(0, 1)
            self.__spi.max_speed_hz = SPI_MAX_SPEED_HZ

            # setup hardware and wiring related parameters
            self.__width: int = config.main.display_width
            self.__height: int = config.main.display_height
            self.__color_type: LEDColorType = config.apa102.color_type
            self.__wire_mode: LEDWireMode = config.apa102.wire_mode
            self.__origin: LEDOrigin = config.apa102.origin
            self.__orientation: LEDOrientation = config.apa102.orientation

            # setup apa102 protocol stuff
            self.__start_frame: Final[list[int]] = [0] * 4
            # end frame is >= (n/2) bits of 1, where n is the number of LEDs
            self.__end_frame: Final[list[int]] = [0xff] * ((config.main.num_of_pixels + 15) // (2 * 8))
            # each frame starts with 111 and 5 bits that set the brightness
            self.__led_frame_empty_start_byte: Final[int] = 0b11100000
            self.__led_frame_start_array: NDArray[np.uint8] = np.full(
                shape=(self.__height, self.__width, 1),
                # default full brightness (all 8 bits set)
                fill_value=0b11111111,
                dtype=np.uint8
            )

            # setup datastructures for fast lookup of led
            # led index for given coordinate
            self.__pixel_coord_to_led_index: NDArray[np.int_]
            self.__virtual_to_physical_byte_indices: NDArray[np.int_]
            (
                self.__pixel_coord_to_led_index,
                self.__virtual_to_physical_byte_indices
            ) = self.__create_pixel_to_led_index_datastructures()

            # brightness offset
            self.__brightness_ceiling_offset: float = 0.

            # create gamma correction values
            self.__gamma8 = self.__get_gamma8_array(DEFAULT_GAMMA)

            self.show()

        @staticmethod
        def __get_gamma8_array(gamma) -> NDArray[np.uint8]:
            gamma8: NDArray[np.uint8] = np.zeros(256, dtype=np.uint8)

            i: NDArray[np.uint8]
            for i in np.arange(256, dtype=np.uint8):
                gamma8[i] = (255 * ((i/255) ** gamma) + 0.5).astype(np.uint8)

            return gamma8

        def __create_pixel_to_led_index_datastructures(self) -> tuple[NDArray[np.int_], NDArray[np.int_]]:
            pixel_coord_to_led_index: NDArray[np.int_] = np.zeros((self.__height, self.__width),
                                                                  dtype=np.int_)
            virtual_to_physical_byte_indices: NDArray[np.int_] = np.zeros((self.__height, self.__width, 4),
                                                                          dtype=np.int_)

            outer: int
            inner: int
            outer, inner = (
                (self.__height, self.__width) if
                    self.__orientation == LEDOrientation.HORIZONTALLY
                else
                    (self.__width, self.__height)
            )
            current_outer_count: int = 0
            outer_range: Iterable[int] = range(outer)

            if (
                (self.__orientation == LEDOrientation.HORIZONTALLY and
                    self.__origin in (LEDOrigin.BOTTOM_LEFT, LEDOrigin.BOTTOM_RIGHT))
                or
                (self.__orientation == LEDOrientation.VERTICALLY and
                    self.__origin in (LEDOrigin.TOP_RIGHT, LEDOrigin.BOTTOM_RIGHT))
            ):
                outer_range = reversed(outer_range)

            i: int
            for i in outer_range:
                current_inner_count: int = 0

                j: int
                for j in range(inner):
                    mod: int = (0 if self.__orientation == LEDOrientation.HORIZONTALLY and
                                    ((self.__origin == LEDOrigin.BOTTOM_LEFT and
                                        outer % 2 == 0) or
                                    (self.__origin == LEDOrigin.BOTTOM_RIGHT and
                                        outer % 2 == 1) or
                                    self.__origin == LEDOrigin.TOP_RIGHT)
                                or
                                    self.__orientation == LEDOrientation.VERTICALLY and
                                    ((self.__origin == LEDOrigin.TOP_RIGHT and
                                        outer % 2 == 0) or
                                    (self.__origin == LEDOrigin.BOTTOM_RIGHT and
                                        outer % 2 == 1) or
                                    self.__origin == LEDOrigin.BOTTOM_LEFT)
                                else 1)

                    if (
                        (self.__wire_mode == LEDWireMode.ZIG_ZAG and i % 2 == mod)
                        or
                        (self.__wire_mode == LEDWireMode.LINE_BY_LINE and (
                                (self.__orientation == LEDOrientation.HORIZONTALLY and
                                    self.__origin in (LEDOrigin.BOTTOM_RIGHT, LEDOrigin.TOP_RIGHT))
                                or
                                (self.__orientation == LEDOrientation.VERTICALLY and
                                    self.__origin in (LEDOrigin.BOTTOM_LEFT, LEDOrigin.BOTTOM_RIGHT))
                            )
                        )
                    ):
                        j = (inner - 1) - current_inner_count

                    led_index: int = j + current_outer_count * inner
                    coordinate: tuple[int, int] = (
                        (i, current_inner_count) if
                            self.__orientation == LEDOrientation.HORIZONTALLY
                        else
                            (current_inner_count, i)
                    )
                    pixel_coord_to_led_index[coordinate] = led_index

                    current_inner_count += 1
                current_outer_count += 1

            red: int
            green: int
            blue: int
            if self.__color_type == LEDColorType.RGB:
                red, green, blue = 1, 2, 3
            elif self.__color_type == LEDColorType.RBG:
                red, green, blue = 1, 3, 2
            elif self.__color_type == LEDColorType.GRB:
                red, green, blue = 2, 1, 3
            elif self.__color_type == LEDColorType.GBR:
                red, green, blue = 3, 1, 2
            elif self.__color_type == LEDColorType.BGR:
                red, green, blue = 3, 2, 1
            # only LEDColorType.BRG left
            else:
                red, green, blue = 2, 3, 1

            pixel_index: int
            for pixel_index in range(self._config.main.num_of_pixels):
                # for each pixel in buffer
                # calulate byte indices of pixel
                pixel_index_spread: int = pixel_index * 4  # room for byte led,r,g,b
                pixel_bytes_indices: list[int] = [
                    pixel_index_spread,
                    pixel_index_spread + red,
                    pixel_index_spread + green,
                    pixel_index_spread + blue
                ]

                # get coordinate of ith pixel
                pixel_row: int = pixel_index // self.__width
                pixel_col: int = pixel_index - pixel_row * self.__width

                # get led index of led at pixel coordinate
                led_index: int = pixel_coord_to_led_index[(pixel_row, pixel_col)]

                # get coordinate of ith led
                led_row: int = led_index // self.__width
                led_col: int = led_index - led_row * self.__width

                # set the transformation matrix accordingly
                virtual_to_physical_byte_indices[(led_row, led_col)] = pixel_bytes_indices

            return pixel_coord_to_led_index, virtual_to_physical_byte_indices

        def __str__(self) -> str:
            header = (
                f"APA102-matrix configuration: width: {self.__width} height: {self.__height} "
                f"colortype: {self.__color_type} wiremode: {self.__wire_mode} "
                f"origin: {self.__origin} orientation {self.__orientation}\n"
            )

            ret: str = header + "-" * len(header) + "\n"
            ret += '\t' + '\t'.join(map(str, list(range(self.__width)))) + "\n"

            i: int
            for i in range(self.__height):
                ret += f"{i}\t"

                j: int
                for j in range(self.__width):
                    ret += f"{self.__pixel_coord_to_led_index[i, j]}\t"

                ret += "\n"

            return ret

        def __build_apa102_frame(self) -> NDArray[np.uint8]:
            # if there is a brightness offset,
            # lower the color values proportionately
            led_frame_with_brightness: NDArray[np.uint8]
            if self.__brightness_ceiling_offset > 0:
                led_frame_with_brightness = (
                    # current value   -
                    self.frame_buffer - \
                    #       (one brightness step of the current value   * brightness offset in percent    )
                    np.ceil(((self.frame_buffer / (MAX_BRIGHTNESS + 1)) * self.__brightness_ceiling_offset))
                ).astype(np.uint8)
            else:
                led_frame_with_brightness: NDArray[np.uint8] = self.frame_buffer

            return np.concatenate((self.__led_frame_start_array, led_frame_with_brightness), axis=2)

        def __gamma_correct_buffer(self) -> None:
            x: tuple[NDArray[np.uint8], ...]
            for x in np.nditer(self.frame_buffer,
                               op_flags=[['readwrite']],
                               flags=['external_loop', 'buffered'],
                               order='F'):
                x[...] = self.__gamma8[x]  # type: ignore

        def set_brightness(self, brightness: int) -> None:
            # set the brightness level for the LEDs
            logarithmic_percentage: float = (math.pow(10, (brightness / 100)) - 1) / 9
            abs_brightness: float = logarithmic_percentage * MAX_BRIGHTNESS

            # this value is used for the in the start byte of the LED array
            led_brightness: int = math.ceil(abs_brightness)

            # this value represents the offset that is lost due to ceiling the brightness value
            # 1 < self.__brightness_ceiling_offset <= 0
            self.__brightness_ceiling_offset = led_brightness - abs_brightness

            # set LED frame start byte according to the brightness
            self.__led_frame_start_array &= (
                (led_brightness & ~self.__led_frame_empty_start_byte) | self.__led_frame_empty_start_byte
            )

        def show(self, gamma: bool=False) -> None:
            if gamma:
                self.__gamma_correct_buffer()

            apa102_led_frames: NDArray[np.uint8] = self.__build_apa102_frame()
            reindexed_frames: NDArray[np.uint8] = apa102_led_frames.take(self.__virtual_to_physical_byte_indices)

            to_send: list[int] = (
                self.__start_frame +
                reindexed_frames.flatten().tolist() +
                self.__end_frame
            )
            self.__spi.writebytes(to_send)
