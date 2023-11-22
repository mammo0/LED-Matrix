import errno
import os
import shutil
from configparser import ConfigParser
from dataclasses import InitVar, dataclass, field
from io import BytesIO
from logging import Logger
from pathlib import Path
from queue import Queue
from typing import Callable, Generator, Optional, cast
from zipfile import ZipFile, ZipInfo

import numpy as np
from numpy.typing import NDArray
from PIL import Image as pil
from PIL.Image import Image

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings, AnimationVariant)
from led_matrix.animations import ANIMATION_RESOURCES_DIR
from led_matrix.common.color import Color

_GAMEFRAME_ANIMATIONS_DIR = ANIMATION_RESOURCES_DIR / "gameframe"


GameframeVariant = AnimationVariant.build_variants_from_files("GameframeVariant",
                                                              search_dir=_GAMEFRAME_ANIMATIONS_DIR,
                                                              glob_str="*")


#TODO: Subfolders have not been implemented yet.
@dataclass(kw_only=True)
class GameframeParameter(AnimationParameter):
    background_color: Color = Color(0, 0, 0)


@dataclass(kw_only=True)
class GameframeSettings(AnimationSettings):
    variant: Optional[AnimationVariant] = None
    parameter: Optional[AnimationParameter] = field(default_factory=GameframeParameter)


@dataclass(kw_only=True)
class _GameframeConfig:
    hold: int = field(default=100, init=False)
    loop: bool = field(default=True, init=False)
    move_x: int = field(default=0, init=False)
    move_y: int = field(default=0, init=False)
    move_loop: bool = field(default=False, init=False)
    pan_off: bool = field(default=False, init=False)
    next_folder: Path | None = field(default=None, init=False)

    gameframe_dir: InitVar[Path]

    def __post_init__(self, gameframe_dir: Path) -> None:
        config_file: Path = gameframe_dir / "config.ini"

        if config_file.is_file():
            parser: ConfigParser = ConfigParser()

            try:
                # first try utf-8 encoding
                parser.read(str(config_file), encoding="utf-8")
            except UnicodeDecodeError:
                # after that try windows encoding
                parser.read(str(config_file), encoding="cp1252")

            self.hold = int(parser.get('animation', 'hold', fallback='100'))
            self.loop = parser.getboolean('animation', 'loop', fallback=True)
            self.move_x = int(parser.get('translate', 'moveX', fallback='0'))
            self.move_y = int(parser.get('translate', 'moveY', fallback='0'))
            self.move_loop = parser.getboolean('translate', 'loop', fallback=False)
            self.pan_off = parser.getboolean('translate', 'panoff', fallback=False)

            next_folder_name: str | None = parser.get('translate', 'nextFolder', fallback=None)
            if next_folder_name is not None:
                self.next_folder = Path(next_folder_name)


class GameframeAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 logger: Logger,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, logger, on_finish_callable)

        if self._settings.variant is None:
            raise RuntimeError("Started Gameframe animation without a variant.")

        self.__gameframe_dir: Path = self._settings.variant.value

        if not self.__gameframe_dir.is_dir():
            raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), self.__gameframe_dir)
        self.__name: str = f"gameframe.{self.__gameframe_dir.name}"

        self.__background_color: tuple[int, int, int] = cast(GameframeParameter,
                                                             self._settings.parameter).background_color.pil_tuple

        self.__global_crop_x: int = 0
        self.__global_crop_y: int = 0

        self.__gameframe_config: _GameframeConfig = _GameframeConfig(gameframe_dir=self.__gameframe_dir)

        self.__frame_list: list[NDArray[np.uint8]] = self.__load_frames()

        if not (self.__gameframe_config.loop or self.__gameframe_config.move_loop):
            self._repeat = 0

        self.__frame_generator = self.__rendered_frames()

        self._set_animation_speed(self.__gameframe_config.hold / 1000)

    def intrinsic_duration(self) -> float:
        return sum(1 for _ in self.__rendered_frames()) * self.__gameframe_config.hold/1000

    def __str__(self) -> str:
        # pylint: disable=C0209
        return (
            "Path: {}\n"
            "Name: {} frames: {} shape: {}\n"
            "hold: {} loop: {} moveX: {} moveY: {} moveloop: {} panoff: {}\n".format(
                self.__gameframe_dir,
                self.__name,
                str(len(self.__frame_list)),
                (
                    self.__frame_list[0].shape
                    if len(self.__frame_list) > 0
                    else "no frames available",
                ),
                self.__gameframe_config.hold,
                self.__gameframe_config.loop,
                self.__gameframe_config.move_x,
                self.__gameframe_config.move_y,
                self.__gameframe_config.move_loop,
                self.__gameframe_config.pan_off
            )
        )

    def __load_frames(self) -> list[NDArray[np.uint8]]:
        frames: list[NDArray[np.uint8]] = []

        bmp_file: Path
        for bmp_file in list(sorted(self.__gameframe_dir.glob("*.bmp"),
                                    key=lambda bmpfile: int(bmpfile.stem))):
            with open(str(bmp_file), 'rb') as f:
                image: Image = pil.open(f)

            background_img: Image
            # if move_x or move_y are set, than multiple images are placed in one
            if self.__gameframe_config.move_x > 0 or self.__gameframe_config.move_y > 0:
                background_img = pil.new(mode='RGB', size=image.size, color=self.__background_color)
                background_img.paste(image)

                # calculate the global crop coordinates for the single images
                if self.__gameframe_config.move_x > 0:
                    self.__global_crop_x = abs(int((self._width - self.__gameframe_config.move_x) / 2))
                if self.__gameframe_config.move_y > 0:
                    self.__global_crop_y = abs(int((self._height - self.__gameframe_config.move_y) / 2))
            else:
                # center (crop) image
                background_img = pil.new(mode='RGB',
                                         size=(self._width, self._height),
                                         color=self.__background_color)

                x: int = int((self._width - image.width) / 2)
                y: int = int((self._height - image.height) / 2)

                background_img.paste(image, (x, y))

            frames.append(np.array(background_img))

            # free memory
            del image

        if len(frames) == 0:
            raise AttributeError

        return frames

    def __rendered_frames(self) -> Generator[NDArray[np.uint8], None, None]:
        """Generator function to iterate through all frames of animation"""
        i: int = 0
        end: int = len(self.__frame_list)

        x: int = self.__global_crop_x
        y: int = self.__global_crop_y

        delta_x: int = self._width
        delta_y: int = self._height

        if end:
            while True:
                frame: NDArray[np.uint8] = self.__frame_list[i]

                h: int
                w: int
                if self.__gameframe_config.pan_off:
                    if self.__gameframe_config.move_x != 0:
                        (h, w, _b) = frame.shape
                        frame = np.pad(frame,
                                       ((0, 0), (w, w), (0, 0)),
                                       'constant', constant_values=0)

                    if self.__gameframe_config.move_y != 0:
                        (h, w, _b) = frame.shape
                        frame = np.pad(frame,
                                       ((h, h), (0, 0), (0, 0)),
                                       'constant', constant_values=0)

                (h, w, _b) = frame.shape

                if self.__gameframe_config.move_x >= 0:
                    cur_x = w - delta_x - x
                else:
                    cur_x = x

                if self.__gameframe_config.move_y >= 0:
                    cur_y = y
                else:
                    cur_y = h - delta_y - y

                frame = frame[cur_y:cur_y+delta_y, cur_x:cur_x+delta_x, :]
                if frame.size == 0:
                    break

                yield frame

                i += 1
                x += abs(self.__gameframe_config.move_x)
                y += abs(self.__gameframe_config.move_y)

                if (
                    (self.__gameframe_config.move_x > 0 and cur_x <= 0)
                    or
                    (self.__gameframe_config.move_x < 0 and cur_x >= (w - delta_x))
                ):
                    break
                    # if self.__move_loop:
                    #     x = 0

                if (
                    (self.__gameframe_config.move_y > 0 and (cur_y + delta_y) >= h)
                    or
                    (self.__gameframe_config.move_y < 0 and cur_y <= 0)
                ):
                    # if self.__move_loop:
                    #     y = 0
                    break

                # if i == end:
                #     if self.__loop or self.__move_loop:
                #         i = 0
                #     else:
                #         break
                if i == end:
                    if (
                        (self.__gameframe_config.loop or self.__gameframe_config.move_loop)
                        and
                        (
                            (
                                (self.__gameframe_config.move_x > 0 and cur_x > 0)
                                or
                                (self.__gameframe_config.move_x < 0 and cur_x < (w - delta_x))
                            ) or
                            (
                                (self.__gameframe_config.move_y > 0 and (cur_y + delta_y) < h)
                                or
                                (self.__gameframe_config.move_y < 0 and cur_y > 0)
                            )
                        )
                    ):
                        i = 0
                    else:
                        break

    def render_next_frame(self) -> bool:
        next_frame: NDArray[np.uint8] | None = next(self.__frame_generator, None)

        if next_frame is not None:
            self._frame_queue.put(next_frame.copy())

            # maybe there's still more to render
            return True

        if self.is_next_iteration():
            # recreate frame generator if another iteration should be started
            self.__frame_generator = self.__rendered_frames()

        # the current iteration has no frames left
        return False


