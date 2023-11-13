import os
from dataclasses import dataclass
from enum import Enum, auto
from io import BytesIO
from pathlib import Path
from queue import Queue
from threading import TIMEOUT_MAX
from typing import Callable, Generator

import numpy as np
from numpy.typing import NDArray
from PIL import Image as pil
from PIL.Image import Image

from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings, AnimationVariant)
from led_matrix.common import RESOURCES_DIR
from led_matrix.common.alpine import alpine_rw, is_alpine_linux
from led_matrix.common.color import Color
from led_matrix.common.log import eprint

_PICTURES_DIR = RESOURCES_DIR / "animations" / "pictures"


PictureVariant = AnimationVariant.build_variants_from_files("PictureVariant",
                                                            search_dir=_PICTURES_DIR,
                                                            glob_str="*.[pg][ni][gf]")


@dataclass(kw_only=True)
class PictureSettings(AnimationSettings):
    variant: PictureVariant | None = None  # type: ignore


class _PictureType(Enum):
    PNG = auto()
    GIF = auto()


class PictureAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        if self._settings.variant is None:
            raise RuntimeError("Started Gameframe animation without a variant.")

        self.__picture_path: Path = self._settings.variant.value

        self.__image: Image
        self.__picture_type: _PictureType
        self.__frame_generator: Generator[NDArray[np.uint8], None, None]

        if self.__picture_path.suffix == ".gif":
            self.__picture_type = _PictureType.GIF

            self.__image = pil.open(self.__picture_path)

            self.__frame_generator = self.__get_gif_frames()

        elif self.__picture_path.suffix == ".png":
            self.__picture_type = _PictureType.PNG

            self.__image = pil.open(self.__picture_path)

            # showing a static image means we don't need to refresh anything
            self._set_animation_speed(TIMEOUT_MAX)
            self._repeat = -1

            self.__frame_generator = self.__get_png_frames()

        else:
            eprint(f"Only PNG and GIF images supported, not '{self.__picture_path.suffix}'.")
            raise ValueError

    def __get_animation_speed(self) -> float:
        try:
            return int(self.__image.info["duration"]) / 1000
        except KeyError:
            eprint("GIF has no duration in info.")
        except (TypeError, ValueError):
            eprint(f"Cannot convert info[duration]: {self.__image.info['duration']} to int.")

        # default 15 fps
        return 1/15

    def __convert_any_to_rgb(self, image: Image) -> Image:
        bands: tuple[str, ...] = image.getbands()

        if bands == ('R', 'G', 'B', 'A'):
            background = pil.new('RGB', image.size, Color(0, 0, 0).pil_tuple)
            background.paste(image, mask=image.split()[3])
            return background

        if bands != ('R', 'G', 'B'):
            return image.convert('RGB')

        return image

    def __resize_image(self, image: Image, size: tuple[int, int]) -> Image:
        if image.size != size:
            image.thumbnail(size=size)
            frame: Image = pil.new("RGB", size=size)

            img_w, img_h = image.size
            bg_w, bg_h = frame.size
            offset: tuple[int, int] = ((bg_w - img_w) // 2, (bg_h - img_h) // 2)

            frame.paste(image, box=offset)

            return frame

        return image

    def __get_png_frames(self) -> Generator[NDArray[np.uint8], None, None]:
        self.__image = self.__convert_any_to_rgb(self.__image)
        self.__image = self.__resize_image(self.__image, (self._width, self._height))

        yield np.array(self.__image)

    def __get_gif_frames(self) -> Generator[NDArray[np.uint8], None, None]:
        more_frames: bool = True
        while more_frames:
            frame: Image = pil.new("RGBA", self.__image.size)
            frame.paste(self.__image)
            frame = self.__convert_any_to_rgb(frame)
            frame = self.__resize_image(frame, (self._width, self._height))

            try:
                self.__image.seek(self.__image.tell() + 1)
            except EOFError:
                more_frames = False
                self.__image.seek(0)

            yield np.array(frame)

    def render_next_frame(self) -> bool:
        next_frame: NDArray[np.uint8] | None = next(self.__frame_generator, None)

        if next_frame is not None:
            self._frame_queue.put(next_frame.copy())

            if self.__picture_type == _PictureType.GIF:
                self._set_animation_speed(self.__get_animation_speed())

            # maybe there's still more to render
            return True

        if self.is_next_iteration():
            # recreate frame generator if another iteration should be started
            if self.__picture_type == _PictureType.PNG:
                self.__frame_generator = self.__get_png_frames()
            elif self.__picture_type == _PictureType.GIF:
                self.__frame_generator = self.__get_gif_frames()

        # the current iteration has no frames left
        return False

class PictureController(AbstractAnimationController):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, on_finish_callable)

        _PICTURES_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def animation_name(self) -> str:
        return "picture"

    @property
    def animation_class(self) -> type[AbstractAnimation]:
        return PictureAnimation

    @property
    def variant_enum(self) -> type[AnimationVariant] | None:
        return PictureVariant

    @property
    def parameter_class(self) -> type[AnimationParameter] | None:
        return None

    @property
    def settings_class(self) -> type[AnimationSettings]:
        return PictureSettings

    @property
    def default_settings(self) -> AnimationSettings:
        return PictureSettings()

    @property
    def is_repeat_supported(self) -> bool:
        return True

    @property
    def accepts_dynamic_variant(self) -> bool:
        return True

    def _add_dynamic_variant(self, file_name: str, file_content: BytesIO) -> None:
        # error handling
        if file_name.rsplit(".", 1)[-1].lower() not in ("png", "gif"):
            eprint("The new variant file must be a PNG or GIF file!")
            return

        file_path: Path = (_PICTURES_DIR / file_name).resolve()

        def write_file():
            with open(file_path, "wb+") as f:
                f.write(file_content.read())

            global PictureVariant  # pylint: disable=W0603
            PictureVariant = PictureVariant.refresh_variants()

        if is_alpine_linux():
            with alpine_rw():
                write_file()
        else:
            write_file()

    def _remove_dynamic_variant(self, variant: AnimationVariant) -> None:
        animation_file: Path = variant.value.resolve()

        # only remove directories that are in the animations directory
        if animation_file in [p.resolve() for p in _PICTURES_DIR.iterdir()]:
            def remove_file():
                try:
                    os.remove(animation_file)
                except FileNotFoundError:
                    pass

                global PictureVariant  # pylint: disable=W0603
                PictureVariant = PictureVariant.refresh_variants()

            if is_alpine_linux():
                with alpine_rw():
                    remove_file()
            else:
                remove_file()
