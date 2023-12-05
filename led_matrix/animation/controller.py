from __future__ import annotations

from importlib import resources
from logging import Logger
from queue import Empty, LifoQueue, Queue
from threading import Event, Thread
from typing import cast
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from simple_plugin_loader import Loader

from led_matrix.animation.abstract import (AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationSettings, AnimationVariant)
from led_matrix.animation.dummy import DummyController
from led_matrix.animation.event import (AnimationEvent, AnimationEventQueue,
                                        AnimationEventType,
                                        AnimationResumeEvent,
                                        AnimationStartEvent,
                                        AnimationStopEvent, ResumeSettings,
                                        StartSettings, StopSettings)
from led_matrix.common.log import LOG
from led_matrix.config import Configuration


class MainAnimationController(Thread):
    def __init__(self, config: Configuration, display_frame_queue: Queue[NDArray[np.uint8]]) -> None:
        super().__init__(daemon=True)

        self.__log: Logger = LOG.create(MainAnimationController.__name__)

        self.__stop_event: Event = Event()
        self.__controll_queue: AnimationEventQueue = AnimationEventQueue()
        self.__pause_queue: LifoQueue[tuple[AbstractAnimationController, UUID]] = LifoQueue()

        # the current running animation
        self.__current_animation_controller: AbstractAnimationController | None = None

        # the dummy animation is always present as a fallback
        self.__all_animation_controllers: dict[str, AbstractAnimationController] = {}

        dummy_animation: DummyController = DummyController(width=config.main.display_width,
                                                           height=config.main.display_height,
                                                           frame_queue=display_frame_queue,
                                                           on_finish_callable=self.__on_animation_finished)
        self.__all_animation_controllers[dummy_animation.animation_name] = dummy_animation

        # load all available animations
        with resources.as_file(resources.files("led_matrix.animations")) as animations_dir:
            animation_loader: Loader = Loader()
            animation_loader.load_plugins(path=str(animations_dir.resolve()),
                                          plugin_base_class=AbstractAnimationController)

        # use module names to identify the animations not the class names
        animation_cls: type[AbstractAnimationController]
        for animation_cls in animation_loader.plugins.values():
            animation_controller: AbstractAnimationController = animation_cls(
                width=config.main.display_width,
                height=config.main.display_height,
                frame_queue=display_frame_queue,
                on_finish_callable=self.__on_animation_finished
            )
            self.__all_animation_controllers[animation_controller.animation_name] = animation_controller

        # load the default animation
        self.__default_animation_name: str = config.default_animation.animation_name
        default_animation_controller: AbstractAnimationController = (
            self.__all_animation_controllers[self.__default_animation_name]
        )

        dvariant_type: type[AnimationVariant] | None = default_animation_controller.variant_enum
        dparameter_type: type[AnimationParameter] | None = default_animation_controller.parameter_class

        self.__default_animation_settings: AnimationSettings = AnimationSettings(
            variant=config.get_default_animation_variant(dvariant_type),
            parameter=config.get_default_animation_parameter(dparameter_type),
            repeat=config.default_animation.repeat
        )

    def __on_last_element_processed(self) -> AnimationEvent:
        # check for paused animations
        try:
            animation_to_resume, resume_thread_uuid = self.__pause_queue.get_nowait()
        except Empty:
            # if there's no paused animation, start the default animation
            return self.__create_start_event(animation_name=self.__default_animation_name,
                                             animation_settings=self.__default_animation_settings,
                                             # there is no animation running currently
                                             pause_current_animation=False)

        return self.__create_resume_event(animation_controller_to_resume=animation_to_resume,
                                          resume_thread_uuid=resume_thread_uuid)

    def __on_animation_finished(self) -> None:
        # whenever an animation stops or finishes check if there are unfinished jobs
        if not self.__controll_queue.are_tasks_remaining:
            self.__on_last_element_processed()

    def __start_animation(self, event: AnimationStartEvent) -> None:
        try:
            # get the new animation
            animation: AbstractAnimationController = (
                self.__all_animation_controllers[event.event_settings.animation_name]
            )
        except KeyError:
            self.__log.error("The animation '%s' could not be found!",
                             event.event_settings.animation_name)
        else:
            # create the animation thread instance
            animation_uuid: UUID = animation.create_animation(event.event_settings.animation_settings)

            # check if the current animation should be paused
            if (
                event.event_settings.pause_current_animation and
                self.__current_animation_controller is not None
            ):
                # if so, pause it and add it to the pause stack
                animation_to_pause: AbstractAnimationController = self.__current_animation_controller
                paused_animation_uuid: UUID | None = animation_to_pause.pause()
                if paused_animation_uuid is not None:
                    self.__pause_queue.put((animation_to_pause, paused_animation_uuid))
            else:
                # if an animation should be started without pausing the current one,
                # clear the pause queue, because afterwards no resuming should be done
                if not self.__pause_queue.empty():
                    # force clearing of pause queue
                    self.__pause_queue.queue.clear()

                # stop any currently running animation
                self.__stop_animation()

            # start it
            animation.start(animation_uuid)
            self.__current_animation_controller = animation

            # special: set the thread UUID (for blocking until animation has finished)
            event.start_animation_thread_uuid = animation_uuid

    def __stop_animation(self, event: AnimationStopEvent | None=None) -> None:
        # if there's already a running animation, stop it
        if self.__current_animation_controller is not None:
            # but only if not a specific animation should be stopped
            if (
                event is not None and
                self.__current_animation_controller.animation_name !=
                    event.event_settings.animation_name
            ):
                return

            self.__current_animation_controller.stop()
            self.__current_animation_controller = None

    def __resume_animation(self, event: AnimationResumeEvent) -> None:
        event.event_settings.animation_to_resume.resume(event.event_settings.resume_thread_uuid)
        self.__current_animation_controller = event.event_settings.animation_to_resume

    def __create_resume_event(self,
                              animation_controller_to_resume: AbstractAnimationController,
                              resume_thread_uuid: UUID) -> AnimationResumeEvent:
        resume_event: AnimationResumeEvent = AnimationResumeEvent(
            event_type=AnimationEventType.RESUME,
            event_settings=ResumeSettings(animation_to_resume=animation_controller_to_resume,
                                          resume_thread_uuid=resume_thread_uuid)
        )
        self.__controll_queue.put(resume_event)

        return resume_event

    def start_animation(self,
                        animation_name: str,
                        animation_settings: AnimationSettings,
                        pause_current_animation: bool=False,
                        block_until_started: bool=False,
                        block_until_finished: bool=False) -> None:
        start_event: AnimationStartEvent = self.__create_start_event(
            animation_name=animation_name,
            animation_settings=animation_settings,
            pause_current_animation=pause_current_animation
        )

        # wait here until the start event was processed and the animation started
        if block_until_started:
            start_event.wait()

        # check blocking until finished
        if block_until_finished:
            # first wait until the animation started
            start_event.wait()

            # then get the thread object from the start animation
            if (
                self.__current_animation_controller is not None and
                start_event.start_animation_thread_uuid is not None
            ):
                # wait until the thread/animation finishes
                self.__current_animation_controller.wait(start_event.start_animation_thread_uuid)

    def __create_start_event(self,
                             animation_name: str,
                             animation_settings: AnimationSettings,
                             pause_current_animation: bool) -> AnimationStartEvent:
        start_event = AnimationStartEvent(
            event_type=AnimationEventType.START,
            event_settings=StartSettings(animation_name=animation_name,
                                         animation_settings=animation_settings,
                                         pause_current_animation=pause_current_animation)
        )
        self.__controll_queue.put(start_event)

        return start_event

    def stop_animation(self, animation_name: str | None=None, blocking: bool=False) -> None:
        # by default the current animation should be stopped
        if self.__current_animation_controller is None:
            # nothing can be stopped
            return

        # check if the current animation is the one that should be stopped
        if (
            animation_name is not None and
            self.__current_animation_controller.animation_name != animation_name
        ):
            # otherwise do nothing, because only the current one can be stopped
            return

        # create and schedule the stop event
        stop_event: AnimationStopEvent = AnimationStopEvent(
            event_type=AnimationEventType.STOP,
            event_settings=StopSettings(animation_name=self.__current_animation_controller.animation_name)
        )
        self.__controll_queue.put(stop_event)

        # check blocking
        if blocking:
            # wait until the animation is stopped
            stop_event.wait()

    @property
    def all_animation_controllers(self) -> dict[str, AbstractAnimationController]:
        return self.__all_animation_controllers

    def is_animation_running(self, animation_name: str) -> bool:
        try:
            # get the animation
            animation: AbstractAnimationController = self.__all_animation_controllers[animation_name]
        except KeyError:
            self.__log.error("The animation '%s' could not be found!",
                             animation_name)
            return False

        return animation.is_running

    @property
    def current_animation_name(self) -> str:
        if self.__current_animation_controller:
            return self.__current_animation_controller.animation_name

        return ""

    def run(self) -> None:
        # on start show default animation
        self.__create_start_event(animation_name=self.__default_animation_name,
                                  animation_settings=self.__default_animation_settings,
                                  # not needed, because currently no animation is running
                                  pause_current_animation=False)

        while not self.__stop_event.is_set():
            # get the next event
            event: AnimationEvent | None = self.__controll_queue.get()

            # sometimes get can take a while to return, so check the stop flag again here
            if self.__stop_event.is_set():
                self.__controll_queue.task_done(event)
                break

            if event is not None:
                # check the event type
                if event.event_type == AnimationEventType.START:
                    self.__start_animation(cast(AnimationStartEvent, event))
                elif event.event_type == AnimationEventType.RESUME:
                    self.__resume_animation(cast(AnimationResumeEvent, event))
                elif event.event_type == AnimationEventType.STOP:
                    self.__stop_animation(cast(AnimationStopEvent, event))

                    # special case on stop event:
                    # after the animation was stopped check if this was the last task (for now)
                    if self.__controll_queue.is_last_task_running:
                        # if so, resume an paused animations or start the default one
                        new_event: AnimationEvent = self.__on_last_element_processed()
                        # link the new event to the old one
                        # this is needed for a blocking stop event
                        event.chain(new_event)

            # the event is processed now
            self.__controll_queue.task_done(event)

    def stop(self) -> None:
        self.__stop_event.set()
        # add a new element into the control_queue to force returning of get method in loop
        self.__controll_queue.put(None)
        self.join()

        # after the control thread has stopped, there could be an animation thread remaining
        # so stop this animation
        self.__stop_animation()