class GameframeController(AbstractAnimationController,
                          animation_name="gameframe",
                          animation_class=GameframeAnimation,
                          settings_class=GameframeSettings,
                          accepts_dynamic_variant=True,
                          is_repeat_supported=True,
                          variant_enum=GameframeVariant,
                          parameter_class=GameframeParameter):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, on_finish_callable)

        _GAMEFRAME_ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)

    def _add_dynamic_variant(self, file_name: str, file_content: BytesIO) -> None:
        # error handling
        if file_name.rsplit(".", 1)[-1].lower() != "zip":
            self._log.error("The new variant file must be a zip-file!")
            return

        with ZipFile(file_content, "r") as zip_file:
            info: list[ZipInfo] = zip_file.infolist()

            if len(info) > 0:
                extract_path: Path

                # check if the root element is a single directory
                if (len(info) > 1 and info[0].is_dir()):
                    # extract the zip-file directly
                    extract_path = _GAMEFRAME_ANIMATIONS_DIR.resolve()

                    if (_GAMEFRAME_ANIMATIONS_DIR / info[0].filename.rsplit(".", 1)[0]).exists():
                        self._log.warning("The variant '%s' already exists.",
                                          info[0].filename.rsplit('.', 1)[0])
                        return
                else:
                    # if not, try to create a directory with the file name
                    extract_path = (_GAMEFRAME_ANIMATIONS_DIR / file_name.rsplit(".", 1)[0]).resolve()

                    if extract_path.exists():
                        self._log.warning("The variant '%s' already exists.",
                                          extract_path.name)
                        return

                    extract_path.mkdir(parents=True)

                # extract the zip file
                zip_file.extractall(path=str(extract_path))

                global GameframeVariant  # pylint: disable=W0603
                GameframeVariant = GameframeVariant.refresh_variants()

            else:
                self._log.error("The zip-file was empty.")

    def _remove_dynamic_variant(self, variant: AnimationVariant) -> None:
        animation_dir: Path = variant.value.resolve()

        # only remove directories that are in the animations directory
        if _GAMEFRAME_ANIMATIONS_DIR in animation_dir.parents:
            shutil.rmtree(str(animation_dir), ignore_errors=True)

            global GameframeVariant  # pylint: disable=W0603
            GameframeVariant = GameframeVariant.refresh_variants()
