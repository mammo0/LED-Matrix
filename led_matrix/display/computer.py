import queue
from queue import Queue
from threading import Thread
from typing import Final

import numpy as np
import pygame
from numpy.typing import NDArray
from pygame import Vector2
from pygame.color import Color
from pygame.event import Event
from pygame.rect import Rect
from pygame.surface import Surface
from pygame.time import Clock

from led_matrix.config.settings import Settings
from led_matrix.display.abstract import AbstractDisplay
from led_matrix.main import MainController

class _PygameDisplayThread(Thread):
    MAX_FPS: Final[float] = 60.

    def __init__(self, width: int, height: int, margin: int, size: int) -> None:
        super().__init__()

        self.__width: int = width
        self.__height: int = height
        self.__margin: int = margin
        self.__size: int = size

        self.__display_queue: Queue[NDArray[np.uint8]] = Queue()
        self.__last_frame: NDArray[np.uint8] | None = None

        self.__brightness: float = 100.

        self.__window_size: tuple[int, int] = (width * size + (width + 1) * margin,
                                               height * size + (height + 1) * margin)

        # these variables are used for simulating a LED
        # use this to set the amount of 'segments' we rotate our blend into
        # this helps stop blends from looking 'boxy' or like a cross.
        self.__circular_smoothness_steps = 10

        self.__led_gradient_background: Color = Color((0, 0, 0, 200))
        self.__led_gradient_background.r = self.__led_gradient_background.r // self.__circular_smoothness_steps
        self.__led_gradient_background.g = self.__led_gradient_background.g // self.__circular_smoothness_steps
        self.__led_gradient_background.b = self.__led_gradient_background.b // self.__circular_smoothness_steps
        self.__led_gradient_background.a = self.__led_gradient_background.a // self.__circular_smoothness_steps

        # clock to handle fps
        self.__clock: Clock = Clock()

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

    def __draw_frame(self, surface: Surface, frame: NDArray[np.uint8]) -> None:
        surface.fill(color=Color(0, 0, 0))

        # lock brightness value
        frame_brightness: float = self.__brightness

        it: np.nditer = np.nditer([frame[..., 0],
                                   frame[..., 1],
                                   frame[..., 2]], flags=['multi_index'])
        while not it.finished:
            color: Color = Color(int(it[0] * frame_brightness),
                                 int(it[1] * frame_brightness),
                                 int(it[2] * frame_brightness))

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
                surface.blit(led_surface, dest=led_pos)

            it.iternext()

    def display_frame(self, frame: NDArray[np.uint8]) -> None:
        # queue the frame
        self.__display_queue.put(frame)

    def set_brightness(self, brightness: int) -> None:
        # expecting float brightness 0 .. 1.0
        self.__brightness = brightness / 100

        # re-add the last frame to the display queue on brightness change
        # this triggers an immediate redraw of the frame
        if self.__last_frame is not None:
            self.__display_queue.put(self.__last_frame)

    def run(self) -> None:
        # pygame must be initialized in the thread that updates the display
        pygame.init()
        surface: Surface = pygame.display.set_mode(self.__window_size)
        pygame.display.set_caption(f"LED-Matrix {self.__width}x{self.__height}")

        # start the main loop
        while True:
            try:
                event: Event
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        # stop everything
                        MainController.quit()
                        return
            except pygame.error:
                # this error is normally thrown if we are already shutting down...
                return

            try:
                # preserve the last frame to be able to redraw it
                # needed on brightness change
                self.__last_frame = self.__display_queue.get(block=False)
            except queue.Empty:
                # just continue here
                pass
            else:
                self.__draw_frame(surface=surface,
                                  frame=self.__last_frame)

                self.__display_queue.task_done()

            # draw the game screen
            pygame.display.update()

            # limit the FPS by sleeping for the remainder of the frame time
            self.__clock.tick(_PygameDisplayThread.MAX_FPS)


class Computer(AbstractDisplay):
    def __init__(self, config: Settings) -> None:
        super().__init__(config=config)

        self.__pygame_thread: _PygameDisplayThread = _PygameDisplayThread(width=config.main.display_width,
                                                                          height=config.main.display_height,
                                                                          margin=config.computer.margin,
                                                                          size=config.computer.led_size)

        # start the pygame thread
        self.__pygame_thread.start()

    def set_brightness(self, brightness: int) -> None:
        # forward brightness to pygame thread
        self.__pygame_thread.set_brightness(brightness)

    def show(self, gamma: bool=False) -> None:
        self.__pygame_thread.display_frame(frame=self.frame_buffer)
