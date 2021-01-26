import sys

import pygame

from common.config import Config
from display.abstract import AbstractDisplay
import numpy as np


class Computer(AbstractDisplay):
    def __init__(self, width, height, brightness, config):
        super().__init__(width, height, brightness, config)

        self.set_brightness(brightness)

        self.__margin = self._config.get(Config.COMPUTER.Margin)
        self.__size = self._config.get(Config.COMPUTER.LEDSize)

        window_size = (width * self.__size + (width + 1) * self.__margin,
                       height * self.__size + (height + 1) * self.__margin)

        pygame.init()
        self.__surface = pygame.display.set_mode(window_size)
        pygame.display.set_caption("RibbaPi {}x{}".format(width, height))
        self.show()

    def set_brightness(self, brightness):
        # expecting float brightness 0 .. 1.0
        self._brightness = brightness / 100

    def show(self, gamma=False):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.__surface.fill((0, 0, 0))

        it = np.nditer([self.buffer[:, :, 0],
                        self.buffer[:, :, 1],
                        self.buffer[:, :, 2]], flags=['multi_index'])
        while not it.finished:
            color = (it[0] * self._brightness, it[1] * self._brightness, it[2] * self._brightness)
            (row, column) = it.multi_index
            pygame.draw.rect(self.__surface, color,
                             [(self.__margin + self.__size) * column + self.__margin,
                              (self.__margin + self.__size) * row + self.__margin,
                              self.__size,
                              self.__size])
            it.iternext()

        pygame.display.update()
        # pygame.event.clear()
