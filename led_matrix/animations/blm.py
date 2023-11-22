import errno
import os
from dataclasses import dataclass, field
from io import BytesIO, TextIOWrapper
from pathlib import Path
from queue import Queue
from typing import Callable, Generator, Optional, cast

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings, AnimationVariant)
from led_matrix.animations import ANIMATION_RESOURCES_DIR
from led_matrix.common.color import Color
from led_matrix.common.log import eprint

_BLM_ANIMATIONS_DIR = ANIMATION_RESOURCES_DIR / "162-blms"


BlmVariant = AnimationVariant.build_variants_from_files(name="BlmVariant",
                                                        search_dir=_BLM_ANIMATIONS_DIR,
                                                        glob_str="*.blm")


@dataclass(kw_only=True)
class BlmParameter(AnimationParameter):
    foregound_color: Color = Color(255, 255, 255)
    background_color: Color = Color(10, 10, 10)
    padding_color: Color = Color(60, 60, 60)


@dataclass(kw_only=True)
class BlmSettings(AnimationSettings):
    variant: Optional[AnimationVariant] = None
    parameter: Optional[AnimationParameter] = field(default_factory=BlmParameter)


@dataclass(kw_only=True)
class _BlmFrame:
    hold: int
    text_frame: list[list[str]]
    frame: NDArray[np.uint8] = field(init=False)
    is_valid: bool = field(init=False, default=True)

    def __post_init__(self):
        try:
            self.frame = np.array(self.text_frame, dtype=np.uint8)
        except ValueError:
            self.is_valid = False


class BlmAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        if self._settings.variant is None:
            raise RuntimeError("Started BLM animation without a variant.")

        self.__path: Path = self._settings.variant.value

        if not self.__path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.__path)

        self.__frames: list[_BlmFrame] = self.__load_frames()

        parameter: BlmParameter = cast(BlmParameter, self._settings.parameter)
        self.__foregound_color: tuple[int, int, int] = parameter.foregound_color.pil_tuple
        self.__background_color: tuple[int, int, int] = parameter.background_color.pil_tuple
        self.__padding_color: tuple[int, int, int] = parameter.padding_color.pil_tuple

        self.__frame_generator: Generator[tuple[int, NDArray[np.uint8]], None, None] = self.__rendered_frames()

    def intrinsic_duration(self) -> float:
        ret: int = 0
        item: _BlmFrame
        for item in self.__frames:
            ret += item.hold

        return ret / 1000.0

    def __str__(self) -> str:
        # pylint: disable=C0209
        return "Path: {} file: {} frames: {} shape: {} duration: {}\n".format(
            self.__path,
            f"blm.{self.__path.stem}",
            str(len(self.__frames)),
            (
                (len(self.__frames[0].text_frame), len(self.__frames[0].text_frame[0]))
                if len(self.__frames) > 0
                else "no frames available"
            ),
            self.intrinsic_duration()
        )

    def __load_frames(self) -> list[_BlmFrame]:
        blm_frames: list[_BlmFrame] = []

        f: TextIOWrapper
        with self.__path.open(encoding='latin1') as f:
            hold: int = 0
            frame: list[list[str]] = []

            line: str
            for line in f:
                line = line.strip()

                if line.startswith('#'):
                    continue

                if line.startswith("@"):
                    if len(frame) > 0:
                        blm_frames.append(_BlmFrame(hold=hold,
                                                    text_frame=frame))

                    hold = int(line[1:])
                    # reset frame
                    frame = []
                    continue

                if len(line):
                    frame.append(list(line))

            if len(frame) > 0:
                blm_frames.append(_BlmFrame(hold=hold,
                                            text_frame=frame))

        if len(blm_frames) == 0:
            raise AttributeError

        return blm_frames

    def render_next_frame(self) -> bool:
        next_frame: tuple[int, NDArray[np.uint8]] | None = next(self.__frame_generator, None)

        if next_frame is not None:
            self._frame_queue.put(next_frame[1].copy())
            self._set_animation_speed(next_frame[0] / 1000)

            # maybe there's still more to render
            return True

        if self.is_next_iteration():
            # recreate frame generator if another iteration should be started
            self.__frame_generator = self.__rendered_frames()

        # the current iteration has no frames left
        return False

    def __rendered_frames(self) -> Generator[tuple[int, NDArray[np.uint8]], None, None]:
        """
        Generator function to iterate through all frames of animation.
        Cropped to fit matrix size.
        """
        frame: _BlmFrame
        for frame in self.__frames:
            array: NDArray[np.uint8] = frame.frame
            array = np.dstack((array, array, array))

            # indices where to find the ones and the zeros in the frame
            # needed to replace with a color
            ones: NDArray[np.bool_] = array == 1
            zeros: NDArray[np.bool_] = array == 0

            np.putmask(array, ones, self.__foregound_color)
            np.putmask(array, zeros, self.__background_color)

            h: int
            w: int
            (h, w, _b) = array.shape

            diff_h: int = h - self._height
            diff_w: int = w - self._width

            diff_h_top: int = abs(diff_h // 2)
            diff_h_bottom: int = abs(diff_h) - diff_h_top

            diff_w_left: int = abs(diff_w // 2)
            diff_w_right: int = abs(diff_w) - diff_w_left

            # print(h, w, b, diff_h, diff_w, diff_h_top, diff_h_bottom,
            #      diff_w_left, diff_w_right)

            # first crop array
            if diff_h > 0:
                array = array[diff_h_top:-diff_h_bottom, :, :]
            if diff_w > 0:
                array = array[:, diff_w_left:-diff_w_right, :]

            # then pad it
            pad: NDArray[np.uint8]
            if diff_h < 0:
                pad = np.full((self._height, self._width, 3), fill_value=self.__padding_color, dtype=np.uint8)
                pad[diff_h_top:array.shape[0]+diff_h_top, :, :] = array
                array = pad
            if diff_w < 0:
                pad = np.full((self._height, self._width, 3), fill_value=self.__padding_color, dtype=np.uint8)
                pad[:, diff_w_left:array.shape[1]+diff_w_left, :] = array
                array = pad

            yield (frame.hold, array)


class BlmController(AbstractAnimationController,
                    animation_name="blinkenlights",
                    animation_class=BlmAnimation,
                    settings_class=BlmSettings,
                    default_settings=BlmSettings(),
                    accepts_dynamic_variant=True,
                    is_repeat_supported=True,
                    variant_enum=BlmVariant,
                    parameter_class=BlmParameter):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, on_finish_callable)

        _BLM_ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)

    def _add_dynamic_variant(self, file_name: str, file_content: BytesIO) -> None:
        # error handling
        if file_name.rsplit(".", 1)[-1].lower() != "blm":
            eprint("The new variant file must be a blm-file!")
            return

        file_path: Path = (_BLM_ANIMATIONS_DIR / file_name).resolve()

        with open(file_path, "wb+") as f:
            f.write(file_content.read())

        global BlmVariant  # pylint: disable=W0603
        BlmVariant = BlmVariant.refresh_variants()

    def _remove_dynamic_variant(self, variant: AnimationVariant) -> None:
        animation_file: Path = variant.value.resolve()

        # only remove files that are in the animations directory
        if _BLM_ANIMATIONS_DIR in animation_file.parents:
            animation_file.unlink(missing_ok=True)

            global BlmVariant  # pylint: disable=W0603
            BlmVariant = BlmVariant.refresh_variants()
