from enum import Enum
import math
import time

from PIL import Image, ImageDraw

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController
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


class ClockAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat,
                 variant=ClockVariant.analog,
                 **kwargs):
        super().__init__(width, height, frame_queue, repeat)
        self.name = "clock"
        self.variant = variant

        self.params = ClockParameter(**kwargs)
        self.background_color = self.params.background_color.pil_tuple
        self.divider_color = self.params.divider_color.pil_tuple
        self.hour_color = self.params.hour_color.pil_tuple
        self.minute_color = self.params.minute_color.pil_tuple

        self.background = Image.new("RGB", (width, height), self.background_color)

        self.analog_middle_x = self.middle_calculation(width)
        self.analog_middle_y = self.middle_calculation(height)
        self.analog_max_hand_length = min([self.analog_middle_x + 1,
                                           self.analog_middle_y + 1])

    @property
    def variant_value(self):
        return self.variant

    @property
    def parameter_instance(self):
        return self.params

    def middle_calculation(self, value):
        value /= 2
        if value == int(value):
            return int(value) - 1
        else:
            return math.floor(value)

    def analog_minute_point(self, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2

        x = int(self.analog_middle_x + self.analog_max_hand_length * math.cos(angle))
        y = int(self.analog_middle_y + self.analog_max_hand_length * math.sin(angle))

        return (x, y)

    def analog_hour_point(self, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        length = math.ceil(self.analog_max_hand_length / 2)

        x = int(self.analog_middle_x + length * math.cos(angle))
        y = int(self.analog_middle_y + length * math.sin(angle))

        return (x, y)

    def analog_create_clock_image(self, hour, minute):
        middle_point = (self.analog_middle_x, self.analog_middle_y)

        image = self.background.copy()

        draw = ImageDraw.Draw(image)
        draw.line([middle_point, self.analog_minute_point(minute)],
                  fill=self.minute_color)
        draw.line([middle_point, self.analog_hour_point(hour)],
                  fill=self.hour_color)
        draw.point(middle_point,
                   fill=self.divider_color)

        return image

    def digital_draw_digit(self, draw, digit, x, y, width, height, color):
        if digit in [4, 5, 6, 7, 8, 9, 0]:
            # draw left upper
            point_begin = (x, y)
            point_end = (x, y + self.middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)
        if digit in [2, 6, 8, 0]:
            # draw left lower
            point_begin = (x, y + self.middle_calculation(height))
            point_end = (x, y + height - 1)
            draw.line([point_begin, point_end], fill=color)

        if digit in [1, 2, 3, 4, 7, 8, 9, 0]:
            # draw right upper
            point_begin = (x + width - 1, y)
            point_end = (x + width - 1, y + self.middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)
        if digit in [1, 3, 4, 5, 6, 7, 8, 9, 0]:
            # draw right lower
            point_begin = (x + width - 1, y + self.middle_calculation(height))
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
            point_begin = (x, y + self.middle_calculation(height))
            point_end = (x + width - 1, y + self.middle_calculation(height))
            draw.line([point_begin, point_end], fill=color)

    def digital_create_clock_image(self, hour, minute, second):
        hour_txt = str(hour).zfill(2)
        minute_txt = str(minute).zfill(2)

        image = self.background.copy()
        draw = ImageDraw.Draw(image)

        # char width: space between middle and right/left - 1 (space between chars)} / 2 (two chars for hour/minute)
        char_width = (self.analog_middle_x - 1) / 2

        # char height: matrix height - 2 pixel space
        char_height = self.height - 2

        # draw hours
        hour_1_x = self.analog_middle_x - (2 * char_width + 1)
        hour_2_x = hour_1_x + char_width + 1
        self.digital_draw_digit(draw, int(hour_txt[0]),
                                x=hour_1_x, y=1, width=char_width, height=char_height, color=self.hour_color)
        self.digital_draw_digit(draw, int(hour_txt[1]),
                                x=hour_2_x, y=1, width=char_width, height=char_height, color=self.hour_color)

        # draw minutes
        minute_1_x = self.width - (2 * char_width + 1)
        minute_2_x = minute_1_x + char_width + 1
        self.digital_draw_digit(draw, int(minute_txt[0]),
                                x=minute_1_x, y=1, width=char_width, height=char_height, color=self.minute_color)
        self.digital_draw_digit(draw, int(minute_txt[1]),
                                x=minute_2_x, y=1, width=char_width, height=char_height, color=self.minute_color)

        # draw the minute hour divider every two seconds
        divider_space = int(char_height / 4)
        if second % 2 == 0:
            draw.point([self.analog_middle_x, self.analog_middle_y + divider_space],
                       fill=self.divider_color)
            draw.point([self.analog_middle_x, self.analog_middle_y - divider_space],
                       fill=self.divider_color)

        return image

    def animate(self):
        while not self._stop_event.is_set():
            local_time = time.localtime()

            if self.variant == ClockVariant.analog:
                image = self.analog_create_clock_image(local_time.tm_hour,
                                                       local_time.tm_min)
                self.frame_queue.put(np.array(image).copy())
                self._stop_event.wait(timeout=1)
            elif self.variant == ClockVariant.digital:
                image = self.digital_create_clock_image(local_time.tm_hour,
                                                        local_time.tm_min,
                                                        local_time.tm_sec)
                self.frame_queue.put(np.array(image).copy())
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
