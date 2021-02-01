"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC, ABCMeta
from threading import Thread, Event

from simple_classproperty import ClasspropertyMeta, classproperty

from common import eprint
from common.structure import TypedStructure


class _AnimationSettingsStructureMeta(type(TypedStructure)):
    def __new__(metacls, cls, bases, classdict):
        new_cls = type(TypedStructure).__new__(metacls, cls, bases, classdict)

        # programmatically change the animation_name attribute
        if cls != "AnimationSettingsStructure":
            new_cls._params_map_["animation_name"] = new_cls.__module__.rpartition(".")[-1]

        return new_cls


class AnimationSettingsStructure(TypedStructure, metaclass=_AnimationSettingsStructureMeta):
    # The name of the animation.
    # do not change this manually, it gets set by the metaclass
    animation_name = None
    # If available, the variant.
    variant = None
    # If available, the parameter(s) for the animation.
    parameter = None
    # If available, how many times an animation should be repeated.
    # 0: no repeat, -1: forever, > 0: x-times
    repeat = 0


class AnimationParameter(TypedStructure):
    pass


class AbstractAnimation(ABC, Thread):
    def __init__(self, width, height, frame_queue, settings, on_finish_callable):
        super().__init__(daemon=True)
        self._width = width  # width of frames to produce
        self._height = height  # height of frames to produce
        self._frame_queue = frame_queue  # queue to put frames onto
        self._settings = settings
        self._repeat = self._settings.repeat
        self.__remaining_repeat = self._repeat - 1
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
    def settings(self):
        return self._settings

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
    @abstractmethod
    def _default_animation_settings(self):
        """
        @return: A subclass AnimationSettingsStructure that holds the default settings for the underlying animation.
        """

    @property
    def animation_settings(self):
        if (self.__animation_running.is_set() and
                self.__animation_thread and
                self.__animation_thread.is_alive()):
            return self.__animation_thread.settings
        else:
            return self._default_animation_settings()

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

    @property
    def is_running(self):
        return self.__animation_running.is_set()

    def start_animation(self, animation_settings):
        """
        For settings see AnimationSettingsStructure.
        """
        # parse the parameters
        self._validate_animation_settings(animation_settings)

        self.__animation_thread = self.animation_class(width=self.__width, height=self.__height,
                                                       frame_queue=self.__frame_queue,
                                                       settings=animation_settings,
                                                       on_finish_callable=self.__animation_finished_stopped)

        # mark the animation as running
        self.__animation_running.set()

        # start the animation thread
        self.__animation_thread.start()

    def _validate_animation_settings(self, animation_settings):
        # variant
        if not isinstance(animation_settings.variant, self.animation_variants):
            animation_settings.variant = self.animation_variants[animation_settings.variant]

        # parameter
        if isinstance(animation_settings.parameter, dict):
            animation_settings.parameter = self.animation_parameters(**animation_settings.parameter)

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
