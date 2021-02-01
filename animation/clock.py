from enum import Enum
import math
import time

from PIL import Image, ImageDraw

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController, _AnimationSettingsStructure
from common.color import Color
import numpy as np


class ClockVariant(Enum):
    analog = 1
    digital = 2


class ClockParameter(AnimationParameter):
    # default values
    background_color = Color(0, 0, 0)
    divider_color = Color(255, 255, 255)
    hour_color = Color(255, 0, 0)
    minute_color = Color(255, 255, 255)
    blinking_seconds = True


class ClockSettings(_AnimationSettingsStructure):
    # default settings
    variant = ClockVariant.analog
    parameter = ClockParameter


class ClockAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, settings, on_finish_callable):
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        background_color = self._settings.parameter.background_color.pil_tuple
        self.__divider_color = self._settings.parameter.divider_color.pil_tuple
        self.__hour_color = self._settings.parameter.hour_color.pil_tuple
        self.__minute_color = self._settings.parameter.minute_color.pil_tuple
        self.__blinking_seconds = self._settings.parameter.blinking_seconds

        self.__background_image = Image.new("RGB", (width, height), background_color)

        self.__analog_middle_x = self.__middle_calculation(width)
        self.__analog_middle_y = self.__middle_calculation(height)
        self.__analog_max_hand_length = min([self.__analog_middle_x + 1,
                                             self.__analog_middle_y + 1])

    def __middle_calculation(self, value):
        value /= 2
        if value == int(value):
            return int(value) - 1
        else:
            return math.floor(value)

    def __analog_minute_point(self, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2

        x = int(self.__analog_middle_x + self.__analog_max_hand_length * math.cos(angle))
        y = int(self.__analog_middle_y + self.__analog_max_hand_length * math.sin(angle))

        return (x, y)

    def __analog_hour_point(self, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        length = math.ceil(self.__analog_max_hand_length / 2)

        x = int(self.__analog_middle_x + length * math.cos(angle))
        y = int(self.__analog_middle_y + length * math.sin(angle))

        return (x, y)

    def __analog_create_clock_image(self, hour, minute):
        middle_point = (self.__analog_middle_x, self.__analog_middle_y)

        image = self.__background_image.copy()

        draw = ImageDraw.Draw(image)
        draw.line([middle_point, self.__analog_minute_point(minute)],
                  fill=self.__minute_color)
        draw.line([middle_point, self.__analog_hour_point(hour)],
                  fill=self.__hour_color)
        draw.point(middle_point,
                   fill=self.__divider_color)

        return image

    def __digital_draw_digit(self, draw, digit, x, y, width, height, color):
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

    def __digital_create_clock_image(self, hour, minute, second):
        hour_txt = str(hour).zfill(2)
        minute_txt = str(minute).zfill(2)

        image = self.__background_image.copy()
        draw = ImageDraw.Draw(image)

        # char width: space between middle and right/left - 1 (space between chars)} / 2 (two chars for hour/minute)
        char_width = (self.__analog_middle_x - 1) / 2

        # char height: matrix height - 2 pixel space
        char_height = self._height - 2

        # draw hours
        hour_1_x = self.__analog_middle_x - (2 * char_width + 1)
        hour_2_x = hour_1_x + char_width + 1
        self.__digital_draw_digit(draw, int(hour_txt[0]),
                                  x=hour_1_x, y=1, width=char_width, height=char_height, color=self.__hour_color)
        self.__digital_draw_digit(draw, int(hour_txt[1]),
                                  x=hour_2_x, y=1, width=char_width, height=char_height, color=self.__hour_color)

        # draw minutes
        minute_1_x = self._width - (2 * char_width + 1)
        minute_2_x = minute_1_x + char_width + 1
        self.__digital_draw_digit(draw, int(minute_txt[0]),
                                  x=minute_1_x, y=1, width=char_width, height=char_height, color=self.__minute_color)
        self.__digital_draw_digit(draw, int(minute_txt[1]),
                                  x=minute_2_x, y=1, width=char_width, height=char_height, color=self.__minute_color)

        # minute hour divider
        divider_space = int(char_height / 4)
        # always draw it if it should not blink
        if (not self.__blinking_seconds or
                # if it should blink, draw the divider every two seconds
                second % 2 == 0):
            draw.point([self.__analog_middle_x, self.__analog_middle_y + divider_space],
                       fill=self.__divider_color)
            draw.point([self.__analog_middle_x, self.__analog_middle_y - divider_space],
                       fill=self.__divider_color)

        return image

    def animate(self):
        while not self._stop_event.is_set():
            local_time = time.localtime()

            if self._settings.variant == ClockVariant.analog:
                image = self.__analog_create_clock_image(local_time.tm_hour,
                                                         local_time.tm_min)
                self._frame_queue.put(np.array(image).copy())
                self._stop_event.wait(timeout=1)
            elif self._settings.variant == ClockVariant.digital:
                image = self.__digital_create_clock_image(local_time.tm_hour,
                                                          local_time.tm_min,
                                                          local_time.tm_sec)
                self._frame_queue.put(np.array(image).copy())
                self._stop_event.wait(timeout=1/10)


class ClockController(AbstractAnimationController):
    @property
    def animation_class(self):
        return ClockAnimation

    @property
    def animation_variants(self):
        return ClockVariant

    @property
    def animation_parameters(self):
        return ClockParameter

    @property
    def _default_animation_settings(self):
        return ClockSettings

    @property
    def is_repeat_supported(self):
        return False
