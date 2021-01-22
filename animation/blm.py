from enum import Enum
import errno
import os
from pathlib import Path

from animation.abstract import AbstractAnimation, AnimationParameter, \
    AbstractAnimationController
from common.color import Color
import numpy as np


class BlmParameter(AnimationParameter):
    foregound_color = Color(255, 255, 255)
    background_color = Color(10, 10, 10)
    padding_color = Color(60, 60, 60)


class BlmAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat,
                 **kwargs):
        super().__init__(width, height, frame_queue, repeat)

        self.path = Path(kwargs.pop("variant").value)

        self.params = BlmParameter(**kwargs)

        if not self.path.is_file():
            raise __builtins__.FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.path)
        self.name = "blm.{}".format(self.path.stem)

        self.load_frames()

        self.foregound_color = self.params.foregound_color.pil_tuple
        self.background_color = self.params.background_color.pil_tuple
        self.padding_color = self.params.padding_color.pil_tuple

        print(self)

    @property
    def variant_value(self):
        return self.path

    @property
    def parameter_instance(self):
        return self.params

    def intrinsic_duration(self):
        ret = 0
        for item in self.frames:
            ret += item["hold"]
        return ret/1000.0

    def __str__(self):
        return "Path: {} file: {} frames: {} shape: {} duration: {}\n"\
               "".format(self.path,
                         self.name,
                         str(len(self.frames)),
                         (len(self.frames[0]["frame"]),
                          len(self.frames[0]["frame"][0])) if len(self.frames)
                         else "no frames available",
                         self.intrinsic_duration())

    def load_frames(self):
        self.frames = []
        with self.path.open(encoding='latin1') as f:
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
            for frame in self.rendered_frames():
                if not self._stop_event.is_set():
                    self.frame_queue.put(frame["frame"].copy())
                else:
                    break
                self._stop_event.wait(timeout=frame["hold"]/1000)

            # check repeat
            if not self.is_repeat():
                break

    def rendered_frames(self):
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

            np.putmask(array, ones, self.foregound_color)
            np.putmask(array, zeros, self.background_color)

            (h, w, _b) = array.shape

            diff_h = h - self.height

            diff_w = w - self.width

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
                               constant_values=((self.padding_color,
                                                 self.padding_color),
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
                                                (self.padding_color,
                                                 self.padding_color),
                                                (0, 0)))
            elif diff_w > 0:
                # cropping
                array = array[:, diff_w_left:-diff_w_right, :]
            # print(array.shape)

            yield {"hold": frame["hold"], "frame": array}


class BlmController(AbstractAnimationController):
    def __init__(self, width, height, frame_queue, resources_path):
        super(BlmController, self).__init__(width, height, frame_queue, resources_path)

        self.resources_path = self.resources_path / "animations" / "162-blms"

    @property
    def animation_class(self):
        return BlmAnimation

    @property
    def animation_variants(self):
        blm_animations = {}
        for animation_file in sorted(self.resources_path.glob("*.blm"), key=lambda s: s.name.lower()):
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
    def is_repeat_supported(self):
        return True
