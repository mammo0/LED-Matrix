"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC
import json
from threading import Thread, Event
import time

from common import eprint


class AnimationParameterMeta(type):
    def __new__(metacls, cls, bases, classdict):
        # do not do this when initializing the main class
        if cls != "AnimationParameter":
            # get all static defined variables
            params = {k: v for k, v in classdict.items() if not (k.startswith("_") or callable(v))}

            # and remove them from the normal class dictionary
            for key in params.keys():
                classdict.pop(key)
        else:
            params = {}

        # add new attributes
        parameter_cls = super().__new__(metacls, cls, bases, classdict)
        parameter_cls._params_map_ = params
        parameter_cls._params_names_ = list(params)

        return parameter_cls

    def __dir__(cls):
        return (['__class__', '__doc__', '__members__', '__module__'] +
                cls._params_map_)

    def __getattr__(cls, name):
        try:
            return cls._params_map_[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(cls, name, value):
        params_map = cls.__dict__.get('_params_map_', {})
        if name in params_map:
            raise AttributeError('Cannot reassign members.')
        super().__setattr__(name, value)

    def __delattr__(cls, attr):
        if attr in cls._member_map_:
            raise AttributeError(
                    "%s: cannot delete Enum member." % cls.__name__)
        super().__delattr__(attr)

    @property
    def names(cls):
        return cls._params_names_


class AnimationParameter(metaclass=AnimationParameterMeta):
    def __init__(self, **params):
        # preserve the class map
        self._params_map_ = self._params_map_.copy()

        # overwrite values in the instance
        for k, v in params.items():
            if k in self._params_map_:
                self._params_map_[k] = v

    def __dir__(self):
        return (['__class__', '__doc__', '__module__'] +
                self._params_map_)

    def __getattr__(self, name):
        # this method is needed to access the variables of the instance (not the class!)
        try:
            return self._params_map_[name]
        except KeyError:
            raise AttributeError(name) from None


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

        self.animation_thread = None  # this variable contains the animation thread

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

    def start_animation(self, variant, parameter=None, repeat=0):
        """
        Start a specific variant (see 'anmimation_variants' property above) of an animation with
        an optional parameter.
        @param repeat:   0: no repeat
                        -1: forever
                       > 0: x-times
        """
        # we're expecting a JSON string as parameter that contains the colors
        options = self._validate_parameter(parameter)
        self.animation_thread = self.animation_class(width=self.width, height=self.height,
                                                     frame_queue=self.frame_queue,
                                                     repeat=repeat, variant=variant,
                                                     **options)

        # start the animation thread
        self.animation_thread.start()

    def _validate_parameter(self, parameter):
        # if no parameter is specified
        if (not parameter or
                self.animation_parameters is None):
            return {}

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

    def stop_antimation(self):
        # stop the animation if it's currently running.
        if (self.animation_thread and
                isinstance(self.animation_thread, AbstractAnimation) and
                self.animation_thread.is_alive()):
            self.animation_thread.stop_and_wait()
