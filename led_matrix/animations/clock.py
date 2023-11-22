import math
import time
from dataclasses import dataclass, field
from enum import auto
from logging import Logger
from queue import Queue
from typing import Callable, Optional, cast

import numpy as np
from PIL.Image import Image, new
from PIL.ImageDraw import Draw, ImageDraw

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings, AnimationVariant)
from led_matrix.common.color import Color


class ClockVariant(AnimationVariant):
    ANALOG = auto()
    DIGITAL = auto()


@dataclass(kw_only=True)
class ClockParameter(AnimationParameter):
    # default values
    background_color: Color = Color(0, 0, 0)
    divider_color: Color = Color(255, 255, 255)
    hour_color: Color = Color(255, 0, 0)
    minute_color:Color = Color(255, 255, 255)
    blinking_seconds: bool = True


@dataclass(kw_only=True)
class ClockSettings(AnimationSettings):
    # default settings
    variant: Optional[AnimationVariant] = ClockVariant.ANALOG
    parameter: Optional[AnimationParameter] = field(default_factory=ClockParameter)


class ClockAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 logger: Logger,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, logger, on_finish_callable)

        parameter: ClockParameter = cast(ClockParameter, self._settings.parameter)

        backgroud_color: tuple[int, int, int] = parameter.background_color.pil_tuple
        self.__divider_color: tuple[int, int, int] = parameter.divider_color.pil_tuple
        self.__hour_color: tuple[int, int, int] = parameter.hour_color.pil_tuple
        self.__minute_color: tuple[int, int, int] = parameter.minute_color.pil_tuple
        self.__blinking_seconds: bool = parameter.blinking_seconds

        self.__background_image: Image = new("RGB", (width, height), backgroud_color)

        self.__analog_middle_x: int = self.__middle_calculation(width)
        self.__analog_middle_y: int = self.__middle_calculation(height)
        self.__analog_max_hand_length: int = min([self.__analog_middle_x + 1,
                                                  self.__analog_middle_y + 1])

        # set the animation speed bassed on the variant
        if self._settings.variant == ClockVariant.ANALOG:
            self._set_animation_speed(1)
        elif self._settings.variant == ClockVariant.DIGITAL:
            self._set_animation_speed(1/10)

    def __middle_calculation(self, value: int) -> int:
        r: float = value / 2
        if r == int(r):
            return int(r) - 1

        return math.floor(r)

    def __analog_minute_point(self, minute: int) -> tuple[int, int]:
        minute %= 60
        angle: float = 2*math.pi * minute/60 - math.pi/2

        x: int = self.__analog_middle_x + int(self.__analog_max_hand_length * math.cos(angle))
        y: int = self.__analog_middle_y + int(self.__analog_max_hand_length * math.sin(angle))

        return (x, y)

    def __analog_hour_point(self, hour: int) -> tuple[int, int]:
        hour %= 12
        angle: float = 2*math.pi * hour/12 - math.pi/2
        length: int = math.ceil(self.__analog_max_hand_length / 2)

        x: int = int(self.__analog_middle_x + length * math.cos(angle))
        y: int = int(self.__analog_middle_y + length * math.sin(angle))

        return (x, y)

    def __analog_create_clock_image(self, hour: int, minute: int) -> Image:
        middle_point: tuple[int, int] = (self.__analog_middle_x, self.__analog_middle_y)

        image: Image = self.__background_image.copy()

        draw: ImageDraw = Draw(image)
        draw.line([middle_point, self.__analog_minute_point(minute)],
                  fill=self.__minute_color)
        draw.line([middle_point, self.__analog_hour_point(hour)],
                  fill=self.__hour_color)
        draw.point(middle_point,
                   fill=self.__divider_color)

        return image

    def __digital_draw_digit(self, draw: ImageDraw, digit: int,
                             x: int, y: int, width: int, height: int,
                             color: tuple[int, int, int]) -> None:
        point_begin: tuple[int, int]
        point_end: tuple[int, int]

        if digit in [4, 5, 6, 7, 8, 9, 0]:
            # draw left upper
            point_begin = (x, y)
            point_end = (x, y + self.__middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)
        if digit in [2, 6, 8, 0]:
            # draw left lower
            point_begin = (x, y + self.__middle_calculation(height))
            point_end = (x, y + height - 1)
            draw.line([point_begin, point_end], fill=color)

        if digit in [1, 2, 3, 4, 7, 8, 9, 0]:
            # draw right upper
            point_begin = (x + width - 1, y)
            point_end = (x + width - 1, y + self.__middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)
        if digit in [1, 3, 4, 5, 6, 7, 8, 9, 0]:
            # draw right lower
            point_begin = (x + width - 1, y + self.__middle_calculation(height))
            point_end = (x + width - 1, y + height - 1)
            draw.line([point_begin, point_end], fill=color)

        if digit in [2, 3, 5, 6, 7, 8, 9, 0]:
            # draw top
            point_begin = (x, y)
            point_end = (x + width - 1, y)
            draw.line([point_begin, point_end], fill=color)
        if digit in [2, 3, 5, 6, 8, 9, 0]:
            # draw bottom
            point_begin = (x, y + height - 1)
            point_end = (x + width - 1, y + height - 1)
            draw.line([point_begin, point_end], fill=color)
        if digit in [2, 3, 4, 5, 6, 8, 9]:
            # draw middle
            point_begin = (x, y + self.__middle_calculation(height))
            point_end = (x + width - 1, y + self.__middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)

    def __digital_create_clock_image(self, hour: int, minute: int, second: int) -> Image:
        hour_txt: str = str(hour).zfill(2)
        minute_txt: str = str(minute).zfill(2)

        image: Image = self.__background_image.copy()
        draw: ImageDraw = Draw(image)

        # char width: space between middle and right/left - 1 (space between chars)} / 2 (two chars for hour/minute)
        char_width: int = int((self.__analog_middle_x - 1) / 2)

        # char height: matrix height - 2 pixel space
        char_height: int = self._height - 2

        # draw hours
        hour_1_x: int = self.__analog_middle_x - (2 * char_width + 1)
        hour_2_x: int = hour_1_x + char_width + 1
        self.__digital_draw_digit(draw, int(hour_txt[0]),
                                  x=hour_1_x, y=1, width=char_width, height=char_height, color=self.__hour_color)
        self.__digital_draw_digit(draw, int(hour_txt[1]),
                                  x=hour_2_x, y=1, width=char_width, height=char_height, color=self.__hour_color)

        # draw minutes
        minute_1_x: int = self._width - (2 * char_width + 1)
        minute_2_x: int = minute_1_x + char_width + 1
        self.__digital_draw_digit(draw, int(minute_txt[0]),
                                  x=minute_1_x, y=1, width=char_width, height=char_height, color=self.__minute_color)
        self.__digital_draw_digit(draw, int(minute_txt[1]),
                                  x=minute_2_x, y=1, width=char_width, height=char_height, color=self.__minute_color)

        # minute hour divider
        divider_space: int = int(char_height / 4)
        # always draw it if it should not blink
        if (not self.__blinking_seconds or
                # if it should blink, draw the divider every two seconds
                second % 2 == 0):
            draw.point([self.__analog_middle_x, self.__analog_middle_y + divider_space],
                       fill=self.__divider_color)
            draw.point([self.__analog_middle_x, self.__analog_middle_y - divider_space],
                       fill=self.__divider_color)

        return image

    def render_next_frame(self) -> bool:
        local_time: time.struct_time = time.localtime()

        image: Image
        if self._settings.variant == ClockVariant.ANALOG:
            image = self.__analog_create_clock_image(local_time.tm_hour,
                                                     local_time.tm_min)
            self._frame_queue.put(np.array(image).copy())
        elif self._settings.variant == ClockVariant.DIGITAL:
            image = self.__digital_create_clock_image(local_time.tm_hour,
                                                      local_time.tm_min,
                                                      local_time.tm_sec)
            self._frame_queue.put(np.array(image).copy())
        else:
            # this should not happen
            # but if, just exit here
            return False

        # the clock animation is infinitely
        return True


class ClockController(AbstractAnimationController,
                      animation_name="clock",
                      animation_class=ClockAnimation,
                      settings_class=ClockSettings,
                      default_settings=ClockSettings(),
                      accepts_dynamic_variant=False,
                      is_repeat_supported=False,
                      variant_enum=ClockVariant,
                      parameter_class=ClockParameter):
    pass
