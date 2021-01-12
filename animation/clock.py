import math
import time

from PIL import Image, ImageDraw

from animation.abstract_animation import AbstractAnimation
import numpy as np


class ClockAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat=False,
                 variant="analog",
                 background_color=(0, 0, 0), divider_color=(255, 255, 255),
                 hour_color=(255, 0, 0), minute_color=(255, 255, 255)):
        super().__init__(width, height, frame_queue, repeat)
        self.name = "clock"
        self.variant = variant

        self.background_color = background_color
        self.divider_color = divider_color
        self.hour_color = hour_color
        self.minute_color = minute_color

        self.background = Image.new("RGB", (width, height), background_color)

        self.analog_middle_x = int(width / 2)
        self.analog_middle_y = int(height / 2)
        self.analog_max_hand_length = min([self.analog_middle_x, round(width / 2),
                                           self.analog_middle_y, round(height / 2)])

    def analog_minute_point(self, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2

        x = int(self.analog_middle_x + self.analog_max_hand_length * math.cos(angle))
        y = int(self.analog_middle_y + self.analog_max_hand_length * math.sin(angle))

        return (x, y)

    def analog_hour_point(self, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        length = int(self.analog_max_hand_length / 2)

        x = int(self.analog_middle_x + length * math.cos(angle))
        y = int(self.analog_middle_y + length * math.sin(angle))

        return (x, y)

    def analog_create_clock_image(self, hour, minute):
        middle_point = (self.analog_middle_x, self.analog_middle_y)

        draw = ImageDraw.Draw(self.background)
        draw.line([middle_point, self.analog_minute_point(minute)],
                  fill=self.minute_color)
        draw.line([middle_point, self.analog_hour_point(hour)],
                  fill=self.hour_color)
        draw.point(middle_point,
                   fill=self.divider_color)

        return self.background

    def animate(self):
        while self._running:
            if self.variant == "analog":
                local_time = time.localtime()
                image = self.analog_create_clock_image(local_time.tm_hour,
                                                       local_time.tm_min)
                self.frame_queue.put(np.array(image).copy())
                time.sleep(1)
            else:
                # TODO: add digital clock
                pass

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat,
                "variant": self.variant, "background_color": self.background_color,
                "divider_color": self.divider_color, "hour_color": self.hour_color,
                "minute_color": self.minute_color}
