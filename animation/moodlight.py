import colorsys
from enum import Enum

from animation.abstract import AbstractAnimation, AbstractAnimationController,\
    _AnimationSettingsStructure
import numpy as np


class MoodlightVariant(Enum):
    colorwheel = 1
    cyclecolors = 2
    wish_down_up = 3


class _ColorMode(Enum):
    colorwheel = 1
    cyclecolors = 2


class _Style(Enum):
    fill = 1
    random_dot = 2
    wish_down_up = 3


class MoodlightSettings(_AnimationSettingsStructure):
    variant = MoodlightVariant.wish_down_up


class MoodlightAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, settings, on_finish_callable):
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        self.__colors = [(255, 0, 0), (255, 255, 0), (0, 255, 255), (0, 0, 255)]  # if empty choose random colors
        # TODO: implement hold and transition_duration
        self.__hold = 10  # seconds to hold colors
        self.__transition_duration = 10  # seconds to change from one to other

        if self._settings.variant == MoodlightVariant.colorwheel:
            self.__frame_generator = self.__generate_frames(_ColorMode.colorwheel, _Style.fill)
        elif self._settings.variant == MoodlightVariant.cyclecolors:
            self.__frame_generator = self.__generate_frames(_ColorMode.cyclecolors, _Style.random_dot)
        elif self._settings.variant == MoodlightVariant.wish_down_up:
            self.__frame_generator = self.__generate_frames(_ColorMode.colorwheel, _Style.wish_down_up)

    def __hsv_to_rgb(self, h, s, v):
        # h is in degrees
        # s, v in percent
        h %= 360
        h /= 360
        s /= 100
        v /= 100
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

    def __rgb_to_hsv(self, r, g, b):
        r /= 255
        g /= 255
        b /= 255
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (h * 360, s * 100, v * 100)

    def __color_wheel_generator(self, steps):
        # steps: how many steps to take to go from 0 to 360.
        increase = (360 - 0) / steps
        while True:
            for i in np.arange(0, 360, increase):
                color = self.__hsv_to_rgb(i, 100, 100)
                yield color

    def __cycle_selected_colors_generator(self, steps, hold):
        # steps: how many steps from one color to other color
        # hold: how many iterations to stay at one color
        current_color = None
        while True:
            for color in self.__colors:
                if not current_color:
                    current_color = color
                    yield color
                else:
                    # rgb color
                    r, g, b = color
                    current_r, current_g, current_b = current_color
                    increase_r = (r - current_r) / steps
                    increase_g = (g - current_g) / steps
                    increase_b = (b - current_b) / steps
                    for _ in range(steps):
                        current_r += increase_r
                        current_g += increase_g
                        current_b += increase_b
                        current_color = (current_r, current_g, current_b)
                        color = (int(current_r), int(current_g), int(current_b))
                        yield color
                for _ in range(hold):
                    yield color

    def __generate_frames(self, color_mode, style):
        frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)

        if color_mode == _ColorMode.colorwheel:
            colors = self.__color_wheel_generator(500)
        elif color_mode == _ColorMode.cyclecolors:
            colors = self.__cycle_selected_colors_generator(5, 100)

        while True:
            if style == _Style.fill:
                frame[:, :] = next(colors)
                yield frame
            elif style == _Style.random_dot:
                y = np.random.randint(0, self._height)
                x = np.random.randint(0, self._width)
                frame[y, x] = next(colors)
                yield frame
            elif style == _Style.wish_down_up:
                color = next(colors)
                frame = np.concatenate((frame[1:16, :],
                                        np.array(color * self._width).reshape(1, self._width, 3)), axis=0)
                yield frame

    def render_next_frame(self):
        # there's always a next frame because of 'while True' in the generator
        next_frame = next(self.__frame_generator)
        self._frame_queue.put(next_frame.copy())

        # moodlight runs infinitely
        return True


class MoodlightController(AbstractAnimationController):
    @property
    def animation_class(self):
        return MoodlightAnimation

    @property
    def animation_variants(self):
        return MoodlightVariant

    @property
    def animation_parameters(self):
        return None

    @property
    def default_animation_settings(self):
        return MoodlightSettings

    @property
    def is_repeat_supported(self):
        return False

    @property
    def accepts_dynamic_variant(self):
        return False
