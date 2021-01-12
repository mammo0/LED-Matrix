import math
import time

from PIL import Image, ImageDraw

from animation.abstract_animation import AbstractAnimation
import numpy as np


LEN_HOUR = 2


class ClockAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat=False,
                 variant="analog",
                 background_color=(50, 70, 230), devider_color=(255, 255, 255),
                 hour_color=(255, 255, 255), minute_color=(255, 255, 255)):
        super().__init__(width, height, frame_queue, repeat)
        self.name = "clock"
        self.variant = variant
        self.background_color = background_color
        watch = Image.open("resources/clock/watch_16x16_without_arms.png")
        self.background = Image.new("RGB", (width, height), background_color)
        self.x = int((self.width - watch.width) / 2)
        self.y = int((self.height - watch.height) / 2)
        self.background.paste(watch, (self.x, self.y), mask=watch.split()[3])
        # self.dump_animation()

    def minute_point(self, middle, minute):
        minute %= 60
        angle = 2*math.pi * minute/60 - math.pi/2
        length = 2
        while True:
            x = int(middle[0] + length * math.cos(angle))
            y = int(middle[1] + length * math.sin(angle))
            if x == (5 + self.x) or x == (10 + self.x):
                break
            if y == (5 + self.y) or y == (10 + self.y):
                break
            length += 1
        return (x, y)

    def hour_point(self, middle, hour):
        hour %= 12
        angle = 2*math.pi * hour/12 - math.pi/2
        x = int(middle[0] + LEN_HOUR * math.cos(angle))
        y = int(middle[1] + LEN_HOUR * math.sin(angle))
        if x > (9 + self.x):
            x = (9 + self.x)
        if y > (10 + self.x):
            y = (10 + self.x)
        return (x, y)

    def middle_point(self, minute):
        x = self.width / 2
        y = self.height / 2
        return int(x), int(y)
#        if minute > 0 and minute <=15:
#            return (7,8)
#        elif minute > 15 and minute <=30:
#            return (7,7)
#        elif minute > 30 and minute <=45:
#            return (8,7)
#        else:
#            return (8,8)

    def add_hour_minute_hands(self, image, hour, minute):
        middle = self.middle_point(minute)
        draw = ImageDraw.Draw(image)
        draw.line([self.middle_point(minute),
                   self.minute_point(middle, minute)], fill=(0, 0, 0))
        draw.line([self.middle_point(minute),
                   self.hour_point(middle, hour)], fill=(0, 0, 0))

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
                "variant": self.variant, "background_color": self.background_color}

    def dump_animation(self, min_step=5):
        hour = 0
        for i in range(1, 12*60+1):
            if i % 60 == 0:
                hour += 1
                hour %= 12
            minute = i % 60
            if minute % min_step == 0:
                cp = self.background.copy()
                draw = ImageDraw.Draw(cp)
                middle = self.middle_point(minute)
                draw.line([self.middle_point(minute),
                           self.minute_point(middle, minute)], fill=(0, 0, 0))
                draw.line([self.middle_point(minute),
                           self.hour_point(middle, hour)], fill=(0, 0, 0))
                cp.save("{}.bmp".format(i))
