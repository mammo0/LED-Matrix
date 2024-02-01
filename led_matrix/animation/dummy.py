from dataclasses import dataclass
from logging import Logger
from queue import Queue
from typing import Callable, Final, cast

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationSettings)

DUMMY_ANIMATION_NAME: Final[str] = "dummy"


@dataclass(kw_only=True)
class DummySettings(AnimationSettings):
    pass


class DummyAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 logger: Logger,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, logger, on_finish_callable)

        self.__first_run: bool = True

    def render_next_frame(self):
        # only on first run
        if self.__first_run:
            # clear the current display
            frame: NDArray[np.uint8] = np.zeros((self._height, self._width, 3),
                                                dtype=np.uint8)
            self._frame_queue.put(frame)
            self.__first_run = False

        # do nothing more here, but continue
        return True

    def display_frame(self, frame: NDArray[np.uint8]):
        # check stop and pause event
        if not (self._stop_event.is_set() or
                self._pause_event.is_set()):
            self._frame_queue.put(frame)


class DummyController(AbstractAnimationController,
                      animation_name=DUMMY_ANIMATION_NAME,
                      animation_class=DummyAnimation,
                      settings_class=DummySettings,
                      accepts_dynamic_variant=False,
                      is_repeat_supported=False):
    def display_frame(self, frame: NDArray[np.uint8]) -> None:
        """
        This method is special and only available in the Dummy animation.
        It allows direct access to the frame queue.
        @param frame: This frame gets directly added to the frame queue if the animation is running.
        """
        if self._current_animation is not None and self.is_running:
            animation_thread: DummyAnimation = cast(DummyAnimation, self._current_animation[1])
            animation_thread.display_frame(frame)
