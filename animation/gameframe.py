import configparser
import errno
import os
from pathlib import Path
import shutil
from zipfile import ZipFile

from PIL import Image

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController, _AnimationSettingsStructure
from common import eprint, RESOURCES_DIR
from common.alpine import alpine_rw, is_alpine_linux
from common.color import Color
from common.enum import DynamicEnumMeta, DynamicEnum
import numpy as np


_ANIMATIONS_DIR = RESOURCES_DIR / "animations" / "gameframe"


# TODO: Subfolders have not been implemented yet.
class GameframeParameter(AnimationParameter):
    background_color = Color(0, 0, 0)


class _GameframeVariantMeta(DynamicEnumMeta):
    @property
    def dynamic_enum_dict(cls):
        gameframe_animations = {}
        for animation_dir in sorted(_ANIMATIONS_DIR.glob("*"), key=lambda s: s.name.lower()):
            if animation_dir.is_dir():
                gameframe_animations[animation_dir.name] = animation_dir.resolve()

        gameframe_animations

        return gameframe_animations


class GameframeVariant(DynamicEnum, metaclass=_GameframeVariantMeta):
    pass


class GameframeSettings(_AnimationSettingsStructure):
    variant = GameframeVariant._empty
    parameter = GameframeParameter


class GameframeAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, settings, on_finish_callable):
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        self.__folder = Path(self._settings.variant.value)

        if not self.__folder.is_dir():
            raise __builtins__.NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), self.__folder)
        self.__name = "gameframe.{}".format(self.__folder.name)

        self.__background_color = self._settings.parameter.background_color.pil_tuple

        self.__load_frames()
        self.__read_config()

        if not (self.__loop or self.__move_loop):
            self._repeat = 0

        self.__frame_generator = self.__rendered_frames()

        self._set_animation_speed(self.__hold / 1000)

    def intrinsic_duration(self):
        return sum(1 for _ in self.__rendered_frames()) * self.__hold/1000

    def __str__(self):
        return "Path: {}\n"\
               "Name: {} frames: {} shape: {}\n"\
               "hold: {} loop: {} moveX: {} moveY: {} moveloop: {} "\
               "panoff: {}\n"\
               "".format(self.__folder,
                         self.__name,
                         str(len(self.frames)),
                         self.frames[0].shape if len(self.frames) else
                         "no frames available",
                         self.__hold,
                         self.__loop,
                         self.__moveX,
                         self.__moveY,
                         self.__move_loop,
                         self.__panoff)

    def __load_frames(self):
        self.frames = []
        for path in list(sorted(self.__folder.glob("*.bmp"),
                                key=lambda bmpfile: int(bmpfile.stem))):
            with open(str(path), 'rb') as f:
                image = Image.open(f)
                # center (crop) image
                background_img = Image.new(mode='RGB', size=(self._width, self._height), color=self.__background_color)
                x = (self._width - image.width) / 2
                y = (self._height - image.height) / 2
                background_img.paste(image, (int(x), int(y)))
                self.frames.append(np.array(background_img))
            image = None
        if len(self.frames) == 0:
            raise AttributeError

    def __read_config(self):
        self.__hold = 100
        self.__loop = True
        self.__moveX = 0
        self.__moveY = 0
        self.__move_loop = False
        self.__panoff = False
        self.__nextFolder = None

        config = self.__folder.joinpath("config.ini")
        if config.is_file():
            parser = configparser.ConfigParser()
            parser.read(str(config))
            self.__hold = int(parser.get('animation', 'hold', fallback='100'))
            self.__loop = parser.getboolean('animation', 'loop', fallback=True)
            self.__moveX = int(parser.get('translate', 'moveX', fallback='0'))
            self.__moveY = int(parser.get('translate', 'moveY', fallback='0'))
            self.__move_loop = \
                parser.getboolean('translate', 'loop', fallback=False)
            self.__panoff = \
                parser.getboolean('translate', 'panoff', fallback=False)
            self.__nextFolder = \
                parser.getboolean('translate', 'nextFolder', fallback=None)

    def __rendered_frames(self):
        """Generator function to iterate through all frames of animation"""
        i = 0
        end = len(self.frames)

        x = 0
        y = 0
        DX = self._width
        DY = self._height

        if end:
            while True:
                frame = self.frames[i]
                if self.__panoff:
                    if self.__moveX != 0:
                        (h, w, _b) = frame.shape
                        frame = np.pad(frame,
                                       ((0, 0), (w, w), (0, 0)),
                                       'constant', constant_values=0)
                    if self.__moveY != 0:
                        (h, w, _b) = frame.shape
                        frame = np.pad(frame,
                                       ((h, h), (0, 0), (0, 0)),
                                       'constant', constant_values=0)
                (h, w, _b) = frame.shape
                if self.__moveX >= 0:
                    cur_x = w - DX - x
                else:
                    cur_x = x
                if self.__moveY >= 0:
                    cur_y = y
                else:
                    cur_y = h - DY - y

                yield frame[cur_y:cur_y+DY, cur_x:cur_x+DX, :]

                i += 1
                x += abs(self.__moveX)
                y += abs(self.__moveY)

                if (self.__moveX > 0 and cur_x <= 0) or \
                   (self.__moveX < 0 and cur_x >= (w - DX)):
                    break
                    # if self.__move_loop:
                    #     x = 0

                if (self.__moveY > 0 and (cur_y + DY) >= h) or \
                   (self.__moveY < 0 and cur_y <= 0):
                    # if self.__move_loop:
                    #     y = 0
                    break

                # if i == end:
                #     if self.__loop or self.__move_loop:
                #         i = 0
                #     else:
                #         break
                if i == end:
                    if ((self.__loop or self.__move_loop) and
                        (((self.__moveX > 0 and cur_x > 0) or
                          (self.__moveX < 0 and cur_x < (w - DX))) or
                         ((self.__moveY > 0 and (cur_y + DY) < h) or
                          (self.__moveY < 0 and cur_y > 0)))):
                        i = 0
                    else:
                        break

    def render_next_frame(self):
        next_frame = next(self.__frame_generator, None)

        if next_frame is not None:
            self._frame_queue.put(next_frame.copy())

            # maybe there's still more to render
            return True
        elif self.is_next_iteration():
            # recreate frame generator if another iteration should be started
            self.__frame_generator = self.__rendered_frames()

        # the current iteration has no frames left
        return False


