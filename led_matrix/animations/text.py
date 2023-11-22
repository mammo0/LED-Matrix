import sys
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from queue import Queue
from typing import Callable, Final, Generator, Optional, cast

import freetype
import numpy as np
from freetype import Bitmap, Face
from freetype.ft_structs import FT_Vector
from numpy.typing import NDArray
from PIL import Image as pil
from PIL.Image import Image

from led_matrix import STATIC_RESOURCES_DIR
from led_matrix.animation.abstract import (AbstractAnimation,
                                           AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings)

_FONTS_DIR: Final[Path] = STATIC_RESOURCES_DIR / "fonts"
_TEXT_FONT: Final[Face] = Face(str(_FONTS_DIR / "LiberationSans-Regular_2.1.2.ttf"))
_EMOJI_FONT: Final[Face] = Face(str(_FONTS_DIR / "twemoji-14.0.2.ttf"))
# often only one char size is available and valid for emoji fonts
# use the last one (should be the largest)
_EMOJI_FONT.set_char_size(_EMOJI_FONT.available_sizes[-1].size)


@dataclass(kw_only=True)
class TextParameter(AnimationParameter):
    text: str = ""
    text_size: int = 12
    steps_per_second: int = 15
    pixels_per_step: int = 1


@dataclass(kw_only=True)
class TextSettings(AnimationSettings):
    parameter: Optional[AnimationParameter] = field(default_factory=TextParameter)


