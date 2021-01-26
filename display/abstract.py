"""
This module is the abstract representation of a pixel matrix display.
"""
import abc
import time

import numpy as np


class AbstractDisplay(abc.ABC):
    def __init__(self, width, height, brightness, config):
        self._width = width
        self._height = height
        self._brightness = brightness
        self._config = config

        self._num_pixels = self._height * self._width
        self._buffer = np.zeros((self._height, self._width, 3),
                                dtype=np.uint8)  # 3 for red, green, blue

    @property
    def buffer(self):
        """The buffer contains the rgb data to be displayed."""
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        if isinstance(value, np.ndarray):
            if self._buffer.shape == value.shape:
                # del self._buffer
                self._buffer = value

    def clear_buffer(self):
        # del self._buffer
        self._buffer = np.zeros_like(self._buffer)

    @abc.abstractmethod
    def show(self, gamma=False):
        """Display the contents of buffer on display. Gamma correction can be
        toggled."""

    @abc.abstractmethod
    def set_brightness(self, brightness):
        """Set the brightness 0 to 100 value"""

    def __set_pixel_at_index(self, index, color):
        """Set pixel at logical position index (from top left counted row-wise)
        to color, which must be a rgb values tuple"""
        if (index < 0) or (index >= self._num_pixels):
            return
        index *= 3
        self._buffer.put([index, index+1, index+2], color)

    def __set_pixel_at_coord(self, x, y, color):
        """Set pixel at coordinate x,y to color, which must be a rgb values
        tuple"""
        if (x < 0) or (x >= self._width) or (y < 0) or (y >= self._height):
            return
        self._buffer[y, x] = color

    def __set_buffer_with_flat_values(self, rgb_values):
        try:
            rgb_values = np.array(rgb_values, dtype=np.uint8)
            rgb_values.resize((self._num_pixels * 3,))
            rgb_values = rgb_values.reshape(self._height, self._width, 3)
        except Exception:
            return
        # del self._buffer
        self._buffer = rgb_values

    def __create_test_pattern(self):
        # written for 16x16 displays
        self.clear_buffer()
        values = np.arange(0, 256, int(256/(self._width-1)), dtype=np.uint8)
        # self._buffer[0:self._width/4*1, :, 0:3] = \
        #     self._buffer[0:4, :, 0:3] + \
        #     np.resize(values, (3, self._width)).transpose()
        self._buffer[0:self._width/4*1, :, 0:3] += \
            np.resize(values, (3, self._width)).transpose()
        self._buffer[self._width/4*1:self._width/4*2, :, 0] += values
        self._buffer[self._width/4*2:self._width/4*3, :, 1] += values
        self._buffer[self._width/4*3:self._width/4*4, :, 2] += values

    def __run_benchmark(self, gamma=False):
        total = 0
        repeat = self._num_pixels * 10
        for i in range(repeat):
            start = time.time()
            self.__set_pixel_at_index(i % self._num_pixels, (255, 255, 255))
            self.show(gamma)
            self.clear_buffer()
            end = time.time()
            diff = end - start
            total = total + diff
        print("{:.2f}s for {} iterations. {:d} refreshs per second"
              "".format(total, repeat, int(repeat/total)))
        self.clear_buffer()
        self.show()
