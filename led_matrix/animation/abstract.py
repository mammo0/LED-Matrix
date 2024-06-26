"""
This is the sceleton code for all animations.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import Field, dataclass, fields
from enum import Enum
from io import BytesIO
from logging import Logger
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import (Callable, ClassVar, Iterator, Optional, Self, final,
                    get_args)
from uuid import UUID, uuid4

from led_matrix.common.color import Color
from led_matrix.common.log import LOG
from led_matrix.common.threading import EventWithUnsetSignal


class AnimationVariant(Enum):
    @classmethod
    def build_variants_from_files(cls, name: str, search_dir: Path, glob_str: str) -> type[Self]:
        variants: dict[str, Path] = {}

        found_file: Path
        for found_file in sorted(search_dir.glob(glob_str), key=lambda s: s.name.lower()):
            if found_file.is_file():
                variants[found_file.stem] = found_file.resolve()

        # this works, because AnimationVariant is derived from Enum
        new_type: type[Self] = AnimationVariant(name, variants)  # type: ignore # pylint: disable=E1121

        setattr(new_type, "__search_dir__", search_dir)
        setattr(new_type, "__glob_str__", glob_str)

        return new_type

    @classmethod
    def refresh_variants(cls) -> type[Self]:
        search_dir: Path | None = getattr(cls, "__search_dir__", None)
        glob_str: str | None = getattr(cls, "__glob_str__", None)

        if glob_str is None or search_dir is None:
            # this happens if no dynamic variant was built with the 'build_variants_from_files' method above
            # so, can't refresh anything
            return cls

        return cls.build_variants_from_files(name=cls.__name__,
                                             search_dir=search_dir,
                                             glob_str=glob_str)


AnimationParameterTypes = str | bool | int | float | Color
@dataclass(kw_only=True)
class AnimationParameter:
    def __post_init__(self) -> None:
        f: Field
        for f, _ in self.iterate_fields():
            if f.type not in get_args(AnimationParameterTypes):
                raise RuntimeError(f"The type of the parameter field '{f.name}' must be one of "
                                   f"'{', '.join(a.__name__ for a in get_args(AnimationParameterTypes))}'!")

    def iterate_fields(self) -> Iterator[tuple[Field, AnimationParameterTypes]]:
        field: Field
        for field in fields(self):
            yield (field, getattr(self, field.name))


@dataclass(kw_only=True)
class AnimationSettings:
    # If available, the variant.
    variant: Optional[AnimationVariant] = None
    # If available, the parameter(s) for the animation.
    parameter: Optional[AnimationParameter] = None
    # If available, how many times an animation should be repeated.
    # 0: no repeat, -1: forever, > 0: x-times
    repeat: int = 0


class AbstractAnimation(ABC, Thread):
    def __init__(self, width: int, height: int,
                 frame_queue: Queue, settings: AnimationSettings,
                 logger: Logger,
                 on_finish_callable: Callable[[], None]) -> None:
        super().__init__(daemon=True)

        self.__log: Logger = logger

        self._width: int = width  # width of frames to produce
        self._height: int = height  # height of frames to produce
        self._frame_queue: Queue = frame_queue  # queue to put frames onto
        self._settings: AnimationSettings = settings
        self._repeat: int = self._settings.repeat
        self.__remaining_repeat: int = self._repeat - 1
        self.__on_finish_callable: Callable[[], None] = on_finish_callable

        # stop event
        # query this often! exit self.render_next_frame quickly
        self._stop_event: Event = Event()
        # pause event
        self._pause_event: Event = Event()
        # helper event
        self.__animation_paused: EventWithUnsetSignal = EventWithUnsetSignal()

        # default animation speed 60 fps
        self.__animation_speed: float = 1/60

    @property
    def _log(self) -> Logger:
        return self.__log

    def run(self) -> None:
        while not self._stop_event.is_set():
            start_time: float = time.time()
            if not self._pause_event.is_set():
                # if the animation is still marked as paused, unset it here
                if self.__animation_paused.is_set():
                    # also notifies the resume method that now the animation is running again
                    self.__animation_paused.clear()

                # add the next frame to the frame queue
                try:
                    more: bool = self.render_next_frame()
                except Exception as e:  # pylint: disable=W0718
                    self.__log.error("During the execution of the animation the following error occurred:",
                                     exc_info=e)
                    break

                # check if the animation has finished
                if not more:
                    # check for more iterations
                    if self.is_next_iteration():
                        # decrease iteration count
                        self.__remaining_repeat -= 1
                        # start a new iteration
                        continue

                    # the animation has finished
                    self.__on_finish_callable()
                    # stop here
                    break
            else:
                # notify the pause method that the animation is now paused
                self.__animation_paused.set()

            # limit fps = animation_speed - the execution time
            wait_time: float = self.__animation_speed - (time.time() - start_time)
            if wait_time > 0:
                self._stop_event.wait(wait_time)

    def _set_animation_speed(self, animation_speed: float) -> None:
        self.__animation_speed = animation_speed

    def pause(self) -> None:
        self._pause_event.set()

        # wait until the current frame is rendered
        self.__animation_paused.wait()

    def resume(self) -> None:
        self._pause_event.clear()

        # wait until the animation is running again
        self.__animation_paused.wait_unset()

    def stop_and_wait(self) -> None:
        self._stop_event.set()

        # the current running animation could still try to insert new frames onto the frame queue
        # but if we reach this point, no more frames should be generated
        # to release the queue lock it must be cleared
        while self._frame_queue.qsize() != 0:
            try:
                self._frame_queue.get_nowait()
            except Empty:
                break

        self.join()

    def is_next_iteration(self) -> bool:
        # no repeat
        if self._repeat == 0:
            return False

        # infinity repeat
        if self._repeat == -1:
            return True

        # check remaining repeat cycles
        if self.__remaining_repeat > 0:
            return True
        return False

    @abstractmethod
    def render_next_frame(self) -> bool:
        """
        This is where frames are put to the frame_queue in correct time.
        @return: True if there are more frames to come.
                 False if the animation is finished.
        """
        raise NotImplementedError

    @property
    def settings(self) -> AnimationSettings:
        return self._settings


class AbstractAnimationController(ABC):
    __animation_name: ClassVar[str]
    __animation_class: ClassVar[type[AbstractAnimation]]
    __settings_class: ClassVar[type[AnimationSettings]]
    __accepts_dynamic_variant: ClassVar[bool]
    __is_repeat_supported: ClassVar[bool]
    __variant_enum: ClassVar[type[AnimationVariant] | None]
    __parameter_class: ClassVar[type[AnimationParameter] | None]

    def __init__(self, width: int, height: int,
                 frame_queue: Queue, on_finish_callable: Callable[["AbstractAnimationController"], None]) -> None:
        # width of frames to produce
        self.__width: int = width
        # height of frames to produce
        self.__height: int = height
        # queue to put frames onto
        self.__frame_queue: Queue = frame_queue
        # this gets called whenever an animation stops/finishes
        self.__on_finish_callable: Callable[[AbstractAnimationController], None] = on_finish_callable

        self.__log: Logger = LOG.create(f"Animation: '{self.animation_name}'")

        self.__animation_threads: dict[UUID, AbstractAnimation] = {}
        self.__paused_animation_threads: dict[UUID, AbstractAnimation] = {}

        # this variable contains the current animation
        self._current_animation: tuple[UUID, AbstractAnimation] | None = None

        self.__animation_running_event: Event = Event()

    def __init_subclass__(cls, *,
                          animation_name: str,
                          animation_class: type[AbstractAnimation],
                          settings_class: type[AnimationSettings],
                          accepts_dynamic_variant: bool,
                          is_repeat_supported: bool,
                          variant_enum: type[AnimationVariant] | None=None,
                          parameter_class: type[AnimationParameter] | None=None) -> None:
        cls.__animation_name = animation_name
        cls.__animation_class = animation_class
        cls.__settings_class = settings_class
        cls.__accepts_dynamic_variant = accepts_dynamic_variant
        cls.__is_repeat_supported = is_repeat_supported
        cls.__variant_enum = variant_enum
        cls.__parameter_class = parameter_class

    @final
    @property
    def _log(self) -> Logger:
        return self.__log

    @final
    @property
    def animation_name(self) -> str:
        """
        @return: The name of the animation.
        """
        return self.__animation_name

    @final
    @property
    def animation_class(self) -> type[AbstractAnimation]:
        """
        @return: The animation class.
        """
        return self.__animation_class

    @final
    @property
    def variant_enum(self) -> type[AnimationVariant] | None:
        """
        @return: An enum object that holds the variants of the underlying animation. Or None if there are no variants.
        """
        return self.__variant_enum

    @final
    @property
    def accepts_dynamic_variant(self) -> bool:
        """
        @return: True if this animation supports adding and removing of new variants.
                 False if not.
        """
        return self.__accepts_dynamic_variant

    @final
    @property
    def parameter_class(self) -> type[AnimationParameter] | None:
        """
        @return: A subclass of AnimationParameter that holds the parameters of the underlying animation.
                 Or None if there are no parameters.
        """
        return self.__parameter_class

    @final
    @property
    def settings_class(self) -> type[AnimationSettings]:
        """
        @return: A subclass of AnimationSettings that holds the settings of the underlying animation.
        """
        return self.__settings_class

    @final
    @property
    def default_settings(self) -> AnimationSettings:
        """
        @return: A subclass _AnimationSettingsStructure that holds the default settings for the underlying animation.
        """
        return self.settings_class()

    @final
    @property
    def settings(self) -> AnimationSettings:
        if (self._current_animation is not None and
                self._current_animation[1].is_alive()):
            return self._current_animation[1].settings

        return self.default_settings

    @final
    @property
    def is_repeat_supported(self) -> bool:
        """
        @return: True if the repeat value is supported by the animation. False otherwise.
        """
        return self.__is_repeat_supported

    def __refresh_variant_enum(self) -> None:
        # this method should be called whenever a dynamic variant has changed
        if self.__variant_enum is not None:
            type(self).__variant_enum = self.__variant_enum.refresh_variants()

    @final
    def add_dynamic_variant(self, file_name: str, file_content: BytesIO) -> None:
        """
        This method adds a new variant to the animation.
        @param file_name: The name of the file.
        @param file_content: A open file(-like) object that can be processed by the animation.
        """
        # error handling
        if not self.accepts_dynamic_variant:
            self.__log.warning("This animation does not support adding of new variants.")
            return

        self._add_dynamic_variant(file_name, file_content)

        # refresh the variant enum class
        self.__refresh_variant_enum()

    def _add_dynamic_variant(self, file_name: str, file_content: BytesIO) -> None:
        """
        Animations that support adding of variants must override this method.
        """
        raise NotImplementedError

    @final
    def remove_dynamic_variant(self, variant: AnimationVariant) -> None:
        """
        This method removes a variant from the animation.
        @param variant: A variant of the animation that should exist in the animation_variants enum.
        """
        # error handling
        if not self.accepts_dynamic_variant:
            self.__log.warning("This animation does not support removing of variants.")
            return

        if self.variant_enum:
            for v in self.variant_enum:
                if (v.name == variant.name and
                        v.value == v.value):
                    self._remove_dynamic_variant(variant)

                    # refresh the variant enum class
                    self.__refresh_variant_enum()

                    return

        self.__log.error("The variant '%s' could not be found.",
                         variant.name)

    def _remove_dynamic_variant(self, variant: AnimationVariant) -> None:
        """
        Animations that support removing of variants must override this method.
        """
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        return self.__animation_running_event.is_set()

    def create_animation(self, animation_settings: AnimationSettings) -> UUID:
        """
        For settings see _AnimationSettingsStructure.
        """
        animation_thread: AbstractAnimation = self.animation_class(
            width=self.__width, height=self.__height,
            frame_queue=self.__frame_queue,
            settings=animation_settings,
            logger=self.__log,
            on_finish_callable=self.__animation_finished
        )
        animation_uuid: UUID = uuid4()
        self.__animation_threads[animation_uuid] = animation_thread

        return animation_uuid

    def start(self, animation_uuid: UUID) -> None:
        animation_thread: AbstractAnimation | None = self.__animation_threads.get(animation_uuid, None)
        if animation_thread is None:
            self.__log.error("Could not find animation to start.")
            return

        self.__log.info("Starting animation")

        # set the current animation thread
        self._current_animation = (animation_uuid, animation_thread)

        # mark the animation as running
        self.__animation_running_event.set()

        # start the animation thread
        animation_thread.start()

    def pause(self) -> UUID | None:
        if (self.__animation_running_event.is_set() and
                self._current_animation is not None and
                self._current_animation[1].is_alive()):
            self._current_animation[1].pause()
            self.__animation_running_event.clear()

            uuid: UUID = self._current_animation[0]
            # no try-clause here, because the dict must contain the uuid
            self.__paused_animation_threads[uuid] = self.__animation_threads.pop(uuid)

            # unset the current animation
            self._current_animation = None

            self.__log.info("Paused animation")

            return uuid

        return None

    def resume(self, paused_uuid: UUID) -> None:
        try:
            animation_thread: AbstractAnimation = self.__paused_animation_threads.pop(paused_uuid)
        except KeyError:
            self.__log.error("Can't find an animation to resume.")
            return

        self.__log.info("Resuming animation")

        animation_thread.resume()
        self.__animation_running_event.set()

        self.__animation_threads[paused_uuid] = animation_thread
        self._current_animation = (paused_uuid, animation_thread)

    def stop(self) -> None:
        # stop the animation if it's currently running.
        if (self._current_animation is not None and
                self._current_animation[1].is_alive()):
            self._current_animation[1].stop_and_wait()

            # clear
            self.__animation_running_event.clear()
            self.__animation_threads.pop(self._current_animation[0])
            self._current_animation = None

            self.__log.info("Stopped animation")

        else:
            self.__log.warning("Can't stop animation, because it's not running")

    def wait(self, animation_uuid: UUID) -> None:
        animation_thread: AbstractAnimation | None = self.__animation_threads.get(animation_uuid, None)
        if animation_thread is None:
            self.__log.error("Could not find the animation to wait for.")
            return

        animation_thread.join()

    def __animation_finished(self) -> None:
        self.__log.info("Animation finished")

        # release running event
        self.__animation_running_event.clear()

        # call finished callable
        self.__on_finish_callable(self)
