import errno
import os
from pathlib import Path

from animation.abstract import AbstractAnimation
import numpy as np


class BlmAnimation(AbstractAnimation):
    def __init__(self, width, height, frame_queue, repeat, path,
                 foregound_color=(255, 255, 255),
                 background_color=(10, 10, 10),
                 padding_color=(60, 60, 60)):
        super().__init__(width, height, frame_queue, repeat)

        self.path = Path(path)
        if not self.path.is_file():
            raise __builtins__.FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        self.name = "blm.{}".format(self.path.stem)

        self.load_frames()

        self.foregound_color = foregound_color
        self.background_color = background_color
        self.padding_color = padding_color

        print(self)

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
            if self.repeat > 0:
                self.repeat -= 1
            elif self.repeat == 0:
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

    @property
    def kwargs(self):
        return {"width": self.width, "height": self.height,
                "frame_queue": self.frame_queue, "repeat": self.repeat,
                "path": self.path, "foregound_color": self.foregound_color,
                "background_color": self.background_color,
                "padding_color": self.padding_color}
