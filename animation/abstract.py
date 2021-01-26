"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC, ABCMeta
import json
from threading import Thread, Event

from simple_classproperty import ClasspropertyMeta, classproperty

from common import eprint
from common.structure import Structure


class AnimationParameter(Structure):
    def __init__(self, **params):
        # safe the default types
        self.__default_types = {
            k: type(v) for k, v in self._params_map_.items()
        }
        self._params_map_ = self._params_map_.copy()

        # overwrite values in the instance
        for k, v in params.items():
            if k in self.names:
                # try to cast values to the default type
                # because not all types are supported by JSON
                self._params_map_[k] = self.__default_types[k](v)


class AbstractAnimation(ABC, Thread):
    def __init__(self, width, height, frame_queue, repeat, on_finish_callable):
        super().__init__(daemon=True)
        self._width = width  # width of frames to produce
        self._height = height  # height of frames to produce
        self._frame_queue = frame_queue  # queue to put frames onto
        self._repeat = repeat  # 0: no repeat, -1: forever, > 0: x-times
        self.__remaining_repeat = repeat - 1
        self.__on_finish_callable = on_finish_callable

        self._stop_event = Event()  # query this often! exit self.animate quickly

    def run(self):
        """This is the run method from threading.Thread"""
        try:
            self.animate()
        except Exception as e:
            eprint("During the execution of the animation the following error occurred:")
            eprint(repr(e))
        finally:
            # now the animation has stopped, so call the finish callable
            self.__on_finish_callable()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def stop_and_wait(self):
        self._stop_event.set()
        self.join()

    def is_next_iteration(self):
        # no repeat
        if self._repeat == 0:
            return False
        # infinity repeat
        elif self._repeat == -1:
            return True
        else:
            # check remaining repeat cycles
            if self.__remaining_repeat > 0:
                self.__remaining_repeat -= 1
                return True
            else:
                return False

    @abstractmethod
    def animate(self):
        """This is where frames are put to the frame_queue in correct time"""

    @property
    @abstractmethod
    def variant_value(self):
        """Return the current variant value of this animation."""

    @property
    @abstractmethod
    def parameter_instance(self):
        """Return the current parameter of this animation."""

    @property
    def repeat_value(self):
        return self._repeat

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
    def __init__(self, width, height, frame_queue, resources_path, on_finish_callable):
        self.__width = width  # width of frames to produce
        self.__height = height  # height of frames to produce
        self.__frame_queue = frame_queue  # queue to put frames onto
        self._resources_path = resources_path  # path to the 'resources' directory
        self.__on_finish_callable = on_finish_callable  # this gets called whenever an animation stops/finishes

        self.__animation_thread = None  # this variable contains the animation thread

        self.__animation_running = Event()

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

    @property
    def current_variant(self):
        if (self.__animation_running.is_set() and
                self.__animation_thread and
                self.__animation_thread.is_alive()):
            return self.animation_variants(self.__animation_thread.variant_value)
        else:
            return None

    @property
    def current_parameter(self):
        if (self.__animation_running.is_set() and
                self.__animation_thread and
                self.__animation_thread.is_alive()):
            return self.__animation_thread.parameter_instance
        else:
            return None

    @property
    @abstractmethod
    def is_repeat_supported(self):
        """
        @return: True if the repeat value is supported by the animation. False otherwise.
        """

    @property
    def current_repeat_value(self):
        if (self.__animation_running.is_set() and
                self.__animation_thread and
                self.__animation_thread.is_alive()):
            return self.__animation_thread.repeat_value
        else:
            return None

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

        if variant and self.animation_variants is not None:
            if isinstance(variant, self.animation_variants):
                options["variant"] = variant
            else:
                try:
                    options["variant"] = self.animation_variants[variant]
                except KeyError:
                    eprint("The variant '%s' does not exist!" % variant)
                    eprint("Available variants: %s" % ", ".join(self.animation_variants._member_names_))

        self.__animation_thread = self.animation_class(width=self.__width, height=self.__height,
                                                       frame_queue=self.__frame_queue,
                                                       repeat=repeat,
                                                       on_finish_callable=self.__animation_finished_stopped,
                                                       **options)

        # mark the animation as running
        self.__animation_running.set()

        # start the animation thread
        self.__animation_thread.start()

    def _validate_parameter(self, parameter):
        # if no parameter is specified
        if (not parameter or
                self.animation_parameters is None):
            return {}

        # an instance of AnimationParameter could also be supplied
        if isinstance(parameter, AnimationParameter):
            # convert it to a dictionary
            return dict(parameter)

        # if it's already a dictionary, just return it
        if isinstance(parameter, dict):
            return parameter

        if len(self.animation_parameters.names) == 1:
            # this is the only possible parameter, so pass it as it is
            return {self.animation_parameters.names[0]: parameter}

        # otherwise there are multiple parameters coded in a JSON string
        try:
            parsed_p = json.loads(parameter)
        except ValueError:
            eprint("[%s] Parameter could not be parsed! Is it valid JSON?" % self.animation_name)
            return {}

        return parsed_p

    def __animation_finished_stopped(self):
        # release running event
        self.__animation_running.clear()

        # call finished callable
        self.__on_finish_callable()

    def stop_animation(self):
        # stop the animation if it's currently running.
        if (self.__animation_thread and
                self.__animation_thread.is_alive()):
            self.__animation_thread.stop_and_wait()