class TextAnimation(AbstractAnimation):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 logger: Logger,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(width, height, frame_queue, settings, logger, on_finish_callable)

        parameter: TextParameter = cast(TextParameter, self._settings.parameter)

        self.__text: str = parameter.text
        self.__text_size: int = parameter.text_size
        self.__steps_per_second: int = parameter.steps_per_second
        self.__pixels_per_step: int = parameter.pixels_per_step

        _TEXT_FONT.set_char_size(self.__text_size * 64)

        np.set_printoptions(threshold=sys.maxsize, linewidth=300)

        self.__frame_generator = self.__generate_frames()

        self._set_animation_speed(1.0 / self.__steps_per_second)

    def __render(self, text: str) -> NDArray[np.uint8]:
        xmin: int = 0
        xmax: int = 0
        ymin: int = 0
        ymax: int = 0

        previous_char: str = "\0"
        pen_x: int = 0
        pen_y: int = 0

        kerning: FT_Vector
        bitmap: Bitmap

        # first pass
        char: str
        for char in text:
            width: int
            rows: int
            top: int
            left: int

            x0: int
            x1: int
            y0: int
            y1: int

            if _TEXT_FONT.get_char_index(char):
                _TEXT_FONT.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)  # type: ignore # pylint: disable=E1101

                kerning = _TEXT_FONT.get_kerning(previous_char, char)
                previous_char = char
                bitmap = _TEXT_FONT.glyph.bitmap

                width = _TEXT_FONT.glyph.bitmap.width
                rows = _TEXT_FONT.glyph.bitmap.rows
                top = _TEXT_FONT.glyph.bitmap_top
                left = _TEXT_FONT.glyph.bitmap_left

                pen_x += (kerning.x >> 6)

                x0 = pen_x + left
                x1 = x0 + width
                y0 = pen_y - (rows - top)
                y1 = y0 + rows

                xmin, xmax = min(xmin, x0),  max(xmax, x1)
                ymin, ymax = min(ymin, y0), max(ymax, y1)
                pen_x += (_TEXT_FONT.glyph.advance.x >> 6)
                pen_y += (_TEXT_FONT.glyph.advance.y >> 6)
                # print(("char: {} width: {} rows: {} top: {} left: {} "
                #        "kernx: {} xmin: {} xmax: {} ymin: {} ymax: {} "
                #        "pen_x: {} pen_y {}").format(c, width, rows, top, left,
                #                                     (kerning.x >> 6), xmin, xmax, ymin, ymax,
                #                                     pen_x, pen_y))
            elif _EMOJI_FONT.get_char_index(char):
                previous_char = "\0"

                width = self.__text_size
                rows = self.__text_size
                top = self.__text_size - 3
                left = 0

                x0 = pen_x + left
                x1 = x0 + width
                y0 = pen_y - (rows - top)
                y1 = y0 + rows

                xmin, xmax = min(xmin, x0),  max(xmax, x1)
                ymin, ymax = min(ymin, y0), max(ymax, y1)
                pen_x += self.__text_size

        text_array: NDArray[np.uint8] = np.zeros((ymax-ymin, xmax-xmin, 3), dtype=np.uint8)

        # second pass
        previous_char = "\0"
        pen_x, pen_y = 0, 0
        for char in text:
            bitmap_array: NDArray[np.uint8]

            if _TEXT_FONT.get_char_index(char):
                _TEXT_FONT.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)  # type: ignore # pylint: disable=E1101

                kerning = _TEXT_FONT.get_kerning(previous_char, char)
                previous_char = char
                bitmap = _TEXT_FONT.glyph.bitmap

                width = _TEXT_FONT.glyph.bitmap.width
                rows = _TEXT_FONT.glyph.bitmap.rows
                top = _TEXT_FONT.glyph.bitmap_top
                left = _TEXT_FONT.glyph.bitmap_left

                pen_x += (kerning.x >> 6)

                x = pen_x - xmin + left
                y = pen_y - ymin - (rows - top)

                bitmap_array = self.__unpack_mono_bitmap(bitmap)
                # Z = np.array(bitmap.buffer, dtype=np.uint8).reshape(rows,
                #                                                     width)
                bitmap_array = np.repeat(bitmap_array, 3, axis=1).reshape(rows, width, 3)

                text_array[y:y+rows, x:x+width] |= bitmap_array[::-1, ::1]

                pen_x += (_TEXT_FONT.glyph.advance.x >> 6)
                pen_y += (_TEXT_FONT.glyph.advance.y >> 6)
            elif _EMOJI_FONT.get_char_index(char):
                previous_char = "\0"

                width = self.__text_size
                rows = self.__text_size
                top = self.__text_size - 3
                left = 0

                x = pen_x - xmin + left
                y = pen_y - ymin - (rows - top)

                bitmap_array = self.__get_color_char(char)
                text_array[y:y+rows, x:x+width] |= bitmap_array[::-1, ::1]

                pen_x += self.__text_size

        return text_array[::-1, ::1]

    @staticmethod
    def __unpack_mono_bitmap(bitmap: Bitmap) -> NDArray[np.uint8]:
        data: bytearray = bytearray(bitmap.rows * bitmap.width)

        y: int
        for y in range(bitmap.rows):
            byte_index: int
            for byte_index in range(bitmap.pitch):
                byte_value: int = bitmap.buffer[y * bitmap.pitch + byte_index]

                num_bits_done: int = byte_index * 8
                rowstart: int = y * bitmap.width + byte_index * 8

                bit_index: int
                for bit_index in range(min(8, bitmap.width - num_bits_done)):
                    bit: int = byte_value & (1 << (7 - bit_index))
                    data[rowstart + bit_index] = 255 if bit else 0

        return np.array(data).reshape(bitmap.rows, bitmap.width)

    def __get_color_char(self, char: str) -> NDArray[np.uint8]:
        _EMOJI_FONT.load_char(char, freetype.FT_LOAD_COLOR)  # type: ignore # pylint: disable=E1101

        bitmap: Bitmap = _EMOJI_FONT.glyph.bitmap
        bitmap_array: NDArray[np.uint8] = np.array(bitmap.buffer,
                                                   dtype=np.uint8).reshape((bitmap.rows, bitmap.width, 4))

        rgb: NDArray[np.uint8] = self.__convert_bgra_to_rgb(bitmap_array)

        im: Image = pil.fromarray(rgb)
        # image offset
        im = im.crop((0, 4, im.width, im.height))
        im = im.resize((self.__text_size, self.__text_size))

        return np.array(im)

    def __convert_bgra_to_rgb(self, buf: NDArray[np.uint8]) -> NDArray[np.uint8]:
        blue: NDArray[np.uint8] = buf[:, :, 0]
        green: NDArray[np.uint8] = buf[:, :, 1]
        red: NDArray[np.uint8] = buf[:, :, 2]

        return np.dstack((red, green, blue))

    def __generate_frames(self) -> Generator[NDArray[np.uint8], None, None]:
        if self.__steps_per_second <= 0 or self.__pixels_per_step < 1:
            return

        buf: NDArray[np.uint8] = self.__render(self.__text)

        height: int
        height, _width, _nbytes = buf.shape

        h_pad_0: int = self._height
        h_pad_1: int = self._width + self.__pixels_per_step
        v_pad_0: int = 0
        v_pad_1: int = 0

        if height < self._height:
            v_pad_0 = int((self._height - height)/2)
            v_pad_1 = self._height - height - v_pad_0

        buf = np.pad(array=buf,
                     pad_width=((v_pad_0, v_pad_1), (h_pad_0, h_pad_1), (0, 0)),
                     mode='constant',
                     constant_values=0)

        i: int
        for i in range(0, buf.shape[1] - self._width, self.__pixels_per_step):
            if self._stop_event.is_set():
                break

            yield buf[0:self._height, i:i+self._width, :]

    def render_next_frame(self) -> bool:
        next_frame: NDArray[np.uint8] | None = next(self.__frame_generator, None)

        if next_frame is not None:
            self._frame_queue.put(next_frame.copy())

            # maybe there's still more to render
            return True

        if self.is_next_iteration():
            # recreate frame generator if another iteration should be started
            self.__frame_generator = self.__generate_frames()

        # the current iteration has no frames left
        return False


class TextController(AbstractAnimationController,
                     animation_name="text",
                     animation_class=TextAnimation,
                     settings_class=TextSettings,
                     default_settings=TextSettings(),
                     accepts_dynamic_variant=False,
                     is_repeat_supported=True,
                     parameter_class=TextParameter):
    pass
