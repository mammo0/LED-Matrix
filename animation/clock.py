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

        self.middle_x = int(width / 2)
        self.middle_y = int(height / 2)
        self.max_hand_length = min([self.middle_x, round(width / 2),
                                    self.middle_y, round(height / 2)])

    def minute_point(self, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2

        x = int(self.middle_x + self.max_hand_length * math.cos(angle))
        y = int(self.middle_y + self.max_hand_length * math.sin(angle))

        return (x, y)

    def hour_point(self, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        length = int(self.max_hand_length / 2)

        x = int(self.middle_x + length * math.cos(angle))
        y = int(self.middle_y + length * math.sin(angle))

        return (x, y)

    def add_hour_minute_hands(self, image, hour, minute):
        middle_point = (self.middle_x, self.middle_y)
        draw = ImageDraw.Draw(image)
        draw.line([middle_point,
                   self.minute_point(minute)], fill=self.minute_color)
        draw.line([middle_point,
                   self.hour_point(hour)], fill=self.hour_color)
        draw.point(middle_point, fill=self.divider_color)

    def animate(self):
        while self._running:
            if self.variant == "analog":
                local_time = time.localtime()
                image = self.background.copy()
                self.add_hour_minute_hands(image,
                                           local_time.tm_hour,
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
