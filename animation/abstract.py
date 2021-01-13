"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC
from threading import Thread
import time


class AbstractAnimation(ABC, Thread):
    def __init__(self, width, height, frame_queue, repeat):
        super().__init__(daemon=True)
        self.width = width  # width of frames to produce
        self.height = height  # height of frames to produce
        self.frame_queue = frame_queue  # queue to put frames onto
        self.repeat = repeat  # 0: no repeat, -1: forever, > 0: x-times

        self._running = False  # query this often! exit self.animate quickly

    def run(self):
        """This is the run method from threading.Thread"""
        # TODO threading.Barrier to sync with ribbapi
        # print("Starting")

        self.started = time.time()
        self._running = True
        self.animate()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def stop(self):
        self._running = False

    @abstractmethod
    def animate(self):
        """This is where frames are put to the frame_queue in correct time"""

    @property
    @abstractmethod
    def kwargs(self):
        """This method must return all init args to be able to create identical
        animation. Repeat should reflect current repeats left."""

    # @property
    # @abstractmethod
    # def intrinsic_duration(self):
    #     """This method should return the duration for one run of the animation,
    #     based on frame count and duration of each frame. In milliseconds.
    #     Return -1 for animations that do not have an intrinsic_duration. The
    #     basic idea is to let animations run for only a default amount of time.
    #     Longer animations should be supported by asking for their intrinsic
    #     duration. Of course repeats must be set to 0 then."""


class AbstractAnimationController(ABC):
    def __init__(self, width, height, frame_queue):
        self.width = width  # width of frames to produce
        self.height = height  # height of frames to produce
        self.frame_queue = frame_queue  # queue to put frames onto

    @property
    @abstractmethod
    def animation_variants(self):
        """
        @return: An enum object that holds the variants of the underlying animation. Or None if there are no variants.
        """

    @abstractmethod
    def start_animation(self, variant, parameter=None, repeat=0):
        """
        Start a specific variant (see 'anmimation_variants' property above) of an animation with
        an optional parameter.
        @param repeat:   0: no repeat
                        -1: forever
                       > 0: x-times
        """

    @abstractmethod
    def stop_antimation(self):
        """
        Stop the animation if it's currently running.
        """
