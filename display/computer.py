#!/usr/bin/env python3

import sys

import pygame

from display.abstract_display import AbstractDisplay
import numpy as np


class Computer(AbstractDisplay):
    def __init__(self, width, height, config):
        super().__init__(width, height, config)

        self.margin = self.config.getint(None, option="Margin")
        self.size = self.config.getint(None, option="LEDSize")

        self.window_size = (width * self.size + (width + 1) * self.margin,
                            height * self.size + (height + 1) * self.margin)

        pygame.init()
        self.surface = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("RibbaPi {}x{}".format(width, height))
        self.show()

    def show(self, gamma=False):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.surface.fill((0, 0, 0))

        it = np.nditer([self.buffer[:, :, 0],
                        self.buffer[:, :, 1],
                        self.buffer[:, :, 2]], flags=['multi_index'])
        while not it.finished:
            color = (it[0] * self.brightness, it[1] * self.brightness, it[2] * self.brightness)
            (row, column) = it.multi_index
            pygame.draw.rect(self.surface, color,
                             [(self.margin + self.size) * column + self.margin,
                              (self.margin + self.size) * row + self.margin,
                              self.size,
                              self.size])
            it.iternext()

        pygame.display.update()
        # pygame.event.clear()


if __name__ == "__main__":
    display = Computer()
#    display.run_benchmark()
    display.create_test_pattern()
    display.show()
    import time
    time.sleep(5)