class GameframeController(AbstractAnimationController):
    def __init__(self, width, height, frame_queue, on_finish_callable):
        super(GameframeController, self).__init__(width, height, frame_queue, on_finish_callable)

        _ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def animation_class(self):
        return GameframeAnimation

    @property
    def animation_variants(self):
        return GameframeVariant

    @property
    def animation_parameters(self):
        return GameframeParameter

    @property
    def default_animation_settings(self):
        return GameframeSettings

    @property
    def is_repeat_supported(self):
        return True

    @property
    def accepts_dynamic_variant(self):
        return True

    def _add_dynamic_variant(self, file_name, file_content):
        # error handling
        if file_name.rsplit(".", 1)[-1].lower() != "zip":
            eprint("The new variant file must be a zip-file!")
            return

        with ZipFile(file_content, "r") as zip_file:
            info = zip_file.infolist()

            if len(info) > 0:
                def extract_zip():
                    # check if the root element is a single directory
                    if (len(info) > 1 or not info[0].is_dir()):
                        # if not, try to create a directory with the file name
                        extract_path = (_ANIMATIONS_DIR / file_name.rsplit(".", 1)[0]).resolve()

                        if extract_path.exists():
                            eprint(f"The variant '{extract_path.name}' already exists.")
                            return
                        else:
                            extract_path.mkdir(parents=True)
                    else:
                        # otherwise extract the zip-file directly
                        extract_path = _ANIMATIONS_DIR.resolve()

                        if (_ANIMATIONS_DIR / info[0].filename.rsplit(".", 1)[0]).exists():
                            eprint(f"The variant '{info[0].filename.rsplit('.', 1)[0]}' already exists.")
                            return

                    # extract the zip file
                    zip_file.extractall(path=str(extract_path))

                if is_alpine_linux():
                    with alpine_rw():
                        extract_zip()
                else:
                    extract_zip()

            else:
                eprint("The zip-file was empty.")

    def _remove_dynamic_variant(self, variant):
        animation_dir = Path(variant.value).resolve()

        # only remove directories that are in the animations directory
        if animation_dir in [p.resolve() for p in _ANIMATIONS_DIR.iterdir()]:
            if is_alpine_linux():
                with alpine_rw():
                    shutil.rmtree(str(animation_dir), ignore_errors=True)
            else:
                shutil.rmtree(str(animation_dir), ignore_errors=True)
