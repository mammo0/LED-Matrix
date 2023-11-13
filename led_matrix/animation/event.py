from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from threading import Event
from typing import Generic, TypeVar
from uuid import UUID

from led_matrix.animation.abstract import AbstractAnimationController, AnimationSettings


@dataclass
class StopSettings:
    animation_name: str


@dataclass
class StartSettings(StopSettings):
    animation_settings: AnimationSettings
    pause_current_animation: bool


@dataclass
class ResumeSettings:
    animation_to_resume: AbstractAnimationController
    resume_thread_uuid: UUID


S = TypeVar("S", StartSettings, StopSettings, ResumeSettings)


class AnimationEventType(Enum):
    START = auto()
    STOP = auto()
    RESUME = auto()


class AnimationEvent(Generic[S]):
    def __init__(self, event_type: AnimationEventType, event_settings: S) -> None:
        self.__event_type: AnimationEventType = event_type
        self.__event_settings: S = event_settings

        self.__next_event: AnimationEvent | None = None
        self.__event_lock: Event = Event()

    def wait(self):
        # first wait for the own lock (when the event is processed the done method should be called)
        self.__event_lock.wait()
        # if there is an event that directly follows to this one, also wait for it
        if self.__next_event is not None:
            self.__next_event.wait()

    def chain(self, event: AnimationEvent):
        # create an event chain of events that belong together
        self.__next_event = event

    def done(self):
        # mark the event as done
        self.__event_lock.set()

    @property
    def event_type(self) -> AnimationEventType:
        return self.__event_type

    @property
    def event_settings(self) -> S:
        return self.__event_settings


class AnimationStartEvent(AnimationEvent[StartSettings]):
    def __init__(self, event_type: AnimationEventType, event_settings: StartSettings) -> None:
        super().__init__(event_type, event_settings)

        # special attribute for monitoring an animation thread on a start event
        self.__start_animation_thread_uuid: UUID | None = None

    @property
    def start_animation_thread_uuid(self) -> UUID | None:
        return self.__start_animation_thread_uuid

    @start_animation_thread_uuid.setter
    def start_animation_thread_uuid(self, start_animation_thread_uuid: UUID) -> None:
        self.__start_animation_thread_uuid = start_animation_thread_uuid


class AnimationStopEvent(AnimationEvent[StopSettings]):
    pass


class AnimationResumeEvent(AnimationEvent[ResumeSettings]):
    pass


E = TypeVar("E", AnimationEvent, None)


class AnimationEventQueue(Queue[E]):
    def __init__(self, maxsize: int=0):
        super().__init__(maxsize=maxsize)

        # this list contains all events + the ones not marked as finished
        # no thread safe list is required here since it is only accessed by the main animation controller thread
        self.__all_events: list[AnimationEvent] = []

    def _put(self, item: E) -> None:
        if item is not None:
            # check for duplicates in all events
            event: AnimationEvent
            for event in self.__all_events:
                # compare event type
                if event.event_type == item.event_type:
                    # on resume event, compare the animation_to_resume thread UUID
                    if (
                        event.event_type == AnimationEventType.RESUME and
                        isinstance(event, AnimationResumeEvent) and
                        isinstance(item, AnimationResumeEvent)
                    ):
                        if event.event_settings.resume_thread_uuid == item.event_settings.resume_thread_uuid:
                            return

                    # on start/stop event compare the animation_name
                    elif (
                        event.event_type == AnimationEventType.STOP and
                        isinstance(event, (AnimationStartEvent, AnimationStopEvent)) and
                        isinstance(item, (AnimationStartEvent, AnimationStopEvent))
                    ):
                        if event.event_settings.animation_name == item.event_settings.animation_name:
                            return

            # add the event to the complete list
            self.__all_events.append(item)

        Queue[E]._put(self, item)

    def task_done(self, event: E | None=None) -> None:
        # super call
        super().task_done()

        # mark the corresponding event also as done
        if event is not None:
            # remove the event from the complete list
            self.__all_events.remove(event)

            event.done()

    @property
    def are_tasks_remaining(self) -> bool:
        with self.mutex:
            return self.unfinished_tasks > 0

    @property
    def is_last_task_running(self) -> bool:
        with self.mutex:
            return self._qsize() == 0 and self.unfinished_tasks <= 1
