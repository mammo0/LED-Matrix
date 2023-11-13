from dataclasses import dataclass
from queue import Queue
from typing import Callable, cast

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation.abstract import (
    AbstractAnimation,
    AbstractAnimationController,
    AnimationParameter,
    AnimationSettings,
    AnimationVariant,
)


@dataclass(kw_only=True)
class DummySettings(AnimationSettings):
    pass


class DummyAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

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


class DummyController(AbstractAnimationController):
    @property
    def animation_name(self) -> str:
        return "dummy"

    @property
    def animation_class(self) -> type[AbstractAnimation]:
        return DummyAnimation

    @property
    def variant_enum(self) -> type[AnimationVariant] | None:
        return None

    @property
    def parameter_class(self) -> type[AnimationParameter] | None:
        return None

    @property
    def settings_class(self) -> type[AnimationSettings]:
        return DummySettings

    @property
    def default_settings(self) -> AnimationSettings:
        return DummySettings(variant=None,
                             parameter=None)

    @property
    def is_repeat_supported(self) -> bool:
        return False

    @property
    def accepts_dynamic_variant(self) -> bool:
        return False

    def display_frame(self, frame: NDArray[np.uint8]) -> None:
        """
        This method is special and only available in the Dummy animation.
        It allows direct access to the frame queue.
        @param frame: This frame gets directly added to the frame queue if the animation is running.
        """
        if self._current_animation is not None and self.is_running:
            animation_thread: DummyAnimation = cast(DummyAnimation, self._current_animation[1])
            animation_thread.display_frame(frame)
