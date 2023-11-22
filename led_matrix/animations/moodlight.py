import colorsys
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from typing import Callable, Generator, Optional

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationSettings, AnimationVariant)
from led_matrix.common.color import Color


class MoodlightVariant(AnimationVariant):
    COLOR_WHEEL = auto()
    CYCLE_COLORS = auto()
    WISH_UP_DOWN = auto()


class _ColorMode(Enum):
    COLOR_WHEEL = auto()
    CYCLE_COLORS = auto()


class _Style(Enum):
    FILL = auto()
    RANDOM_DOT = auto()
    WISH_UP_DOWN = auto()


@dataclass(kw_only=True)
class MoodlightSettings(AnimationSettings):
    variant: Optional[AnimationVariant] = MoodlightVariant.WISH_UP_DOWN


class MoodlightAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        self.__colors: list[Color] = [Color(255, 0, 0),
                                      Color(255, 255, 0),
                                      Color(0, 255, 255),
                                      Color(0, 0, 255)]

        #TODO: implement hold and transition_duration
        # self.__hold = 10  # seconds to hold colors
        # self.__transition_duration = 10  # seconds to change from one to other

        if self._settings.variant == MoodlightVariant.COLOR_WHEEL:
            self.__frame_generator = self.__generate_frames(_ColorMode.COLOR_WHEEL, _Style.FILL)
        elif self._settings.variant == MoodlightVariant.CYCLE_COLORS:
            self.__frame_generator = self.__generate_frames(_ColorMode.CYCLE_COLORS, _Style.RANDOM_DOT)
        elif self._settings.variant == MoodlightVariant.WISH_UP_DOWN:
            self.__frame_generator = self.__generate_frames(_ColorMode.COLOR_WHEEL, _Style.WISH_UP_DOWN)

    def __hsv_to_rgb(self, h: float, s: float, v: float) -> Color:
        # h is in degrees
        # s, v in percent
        h %= 360
        h /= 360
        s /= 100
        v /= 100

        r: float
        g: float
        b: float
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return Color(red_or_hex=int(r * 255),
                     green=int(g * 255),
                     blue=int(b * 255))

    def __color_wheel_generator(self, steps: int) -> Generator[Color, None, None]:
        # steps: how many steps to take to go from 0 to 360.
        increase: float = (360 - 0) / steps

        while True:
            i: float
            for i in np.arange(0, 360, increase):
                color: Color = self.__hsv_to_rgb(i, 100, 100)
                yield color

    def __cycle_selected_colors_generator(self, steps: int, hold: int) -> Generator[Color, None, None]:
        # steps: how many steps from one color to other color
        # hold: how many iterations to stay at one color
        current_color: Color | None = None

        while True:
            for color in self.__colors:
                if current_color is None:
                    current_color = color
                    yield color
                else:
                    # rgb color
                    r, g, b = color.pil_tuple
                    current_r, current_g, current_b = current_color.pil_tuple

                    increase_r: float = (r - current_r) / steps
                    increase_g: float = (g - current_g) / steps
                    increase_b: float = (b - current_b) / steps

                    for _ in range(steps):
                        current_r += int(increase_r)
                        current_g += int(increase_g)
                        current_b += int(increase_b)

                        current_color = color = Color(current_r, current_g, current_b)

                        yield color

                for _ in range(hold):
                    yield color

    def __generate_frames(self, color_mode, style) -> Generator[NDArray[np.uint8], None, None]:
        frame: NDArray[np.uint8] = np.zeros((self._height, self._width, 3), dtype=np.uint8)

        colors: Generator[Color, None, None] | None = None
        if color_mode == _ColorMode.COLOR_WHEEL:
            colors = self.__color_wheel_generator(500)
        elif color_mode == _ColorMode.CYCLE_COLORS:
            colors = self.__cycle_selected_colors_generator(5, 100)

        while colors is not None:
            try:
                color: Color = next(colors)
            except StopIteration:
                return
            if color is None:
                return

            if style == _Style.FILL:
                frame[:, :] = color.pil_tuple
                yield frame
            elif style == _Style.RANDOM_DOT:
                y: int = np.random.randint(0, self._height)
                x: int = np.random.randint(0, self._width)
                frame[y, x] = color.pil_tuple
                yield frame
            elif style == _Style.WISH_UP_DOWN:
                frame: NDArray[np.uint8] = np.concatenate(
                    (frame[1:self._height, :],
                     np.array(color.pil_tuple * self._width).reshape((1, self._width, 3))),
                    axis=0
                )
                yield frame

    def render_next_frame(self) -> bool:
        # there's always a next frame because of 'while True' in the generator
        next_frame: NDArray[np.uint8] = next(self.__frame_generator)
        self._frame_queue.put(next_frame.copy())

        # moodlight runs infinitely
        return True


class MoodlightController(AbstractAnimationController,
                          animation_name="moodlight",
                          animation_class=MoodlightAnimation,
                          settings_class=MoodlightSettings,
                          default_settings=MoodlightSettings(),
                          accepts_dynamic_variant=False,
                          is_repeat_supported=False,
                          variant_enum=MoodlightVariant):
    pass
