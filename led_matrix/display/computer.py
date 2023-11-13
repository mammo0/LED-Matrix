import numpy as np
import pygame
from pygame.color import Color
from pygame.event import Event
from pygame.rect import Rect
from pygame.surface import Surface

from led_matrix.config.settings import Settings
from led_matrix.display.abstract import AbstractDisplay
from led_matrix.main import MainController


class Computer(AbstractDisplay):
    def __init__(self, config: Settings) -> None:
        super().__init__(config=config)

        self.__brightness: float
        self.set_brightness(config.main.brightness)

        width: int = config.main.display_width
        height: int = config.main.display_height
        self.__margin: int = config.computer.margin
        self.__size: int = config.computer.led_size

        window_size: tuple[int, int] = (width * self.__size + (width + 1) * self.__margin,
                                        height * self.__size + (height + 1) * self.__margin)

        pygame.init()
        self.__surface: Surface = pygame.display.set_mode(window_size)
        pygame.display.set_caption(f"LED-Matrix {width}x{height}")

        self.show()

    def set_brightness(self, brightness: int) -> None:
        # expecting float brightness 0 .. 1.0
        self.__brightness = brightness / 100

    def show(self, gamma: bool=False) -> None:
        event: Event
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    # stop everything
                    MainController.quit()
                    return
        except pygame.error:
            # this error is normally thrown if we are already shutting down...
            return

        self.__surface.fill(color=Color(0, 0, 0))

        it: np.nditer = np.nditer([self.frame_buffer[..., 0],
                                   self.frame_buffer[..., 1],
                                   self.frame_buffer[..., 2]], flags=['multi_index'])
        while not it.finished:
            color: Color = Color(int(it[0] * self.__brightness),
                                 int(it[1] * self.__brightness),
                                 int(it[2] * self.__brightness))

            row: int
            column: int
            (row, column) = it.multi_index

            pygame.draw.rect(surface=self.__surface,
                             color=color,
                             rect=Rect((self.__margin + self.__size) * column + self.__margin,
                                       (self.__margin + self.__size) * row + self.__margin,
                                       self.__size,
                                       self.__size)
            )

            it.iternext()

        pygame.display.update()
        # pygame.event.clear()
