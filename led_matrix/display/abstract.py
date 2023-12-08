"""
This module is the abstract representation of a pixel matrix display.
"""
from abc import ABC, abstractmethod
from typing import final

import numpy as np
from numpy.typing import NDArray

from led_matrix.config.settings import Settings
from led_matrix.config.types import ColorTemp


class AbstractDisplay(ABC):
    def __init__(self, config: Settings) -> None:
        self.__config: Settings = config

        self.__buffer: NDArray[np.uint8] = np.zeros(
            (config.main.display_height, config.main.display_width, 3),  # 3 for red, green, blue
            dtype=np.uint8
        )

        self.__color_temp: ColorTemp = ColorTemp.K_6000

    @property
    def frame_buffer(self) -> NDArray[np.uint8]:
        """The buffer contains the rgb data to be displayed."""
        return self.__buffer

    @frame_buffer.setter
    def frame_buffer(self, value: NDArray[np.uint8]):
        if self.__buffer.shape == value.shape:
            # check if the color temperature should be changed
            if self.__color_temp != ColorTemp.K_6000:
                # iterate over the last axis (2) which contains the color values
                i: tuple[int, ...]
                for i in np.ndindex(value.shape[:2]):
                    # apply the color temperature
                    value[i] = np.ceil(value[i] * self.__color_temp.value).astype(np.uint8)

            self.__buffer = value

    def clear_buffer(self) -> None:
        self.__buffer = np.zeros_like(self.__buffer)

    @property
    def _config(self) -> Settings:
        return self.__config

    @abstractmethod
    def show(self, gamma: bool=False) -> None:
        """Display the contents of buffer on display. Gamma correction can be
        toggled."""
        raise NotImplementedError

    @final
    def clear(self) -> None:
        """Clear display"""
        self.clear_buffer()
        self.show()

    @abstractmethod
    def set_brightness(self, brightness: int) -> None:
        """Set the brightness 0 to 100 value"""
        raise NotImplementedError

    @final
    def set_color_temp(self, color_temp: ColorTemp) -> None:
        self.__color_temp = color_temp
