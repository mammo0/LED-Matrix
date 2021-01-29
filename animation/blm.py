from enum import Enum
import errno
import os
from pathlib import Path

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController, AnimationSettingsStructure
from common.color import Color
import numpy as np


class BlmParameter(AnimationParameter):
    foregound_color = Color(255, 255, 255)
    background_color = Color(10, 10, 10)
    padding_color = Color(60, 60, 60)


class BlmSettings(AnimationSettingsStructure):
    parameter = BlmParameter


class BlmAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, settings, on_finish_callable):
        super().__init__(width, height, frame_queue, settings, on_finish_callable)

        self.__path = Path(self._settings.variant.value)

        if not self.__path.is_file():
            raise __builtins__.FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.__path)

        self.__load_frames()

        self.__foregound_color = self._settings.parameter.foregound_color.pil_tuple
        self.__background_color = self._settings.parameter.background_color.pil_tuple
        self.__padding_color = self._settings.parameter.padding_color.pil_tuple

        print(self)

    def intrinsic_duration(self):
        ret = 0
        for item in self.frames:
            ret += item["hold"]
        return ret/1000.0

    def __str__(self):
        return "Path: {} file: {} frames: {} shape: {} duration: {}\n"\
               "".format(self.__path,
                         "blm.{}".format(self.__path.stem),
                         str(len(self.frames)),
                         (len(self.frames[0]["frame"]),
                          len(self.frames[0]["frame"][0])) if len(self.frames)
                         else "no frames available",
                         self.intrinsic_duration())

    def __load_frames(self):
        self.frames = []
        with self.__path.open(encoding='latin1') as f:
            hold = 0
            frame = []
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                elif line.startswith("@"):
                    if len(frame):
                        self.frames.append({"hold": hold, "frame": frame})
                    hold = int(line[1:])
                    frame = []
                    continue
                elif len(line):
                    frame.append(list(line))
            if len(frame):
                self.frames.append({"hold": hold, "frame": frame})
        if len(self.frames) == 0:
            raise AttributeError

    def animate(self):
        while not self._stop_event.is_set():
            for frame in self.__rendered_frames():
                if not self._stop_event.is_set():
                    self._frame_queue.put(frame["frame"].copy())
                else:
                    break
                self._stop_event.wait(timeout=frame["hold"]/1000)

            # check repeat
            if not self.is_next_iteration():
                break

    def __rendered_frames(self):
        """
        Generator function to iterate through all frames of animation.
        Cropped to fit matrix size.
        """
        for frame in self.frames:
            try:
                array = np.array(frame["frame"], dtype=np.uint8)
            except Exception:
                continue
            array = np.dstack((array, array, array))

            # indices where to find the ones and the zeros in the frame
            # needed to replace with a color
            ones = array == 1
            zeros = array == 0

            np.putmask(array, ones, self.__foregound_color)
            np.putmask(array, zeros, self.__background_color)

            (h, w, _b) = array.shape

            diff_h = h - self._height

            diff_w = w - self._width

            diff_h_top = abs(diff_h//2)
            diff_h_bottom = abs(diff_h) - diff_h_top

            diff_w_left = abs(diff_w//2)
            diff_w_right = abs(diff_w) - diff_w_left

            # print(h, w, b, diff_h, diff_w, diff_h_top, diff_h_bottom,
            #      diff_w_left, diff_w_right)

            if diff_h < 0:
                # padding
                array = np.pad(array, ((diff_h_top, diff_h_bottom),
                                       (0, 0),
                                       (0, 0)),
                               'constant',
                               constant_values=((self.__padding_color,
                                                 self.__padding_color),
                                                (0, 0), (0, 0)))
            elif diff_h > 0:
                # cropping
                array = array[diff_h_top:-diff_h_bottom, :, :]

            if diff_w < 0:
                # padding
                array = np.pad(array, ((0, 0),
                                       (diff_w_left, diff_w_right),
                                       (0, 0)),
                               'constant',
                               constant_values=((0, 0),
                                                (self.__padding_color,
                                                 self.__padding_color),
                                                (0, 0)))
            elif diff_w > 0:
                # cropping
                array = array[:, diff_w_left:-diff_w_right, :]
            # print(array.shape)

            yield {"hold": frame["hold"], "frame": array}


class BlmController(AbstractAnimationController):
    def __init__(self, width, height, frame_queue, resources_path, on_finish_callable):
        super(BlmController, self).__init__(width, height, frame_queue, resources_path, on_finish_callable)

        self._resources_path = self._resources_path / "animations" / "162-blms"

    @property
    def animation_class(self):
        return BlmAnimation

    @property
    def animation_variants(self):
        blm_animations = {}
        for animation_file in sorted(self._resources_path.glob("*.blm"), key=lambda s: s.name.lower()):
            if animation_file.is_file():
                blm_animations[animation_file.stem] = animation_file.resolve()

        # if no blm animations where found
        if not blm_animations:
            return None

        return Enum("BlmVariant", blm_animations)

    @property
    def animation_parameters(self):
        return BlmParameter

    @property
    def _default_animation_settings(self):
        return BlmSettings

    @property
    def is_repeat_supported(self):
        return True
