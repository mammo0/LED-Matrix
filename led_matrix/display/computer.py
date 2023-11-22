import numpy as np
import pygame
from pygame import Vector2
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

        width: int = config.main.display_width
        height: int = config.main.display_height
        self.__margin: int = config.computer.margin
        self.__size: int = config.computer.led_size

        window_size: tuple[int, int] = (width * self.__size + (width + 1) * self.__margin,
                                        height * self.__size + (height + 1) * self.__margin)

        # these variables are used for simulating a LED
        # use this to set the amount of 'segments' we rotate our blend into
        # this helps stop blends from looking 'boxy' or like a cross.
        self.__circular_smoothness_steps = 10

        self.__led_gradient_background: Color = Color((0, 0, 0, 200))
        self.__led_gradient_background.r = self.__led_gradient_background.r // self.__circular_smoothness_steps
        self.__led_gradient_background.g = self.__led_gradient_background.g // self.__circular_smoothness_steps
        self.__led_gradient_background.b = self.__led_gradient_background.b // self.__circular_smoothness_steps
        self.__led_gradient_background.a = self.__led_gradient_background.a // self.__circular_smoothness_steps

        pygame.init()
        self.__surface: Surface = pygame.display.set_mode(window_size)
        pygame.display.set_caption(f"LED-Matrix {width}x{height}")

        self.show()

    def __get_led_surface(self, led_color: Color) -> Surface | None:
        if (led_color.r, led_color.g, led_color.b) == (0, 0, 0):
            # do not simulate a black (off) LED
            return None

        led_color.r = led_color.r // self.__circular_smoothness_steps
        led_color.g = led_color.g // self.__circular_smoothness_steps
        led_color.b = led_color.b // self.__circular_smoothness_steps
        led_color.a = led_color.a // self.__circular_smoothness_steps

        led_surface: Surface = Surface((self.__size, self.__size), pygame.SRCALPHA)

        # 4x4 - starter
        radial_grad_starter: Surface = pygame.Surface((4, 4), pygame.SRCALPHA)
        radial_grad_starter.fill(self.__led_gradient_background)
        radial_grad_starter.fill(led_color, Rect(1, 1, 2, 2))

        radial_grad: Surface = pygame.transform.smoothscale(radial_grad_starter,
                                                            led_surface.get_size())

        for i in range(0, self.__circular_smoothness_steps):
            radial_grad_rot: Surface = pygame.transform.rotate(radial_grad,
                                                               (360.0 / self.__circular_smoothness_steps) * i)

            pos_rect: Rect = pygame.Rect((0, 0), led_surface.get_size())

            area_rect: Rect = pygame.Rect(0, 0, *led_surface.get_size())
            area_rect.center = radial_grad_rot.get_width()//2, radial_grad_rot.get_height()//2

            led_surface.blit(radial_grad_rot,
                             dest=pos_rect,
                             area=area_rect,
                             special_flags=pygame.BLEND_RGBA_ADD)

        return led_surface


    def _calc_real_brightness(self, brightness: int) -> float:
        return brightness / 100

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
            color: Color = Color(int(it[0]),
                                 int(it[1]),
                                 int(it[2]))

            # get the LED surface
            led_surface: Surface | None = self.__get_led_surface(led_color=color)

            # None means the LED is off
            if led_surface is not None:
                row: int
                column: int
                (row, column) = it.multi_index

                # the position of the LED on the main surface
                led_pos: Vector2 = Vector2(x=(self.__margin + self.__size) * column + self.__margin,
                                           y=(self.__margin + self.__size) * row + self.__margin)

                # add the LED surface to the main one
                self.__surface.blit(led_surface,
                                    dest=led_pos)

            it.iternext()

        pygame.display.update()
        # pygame.event.clear()
