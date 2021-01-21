"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC, ABCMeta
import ctypes
import json
from threading import Thread, Event
import threading
import time

from simple_classproperty import ClasspropertyMeta, classproperty

from common import eprint
from common.structure import Structure


class AnimationParameter(Structure):
    def __init__(self, **params):
        # overwrite values in the instance
        for k, v in params.items():
            if k in self.names:
                # try to cast values to the default type
                # because not all types are supported by JSON
                default_type = type(self._params_map_[k])
                setattr(self, k, default_type(v))


class AbstractAnimation(ABC, Thread):
    def __init__(self, width, height, frame_queue, repeat):
        super().__init__(daemon=True)
        self.width = width  # width of frames to produce
        self.height = height  # height of frames to produce
        self.frame_queue = frame_queue  # queue to put frames onto
        self.repeat = repeat  # 0: no repeat, -1: forever, > 0: x-times

        self._stop_event = Event()  # query this often! exit self.animate quickly

    def run(self):
        """This is the run method from threading.Thread"""
        # TODO threading.Barrier to sync with ribbapi
        # print("Starting")

        self.started = time.time()
        self.animate()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def stop_and_wait(self):
        self._stop_event.set()
        self.join(timeout=5)

    @abstractmethod
    def animate(self):
        """This is where frames are put to the frame_queue in correct time"""

    @property
    def thread_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for t_id, thread in threading._active.items():
            if thread is self:
                return t_id

        # no id found
        return -1

    # @property
    # @abstractmethod
    # def intrinsic_duration(self):
    #     """This method should return the duration for one run of the animation,
    #     based on frame count and duration of each frame. In milliseconds.
    #     Return -1 for animations that do not have an intrinsic_duration. The
    #     basic idea is to let animations run for only a default amount of time.
    #     Longer animations should be supported by asking for their intrinsic
    #     duration. Of course repeats must be set to 0 then."""


class AbstractAnimationControllerMeta(ABCMeta, ClasspropertyMeta):
    """
    Dummy class for chaining meta classes
    """


class AbstractAnimationController(metaclass=AbstractAnimationControllerMeta):
    def __init__(self, width, height, frame_queue, resources_path):
        self.width = width  # width of frames to produce
        self.height = height  # height of frames to produce
        self.frame_queue = frame_queue  # queue to put frames onto
        self.resources_path = resources_path  # path to the 'resources' directory

        self.animation_thread = None  # this variable contains the animation thread

        self.animation_running = Event()

    @classproperty
    def animation_name(cls):
        return cls.__module__.rpartition(".")[-1]

    @property
    @abstractmethod
    def animation_class(self):
        """
        @return: The animation class.
        """

    @property
    @abstractmethod
    def animation_variants(self):
        """
        @return: An enum object that holds the variants of the underlying animation. Or None if there are no variants.
        """

    @property
    @abstractmethod
    def animation_parameters(self):
        """
        @return: A subclass of AnimationParameter that holds the parameters of the underlying animation.
                 Or None if there are no parameters.
        """

    def start_animation(self, variant=None, parameter=None, repeat=0):
        """
        Start a specific variant (see 'anmimation_variants' property above) of an animation with
        an optional parameter.
        @param repeat:   0: no repeat
                        -1: forever
                       > 0: x-times
        """
        # parse the parameters
        options = self._validate_parameter(parameter)

        if variant:
            if isinstance(variant, self.animation_variants):
                options["variant"] = variant
            else:
                try:
                    options["variant"] = self.animation_variants[variant]
                except KeyError:
                    eprint("The variant '%s' does not exist!" % variant)
                    eprint("Available variants: %s" % ", ".join(self.animation_variants._member_names_))

        self.animation_thread = self.animation_class(width=self.width, height=self.height,
                                                     frame_queue=self.frame_queue, repeat=repeat,
                                                     **options)

        # start the animation thread
        self.animation_thread.start()

        # mark the animation as running
        self.animation_running.set()

    def _validate_parameter(self, parameter):
        # if no parameter is specified
        if (not parameter or
                self.animation_parameters is None):
            return {}

        # an instance of AnimationParameter could also be supplied
        if isinstance(parameter, AnimationParameter):
            # convert it to a dictionary
            return dict(parameter)

        if len(self.animation_parameters.names) == 1:
            # this is the only possible parameter, so pass it as it is
            return {self.animation_parameters.names[0]: parameter}

        # otherwise there are multiple parameters coded in a JSON string
        try:
            parsed_p = json.loads(parameter)
        except ValueError:
            eprint("[Clock] Parameter could not be parsed! Is it valid JSON?")
            return {}

        return parsed_p

    def stop_animation(self):
        # stop the animation if it's currently running.
        if (self.animation_thread and
                self.animation_thread.is_alive()):
            self.animation_thread.stop_and_wait()

            # if the thread is still alive, try to kill it
            if self.animation_thread.is_alive():
                thread_id = self.animation_thread.thread_id
                if thread_id != -1:
                    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                                     ctypes.py_object(SystemExit))
                    if res > 1:
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                        eprint("Exception during killing of animation '%s'!" % self.animation_name)
                        eprint("It may be saver to restart the program.")

        # release running event
        self.animation_running.clear()
