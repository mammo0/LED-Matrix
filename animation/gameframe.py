import configparser
from enum import Enum
import errno
import os
from pathlib import Path

from PIL import Image

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController
from common.color import Color
import numpy as np


# TODO: Subfolders have not been implemented yet.
class GameframeParameter(AnimationParameter):
    background_color = Color(0, 0, 0)


class GameframeAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat, on_finish_callable,
                 **kwargs):
        super().__init__(width, height, frame_queue, repeat, on_finish_callable)

        self.__folder = Path(kwargs.pop("variant").value)

        self.__params = GameframeParameter(**kwargs)

        if not self.__folder.is_dir():
            raise __builtins__.NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), self.__folder)
        self.__name = "gameframe.{}".format(self.__folder.__name)

        self.__background_color = self.__params.background_color.pil_tuple

        self.__load_frames()
        self.__read_config()

        if not (self.__loop or self.__move_loop):
            self._repeat = 0

        print(self.__name, self.intrinsic_duration())

    @property
    def variant_value(self):
        return self.__folder

    @property
    def parameter_instance(self):
        return self.__params

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

    def animate(self):
        while not self._stop_event.is_set():
            for frame in self.__rendered_frames():
                if not self._stop_event.is_set():
                    self._frame_queue.put(frame.copy())
                else:
                    break
                self._stop_event.wait(timeout=self.__hold/1000)
                # if (time.time() - self.started) > self.duration:
                #     break

            # check repeat
            if not self.is_next_iteration():
                break


class GameframeController(AbstractAnimationController):
    def __init__(self, width, height, frame_queue, resources_path, on_finish_callable):
        super(GameframeController, self).__init__(width, height, frame_queue, resources_path, on_finish_callable)

        self._resources_path = self._resources_path / "animations" / "gameframe"

    @property
    def animation_class(self):
        return GameframeAnimation

    @property
    def animation_variants(self):
        gameframe_animations = {}
        for animation_dir in sorted(self._resources_path.glob("*"), key=lambda s: s.name.lower()):
            if animation_dir.is_dir():
                gameframe_animations[animation_dir.name] = animation_dir.resolve()

        # if no blm animations where found
        if not gameframe_animations:
            return None

        return Enum("GameframeVariant", gameframe_animations)

    @property
    def animation_parameters(self):
        return GameframeParameter

    @property
    def is_repeat_supported(self):
        return True
