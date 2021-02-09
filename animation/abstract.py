"""
This is the sceleton code for all animations.
"""

from abc import abstractmethod, ABC, ABCMeta
from threading import Thread, Event

from simple_classproperty import ClasspropertyMeta, classproperty

from common import eprint
from common.color import Color
from common.structure import TypedStructure
from common.threading import EventWithUnsetSignal


class _AnimationSettingsStructureMeta(type(TypedStructure)):
    def __new__(metacls, cls, bases, classdict):
        new_cls = type(TypedStructure).__new__(metacls, cls, bases, classdict)

        # programmatically change the animation_name attribute
        if cls != "_AnimationSettingsStructure":
            new_cls._params_map_["animation_name"] = new_cls.__module__.rpartition(".")[-1]

        return new_cls


class _AnimationSettingsStructure(TypedStructure, metaclass=_AnimationSettingsStructureMeta):
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

    def as_raw_dict(self):
        raw_dict = TypedStructure.as_raw_dict(self)
        for k, v in raw_dict.items():
            if (k == "variant" and
                    v is not None):
                # use enum name of variant (not the value)
                raw_dict[k] = v.name

        return raw_dict


class AnimationParameter(TypedStructure):
    def as_raw_dict(self):
        raw_dict = TypedStructure.as_raw_dict(self)
        for k, v in raw_dict.items():
            if isinstance(v, Color):
                # get hex value for raw
                raw_dict[k] = v.hex_value

        return raw_dict


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

        self._stop_event = Event()  # query this often! exit self.render_next_frame quickly
        # pause event
        self._pause_event = Event()
        # helper event
        self.__animation_paused = EventWithUnsetSignal()

        # default animation speed 60 fps
        self.__animation_speed = 1/60

    def run(self):
        while not self._stop_event.is_set():
            if not self._pause_event.is_set():
                # if the animation is still marked as paused, unset it here
                if self.__animation_paused.is_set():
                    # also notifies the resume method that now the animation is running again
                    self.__animation_paused.clear()

                # add the next frame to the frame queue
                try:
                    more = self.render_next_frame()
                except Exception as e:
                    eprint("During the execution of the animation the following error occurred:")
                    eprint(repr(e))
                    break

                # check if the animation has finished
                if not more:
                    # check for more iterations
                    if self.is_next_iteration():
                        # decrease iteration count
                        self.__remaining_repeat -= 1
                        # start a new iteration
                        continue
                    else:
                        # stop here
                        break
            else:
                # notify the pause method that the animation is now paused
                self.__animation_paused.set()

            # limit fps
            self._stop_event.wait(self.__animation_speed)

        # now the animation has stopped, so call the finish callable
        self.__on_finish_callable()

    # def start(self):
    """We do not overwrite this. It is from threading.Thread"""

    def _set_animation_speed(self, animation_speed):
        self.__animation_speed = animation_speed

    def pause(self):
        self._pause_event.set()

        # wait until the current frame is rendered
        self.__animation_paused.wait()

    def resume(self):
        self._pause_event.clear()

        # wait until the animation is running again
        self.__animation_paused.wait_unset()

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
                return True
            else:
                return False

    @abstractmethod
    def render_next_frame(self):
        """
        This is where frames are put to the frame_queue in correct time.
        @return: True if there are more frames to come.
                 False if the animation is finished.
        """

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
    def __init__(self, width, height, frame_queue, on_finish_callable):
        self.__width = width  # width of frames to produce
        self.__height = height  # height of frames to produce
        self.__frame_queue = frame_queue  # queue to put frames onto
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
    def accepts_dynamic_variant(self):
        """
        @return: True if this animation supports adding and removing of new variants.
                 False if not.
        """

    def add_dynamic_variant(self, file_name, file_content):
        """
        This method adds a new variant to the animation.
        @param file_name: The name of the file.
        @param file_content: A open file(-like) object that can be processed by the animation.
        """
        # error handling
        if not self.accepts_dynamic_variant:
            eprint("This animation does not support adding of new variants.")
            return

        self._add_dynamic_variant(file_name, file_content)

    def _add_dynamic_variant(self, file_name, file_content):
        """
        Animations that support adding of variants must override this method.
        """
        raise NotImplementedError()

    def remove_dynamic_variant(self, variant):
        """
        This method removes a variant from the animation.
        @param variant: A variant of the animation that should exist in the animation_variants enum.
        """
        # error handling
        if not self.accepts_dynamic_variant:
            eprint("This animation does not support removing of variants.")
            return

        for v in self.animation_variants:
            if (v.name == variant.name and
                    v.value == v.value):
                self._remove_dynamic_variant(variant)
                return

        eprint(f"The variant '{variant.name}' could not be found.")

    def _remove_dynamic_variant(self, variant):
        """
        Animations that support removing of variants must override this method.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def animation_parameters(self):
        """
        @return: A subclass of AnimationParameter that holds the parameters of the underlying animation.
                 Or None if there are no parameters.
        """

    @property
    @abstractmethod
    def default_animation_settings(self):
        """
        @return: A subclass _AnimationSettingsStructure that holds the default settings for the underlying animation.
        """

    @property
    def animation_settings(self):
        if (self.__animation_thread and
                self.__animation_thread.is_alive()):
            return self.__animation_thread.settings
        else:
            return self.default_animation_settings()

    @property
    @abstractmethod
    def is_repeat_supported(self):
        """
        @return: True if the repeat value is supported by the animation. False otherwise.
        """

    @property
    def is_running(self):
        return self.__animation_running.is_set()

    def create_animation(self, animation_settings):
        """
        For settings see _AnimationSettingsStructure.
        """
        # parse the parameters
        self._validate_animation_settings(animation_settings)

        return self.animation_class(width=self.__width, height=self.__height,
                                    frame_queue=self.__frame_queue,
                                    settings=animation_settings,
                                    on_finish_callable=self.__animation_finished_stopped)

    def start_animation(self, animation_instance):
        # set the current animation thread
        self.__animation_thread = animation_instance

        # mark the animation as running
        self.__animation_running.set()

        # start the animation thread
        self.__animation_thread.start()

    def pause_animation(self):
        if (self.__animation_running.is_set() and
                self.__animation_thread and
                self.__animation_thread.is_alive()):
            self.__animation_thread.pause()
            self.__animation_running.clear()
            return self.__animation_thread

        return None

    def resume_animation(self, animation_thread):
        animation_thread.resume()
        self.__animation_running.set()

    def _validate_animation_settings(self, animation_settings):
        # variant
        if (self.animation_variants is not None and
                not isinstance(animation_settings.variant, self.animation_variants)):
            animation_settings.variant = self.animation_variants[animation_settings.variant]

        # parameter
        if (self.animation_parameters is not None and
                isinstance(animation_settings.parameter, dict)):
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
