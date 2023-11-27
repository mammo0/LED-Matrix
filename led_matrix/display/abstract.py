"""
This module is the abstract representation of a pixel matrix display.
"""
from abc import ABC, abstractmethod
from typing import final

import numpy as np
from numpy.typing import NDArray

from led_matrix.config.settings import Settings


class AbstractDisplay(ABC):
    def __init__(self, config: Settings) -> None:
        self.__config: Settings = config

        self.__buffer: NDArray[np.uint8] = np.zeros(
            (config.main.display_height, config.main.display_width, 3),  # 3 for red, green, blue
            dtype=np.uint8
        )

        self.__display_brightness: float
        self.set_brightness(config.main.brightness)

    @property
    def frame_buffer(self) -> NDArray[np.uint8]:
        """The buffer contains the rgb data to be displayed."""
        return self.__buffer

    @frame_buffer.setter
    def frame_buffer(self, value: NDArray[np.uint8]):
        if self.__buffer.shape == value.shape:
            # apply the brightness directly to the frame
            self.__buffer = np.ceil(value * self.__display_brightness)

    def clear_buffer(self) -> None:
        self.__buffer = np.zeros_like(self.__buffer)

    @property
    def _config(self) -> Settings:
        return self.__config

    @abstractmethod
    def show(self, gamma: bool=False) -> None:
        """Display the contents of buffer on display. Gamma correction can be
        toggled."""

    @final
    def clear(self) -> None:
        """Clear display"""
        self.clear_buffer()
        self.show()

    @final
    def set_brightness(self, brightness: int) -> None:
        """Set the brightness 0 to 100 value"""
        self.__display_brightness = self._calc_real_brightness(brightness)

    @abstractmethod
    def _calc_real_brightness(self, brightness: int) -> float:
        raise NotImplementedError
