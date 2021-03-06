#!/usr/bin/env python3

from abc import ABC, abstractmethod
import argparse
from collections import namedtuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import LifoQueue
import queue
import signal
import sys
from threading import Lock
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from astral.geocoder import lookup, database
from astral.sun import sun
from simple_plugin_loader import Loader
import tzlocal

from animation.abstract import AbstractAnimationController
from common import BASE_DIR, DEFAULT_CONFIG_FILE, eprint
from common.config import Configuration, Config
from common.schedule import ScheduleEntry
from common.threading import EventWithUnsetSignal
from display.abstract import AbstractDisplay
from server.http_server import HttpServer
from server.rest_server import RestServer
from server.tpm2_net import Tpm2NetServer


# TODO:
# add timer that displays a textmessage from predefined list of messages
# restructure other animations
# make mood light animation
class MainInterface(ABC):
    @abstractmethod
    def reload(self):
        """
        Call this method to reload the configuration and restart the default animation.
        """

    @abstractmethod
    def start_animation(self, animation_settings, pause_current_animation=False,
                        block_until_started=False, block_until_finished=False):
        """
        Start a specific animation. See the respective animation class for which options are available.
        @param animation_settings: Instance of _AnimationSettingsStructure.
        @param pause_current_animation: If set to True, just pause the current animation and resume
                                          after the new animation finishes.
        @param block_until_started: If set to True, wait until the animation is running. Otherwise return immediately.
        @param block_until_finished: If set to True, wait until the animation has finished.
                                     Otherwise return immediately.
        """

    @abstractmethod
    def schedule_animation(self, cron_structure, animation_settings):
        """
        Schedule an animation.
        @param cron_structure: An instance of CronStructure that defines when to run a certain animation.
        @param *: The rest of the parameters are equal to the start_animation method.
        """

    @abstractmethod
    def stop_animation(self, animation_name=None, blocking=False):
        """
        Stop the current or a specific animation (if it's the current one).
        @param animation_name: Optional, the name of the animation to stop. If it's not the current animation,
                               nothing happens.
                               If no name is provided, the current animation will be stopped.
        @param blocking: If set to True, wait until the animation is stopped. Otherwise return immediately.
                         It also waits until the default animation is started again.
        """

    @abstractmethod
    def remove_scheduled_animation(self, schedule_id):
        """
        Remove an animation from the schedule table.
        @param schedule_id: The id for the scheduled animation.
                            Possible values can be observed with the scheduled_animations property.
        """

    @abstractmethod
    def modify_scheduled_animation(self, schedule_entry):
        """
        Modify a scheduled animation.
        @param schedule_entry: A instance of ScheduleEntry that contains the new settings.
                               The JOB_ID variable must match an existing scheduled job. Otherwise this method
                               will do nothing.
        """

    @property
    @abstractmethod
    def available_animations(self):
        """
        Get a dict of the available animations.
        @return: Key: the animation name
                 Value: the corresponding AbstractAnimationController object
        """

    @property
    @abstractmethod
    def scheduled_animations(self):
        """
        @return: A list of ScheduleEntry instances.
        """

    @abstractmethod
    def is_animation_running(self, animation_name):
        """
        @param animation_name: The name of the animation to check.
        @return: True if the specific animation is currently running, otherwise false.
        """

    @abstractmethod
    def get_current_animation_name(self):
        """
        @return: The name of the currently running animation.
                 Empty string if no animation is running.
        """

    @abstractmethod
    def get_day_brightness(self):
        """
        @return: The brightness value for day times.
        """

    @abstractmethod
    def get_night_brightness(self):
        """
        @return: The brightness value for night times.
        """

    @abstractmethod
    def apply_brightness(self, new_day_brightness=None, new_night_brightness=None):
        """
        Applies the brightness based on the current time.
        @param new_day_brightness: If set, use it as the new day brightness value.
        @param new_night_brightness: If set, use it as the new night brightness value.
        """

    @abstractmethod
    def preview_brightness(self, brightness):
        """
        Directly apply the given brightness value on the current display.
        """

    @property
    @abstractmethod
    def config(self):
        """
        Access to the configuration object.
        """

    @property
    @abstractmethod
    def frame_queue(self):
        """
        Access to the frame queue.
        Needed by the animation classes.
        """


class Main(MainInterface):
    def __init__(self, config_file_path=None):
        # catch SIGINT, SIGQUIT and SIGTERM
        self.__quit_signal = threading.Event()
        signal.signal(signal.SIGINT, self.__quit)
        signal.signal(signal.SIGQUIT, self.__quit)
        signal.signal(signal.SIGTERM, self.__quit)
        # catch SIGHUP and reload configuration
        signal.signal(signal.SIGHUP, self.__reload)

        # load config
        if config_file_path is None:
            self.__config_file_path = DEFAULT_CONFIG_FILE
        else:
            self.__config_file_path = config_file_path
        self.__load_settings()

        # this is the queue that holds the frames to display
        self.__frame_queue = queue.Queue(maxsize=1)

        # animation controller
        # gets initialized in mainloop method
        self.__animation_controller = AnimationController(self.config, self.frame_queue)

        # the animation scheduler
        self.__animation_scheduler = self.__create_scheduler()
        self.__schedule_lock = Lock()

        # the nighttime scheduler
        self.__location = lookup(tzlocal.get_localzone().zone.split("/")[1], database())
        self.__nighttime_scheduler = BackgroundScheduler()
        self.__sunrise_job = self.__nighttime_scheduler.add_job(func=self.apply_brightness)
        self.__sunset_job = self.__nighttime_scheduler.add_job(func=self.apply_brightness)
        self.__nighttime_scheduler.add_job(func=self.__calculate_nighttimes,
                                           trigger=CronTrigger(hour="0,12",
                                                               minute=0,
                                                               second=0))
        self.__calculate_nighttimes()
        self.apply_brightness()
        self.__nighttime_scheduler.start()

        # create the display object
        self.__initialize_display()

        # server interfaces
        self.__http_server = None
        self.__rest_server = None
        self.__tpm2_net_server = None

        # this signal is set by the reload method
        self.__reload_signal = EventWithUnsetSignal()

    def __load_settings(self):
        self.__config = Configuration(config_file_path=self.__config_file_path, allow_no_value=True)

        # get [MAIN] options
        self.__conf_hardware = self.__config.get(Config.MAIN.Hardware)
        self.__conf_display_width = self.__config.get(Config.MAIN.DisplayWidth)
        self.__conf_display_height = self.__config.get(Config.MAIN.DisplayHeight)
        self.__day_brightness = self.__config.get(Config.MAIN.DayBrightness)
        self.__night_brightness = self.__config.get(Config.MAIN.NightBrightness)

    def __create_scheduler(self):
        # start with an empty table
        self.__schedule_table = []

        # create the scheduler
        scheduler = BackgroundScheduler()

        # load saved jobs
        saved_jobs = self.config.get(Config.SCHEDULEDANIMATIONS.ScheduleTable)
        for job in saved_jobs:
            entry = ScheduleEntry(**job)

            # during load of the saved scheduled animations, the ANIMATION_SETTINGS attribute is a dict
            # it must be converted to the respective class instead
            animation = self.available_animations[entry.ANIMATION_SETTINGS["animation_name"]]
            entry.ANIMATION_SETTINGS = animation.default_animation_settings(**entry.ANIMATION_SETTINGS)

            # add job to the scheduler
            scheduler.add_job(func=self.start_animation,
                              trigger=CronTrigger(year=entry.CRON_STRUCTURE.YEAR,
                                                  month=entry.CRON_STRUCTURE.MONTH,
                                                  day=entry.CRON_STRUCTURE.DAY,
                                                  week=entry.CRON_STRUCTURE.WEEK,
                                                  day_of_week=entry.CRON_STRUCTURE.DAY_OF_WEEK,
                                                  hour=entry.CRON_STRUCTURE.HOUR,
                                                  minute=entry.CRON_STRUCTURE.MINUTE,
                                                  second=entry.CRON_STRUCTURE.SECOND),
                              args=(entry.ANIMATION_SETTINGS,),
                              kwargs={"pause_current_animation": True, "block_until_finished": True},
                              id=entry.JOB_ID)

            # add it to the internal schedule table
            # no lock is needed here, because when this method is called only the main thread is running
            self.__schedule_table.append(entry)

        return scheduler

    def __initialize_display(self):
        # load display plugins
        display_loader = Loader()
        display_loader.load_plugins((BASE_DIR / "display").resolve(), plugin_base_class=AbstractDisplay)

        # create it
        try:
            self.__display = display_loader.plugins[self.__conf_hardware.casefold()](self.__conf_display_width,
                                                                                     self.__conf_display_height,
                                                                                     self.__display_brightness,
                                                                                     config=self.config)
            self.__clear_display()
        except KeyError:
            raise RuntimeError("Display hardware '{}' not known.".format(self.__conf_hardware))

    def __calculate_nighttimes(self):
        s = sun(self.__location.observer, date=datetime.now().date())
        if s["sunset"] < datetime.now(tz=tzlocal.get_localzone()):
            # calling after sunset, so calculate for the next day
            s = sun(self.__location.observer, date=datetime.now().date() + timedelta(days=1))
        self.__sunrise = s["sunrise"]
        self.__sunset = s["sunset"]

        self.__sunrise_job.reschedule(trigger=DateTrigger(run_date=self.__sunrise))
        self.__sunset_job.reschedule(trigger=DateTrigger(run_date=self.__sunset))

    def __start_servers(self):
        # HTTP server
        if (self.__config.get(Config.MAIN.HttpServer) and
                # if the variable is set, that means we're in a reload phase
                # so the server is already started
                self.__http_server is None):
            self.__http_server = HttpServer(self)
            self.__http_server.start()

        # REST server
        if (self.__config.get(Config.MAIN.RestServer) and
                # if the variable is set, that means we're in a reload phase
                # so the server is already started
                self.__rest_server is None):
            self.__rest_server = RestServer(self)
            self.__rest_server.start()

        # TPM2Net server
        if self.__config.get(Config.MAIN.TPM2NetServer):
            self.__tpm2_net_server = Tpm2NetServer(self, self.__conf_display_width, self.__conf_display_height)
            threading.Thread(target=self.__tpm2_net_server.serve_forever, daemon=True).start()

    def __stop_servers(self):
        # stop only the servers that are started
        # except on reload, then do not stop the HTTP and REST server
        if not self.__reload_signal.is_set():
            # HTTP server
            if self.__http_server:
                self.__http_server.stop()

            # REST server
            if self.__rest_server:
                self.__rest_server.stop()

        # TPM2Net server
        if self.__tpm2_net_server:
            self.__tpm2_net_server.shutdown()
            self.__tpm2_net_server.server_close()

    def __save_schedule_table(self):
        # this method should be surrounded by a lock
        # convert the ScheduleEntry instances to dicts (needed for file saving)
        table = []
        for entry in self.__schedule_table:
            table.append(entry.as_raw_dict())

        # save the table in the config
        self.config.set(Config.SCHEDULEDANIMATIONS.ScheduleTable, table)
        self.config.save()

    def __clear_display(self):
        self.__display.clear_buffer()
        self.__display.show()

    def __quit(self, *_):
        print("Exiting...")
        self.__quit_signal.set()

    @property
    def config(self):
        return self.__config

    @property
    def frame_queue(self):
        return self.__frame_queue

    def __reload(self, *_):
        print("Reloading...")

        # set the reload and quit signal to exit mainloop
        self.__reload_signal.set()
        self.__quit_signal.set()

    def reload(self):
        # start reload process
        self.__reload()

        # wait until the the __reload_signal is unset
        self.__reload_signal.wait_unset()

    def start_animation(self, animation_settings, pause_current_animation=False,
                        block_until_started=False, block_until_finished=False):
        self.__animation_controller.start_animation(animation_settings=animation_settings,
                                                    pause_current_animation=pause_current_animation,
                                                    block_until_started=block_until_started,
                                                    block_until_finished=block_until_finished)

    def schedule_animation(self, cron_structure, animation_settings):
        with self.__schedule_lock:
            job = self.__animation_scheduler.add_job(func=self.start_animation,
                                                     trigger=CronTrigger(year=cron_structure.YEAR,
                                                                         month=cron_structure.MONTH,
                                                                         day=cron_structure.DAY,
                                                                         week=cron_structure.WEEK,
                                                                         day_of_week=cron_structure.DAY_OF_WEEK,
                                                                         hour=cron_structure.HOUR,
                                                                         minute=cron_structure.MINUTE,
                                                                         second=cron_structure.SECOND),
                                                     args=(animation_settings,),
                                                     kwargs={"pause_current_animation": True,
                                                             "block_until_finished": True})

            # create an entry for the schedule table
            schedule_entry = ScheduleEntry()
            schedule_entry.JOB_ID = job.id
            schedule_entry.CRON_STRUCTURE = cron_structure
            schedule_entry.ANIMATION_SETTINGS = animation_settings
            self.__schedule_table.append(schedule_entry)

            # save the new entry in the config
            self.__save_schedule_table()

    def stop_animation(self, animation_name=None, blocking=False):
        self.__animation_controller.stop_animation(animation_name, blocking=blocking)

    def remove_scheduled_animation(self, schedule_id):
        with self.__schedule_lock:
            job_found = False
            for i in range(0, len(self.__schedule_table)):
                if self.__schedule_table[i].JOB_ID == schedule_id:
                    job_found = True
                    self.__animation_scheduler.remove_job(schedule_id)

                    # remove the entry from the table
                    del self.__schedule_table[i]
                    break

            if not job_found:
                eprint("No scheduled animation with ID '%' found!" % str(schedule_id))
            else:
                # save the modified table
                self.__save_schedule_table()

    def modify_scheduled_animation(self, schedule_entry):
        with self.__schedule_lock:
            job_found = False
            for i in range(0, len(self.__schedule_table)):
                if self.__schedule_table[i].JOB_ID == schedule_entry.JOB_ID:
                    job_found = True
                    # modify the arguments
                    self.__animation_scheduler.modify_job(schedule_entry.JOB_ID,
                                                          args=(schedule_entry.ANIMATION_SETTINGS,))

                    # and also reschedule it
                    self.__animation_scheduler.reschedule_job(
                        schedule_entry.JOB_ID,
                        trigger=CronTrigger(year=schedule_entry.CRON_STRUCTURE.YEAR,
                                            month=schedule_entry.CRON_STRUCTURE.MONTH,
                                            day=schedule_entry.CRON_STRUCTURE.DAY,
                                            week=schedule_entry.CRON_STRUCTURE.WEEK,
                                            day_of_week=schedule_entry.CRON_STRUCTURE.DAY_OF_WEEK,
                                            hour=schedule_entry.CRON_STRUCTURE.HOUR,
                                            minute=schedule_entry.CRON_STRUCTURE.MINUTE,
                                            second=schedule_entry.CRON_STRUCTURE.SECOND)
                    )

                    # replace the schedule table entry
                    self.__schedule_table[i] = schedule_entry
                    break

            if not job_found:
                eprint("No scheduled animation with ID '%' found!" % str(schedule_entry.JOB_ID))
            else:
                # save the modified table
                self.__save_schedule_table()

    @property
    def available_animations(self):
        return self.__animation_controller.all_animations

    @property
    def scheduled_animations(self):
        return self.__schedule_table

    def is_animation_running(self, animation_name):
        return self.__animation_controller.is_animation_running(animation_name)

    def get_current_animation_name(self):
        return self.__animation_controller.get_current_animation_name()

    def get_day_brightness(self):
        return self.__day_brightness

    def get_night_brightness(self):
        return self.__night_brightness

    def apply_brightness(self, new_day_brightness=None, new_night_brightness=None):
        if new_day_brightness is not None:
            self.__day_brightness = new_day_brightness
        if new_night_brightness is not None:
            self.__night_brightness = new_night_brightness

        if (self.__night_brightness == -1 or
                self.__sunrise <= datetime.now(tz=tzlocal.get_localzone()) <= self.__sunset):
            self.__display_brightness = self.__day_brightness
        else:
            self.__display_brightness = self.__night_brightness

        self.preview_brightness(self.__display_brightness)

    def preview_brightness(self, brightness):
        # apply to the current display if it's already initialized
        if getattr(self, "_%s__display" % self.__class__.__name__, None) is not None:
            self.__display.set_brightness(brightness)

    def mainloop(self):
        # start the animation controller
        self.__animation_controller.start()

        # start the animation scheduler
        self.__animation_scheduler.start()

        # start the server interfaces
        self.__start_servers()

        first_loop = True
        # run until '__quit' method was called
        while not self.__quit_signal.is_set():
            # check if there is a frame that needs to be displayed
            if not self.__frame_queue.empty():
                # get frame and display it
                self.__display.buffer = self.__frame_queue.get()
                self.__frame_queue.task_done()
                self.__display.show(gamma=True)

                # after the first frame is displayed, clear the reload signal
                if first_loop:
                    self.__reload_signal.clear()
                    first_loop = False
            else:
                # to limit CPU usage do not go faster than 60 "fps" on empty queue
                self.__quit_signal.wait(1/60)

        self.__animation_scheduler.shutdown()
        self.__animation_controller.stop()
        self.__clear_display()

        # stop the server interfaces
        self.__stop_servers()

        if self.__reload_signal.is_set():
            # reload settings
            self.__load_settings()

            # recreate the controller
            self.__animation_controller = AnimationController(self.config, self.frame_queue)

            # recreate the scheduler
            self.__animation_scheduler = self.__create_scheduler()

            # re-initialize the display
            self.__initialize_display()

            # clear quit signal
            # the reload signal gets cleared after the first frame is displayed again
            self.__quit_signal.clear()

            # restart mainloop
            self.mainloop()


class AnimationController(threading.Thread):
    StartStopSettings = namedtuple("StartStopSettings", ["animation_settings",
                                                         "pause_current_animation"],
                                   defaults=(False,))
    ResumeSettings = namedtuple("ResumeSettings", ["animation_to_resume",
                                                   "resume_thread"])

    class _Event():
        def __init__(self, event_type, event_settings):
            self.event_type = event_type
            self.event_settings = event_settings

            # special attribute for monitoring an animation thread on a start event
            self.start_animation_thread = None

            self.next_event = None
            self.event_lock = threading.Event()

        def wait(self):
            # first wait for the own lock (when the event is processed the done method should be called)
            self.event_lock.wait()
            # if there is an event that directly follows to this one, also wait for it
            if self.next_event is not None:
                self.next_event.wait()

        def chain(self, event):
            # create an event chain of events that belong together
            self.next_event = event

        def done(self):
            # mark the event as done
            self.event_lock.set()

    class _EventType(Enum):
        start = 1
        stop = 2
        resume = 3

    class _EventQueue(queue.Queue):
        def __init__(self, maxsize=0):
            queue.Queue.__init__(self, maxsize=maxsize)

            # this list contains all events + the ones not marked as finished
            # no thread safe list is required here since it is only accessed by the main animation controller thread
            self.__all_events = []

        def _put(self, item):
            if item is not None:
                # check for duplicates in all events
                for event in self.__all_events:
                    # compare event type
                    if event.event_type == item.event_type:
                        # on resume event, compare the animation_to_resume thread
                        if event.event_type == AnimationController._EventType.resume:
                            if event.event_settings.resume_thread == item.event_settings.resume_thread:
                                return
                        # on start event compare the animation_settings (raw)
                        elif event.event_type == AnimationController._EventType.start:
                            if event.event_settings.animation_settings.as_raw_dict() == \
                                    item.event_settings.animation_settings.as_raw_dict():
                                return

                # add the event to the complete list
                self.__all_events.append(item)

            queue.Queue._put(self, item)

        def task_done(self, event):
            # super call
            queue.Queue.task_done(self)

            # mark the corresponding event also as done
            if event is not None:
                # remove the event from the complete list
                self.__all_events.remove(event)

                event.done()

        @property
        def tasks_remaining(self):
            with self.mutex:
                return self.unfinished_tasks > 0

        @property
        def last_task_running(self):
            with self.mutex:
                return self._qsize() == 0 and self.unfinished_tasks <= 1

    def __init__(self, config, display_frame_queue):
        super().__init__(daemon=True)

        # the display settings
        self.__display_width = config.get(Config.MAIN.DisplayWidth)
        self.__display_height = config.get(Config.MAIN.DisplayHeight)
        self.__display_frame_queue = display_frame_queue

        self.__stop_event = threading.Event()
        self.__controll_queue = AnimationController._EventQueue()
        self.__pause_queue = LifoQueue()

        # the current running animation
        self.__current_animation = None

        # get all available animations
        self.__all_animations = self.__load_animations()

        # load the default animation
        def_animation_name = config.get(Config.DEFAULTANIMATION.Animation)
        self.__default_animation_settings = self.__all_animations[def_animation_name].animation_settings
        self.__default_animation_settings.variant = config.get(Config.DEFAULTANIMATION.Variant)
        self.__default_animation_settings.parameter = config.get(Config.DEFAULTANIMATION.Parameter)
        self.__default_animation_settings.repeat = config.get(Config.DEFAULTANIMATION.Repeat)

    def __load_animations(self):
        animation_loader = Loader()
        animation_loader.load_plugins((BASE_DIR / "animation").resolve(), AbstractAnimationController)

        animations = {}

        # use module names to identify the animations not the class names
        for _name, cls in animation_loader.plugins.items():
            animation_controller = cls(width=self.__display_width, height=self.__display_height,
                                       frame_queue=self.__display_frame_queue,
                                       on_finish_callable=self.__on_animation_finished)
            animations[animation_controller.default_animation_settings.animation_name] = animation_controller

        return animations

    def __on_last_element_processed(self):
        # check for paused animations
        try:
            animation_to_resume, resume_thread = self.__pause_queue.get_nowait()
        except queue.Empty:
            # if there's no paused animation, start the default animation
            return self.__create_start_event(self.__default_animation_settings)
        else:
            return self.__create_resume_event(animation_to_resume=animation_to_resume, resume_thread=resume_thread)

    def __on_animation_finished(self):
        # whenever an animation stops or finishes check if there are unfinished jobs
        if not self.__controll_queue.tasks_remaining:
            self.__on_last_element_processed()

    def __start_animation(self, event):
        try:
            # get the new animation
            animation = self.__all_animations[event.event_settings.animation_settings.animation_name]
        except KeyError:
            eprint("The animation '%s' could not be found!" % event.event_settings.animation_settings.animation_name)
        else:
            # create the animation thread instance
            animation_thread = animation.create_animation(event.event_settings.animation_settings)

            # check if the current animation should be paused
            if (event.event_settings.pause_current_animation and
                    self.__current_animation is not None):
                # if so, pause it and add it to the pause stack
                animation_to_pause = self.__current_animation
                paused_thread = animation_to_pause.pause_animation()
                if paused_thread is not None:
                    self.__pause_queue.put((animation_to_pause, paused_thread))
            else:
                # if an animation should be started without pausing the current one,
                # clear the pause queue, because afterwards no resuming should be done
                if not self.__pause_queue.empty():
                    # force clearing of pause queue
                    self.__pause_queue.queue.clear()

                # stop any currently running animation
                self.__stop_animation()

            # start it
            animation.start_animation(animation_thread)
            self.__current_animation = animation

            # special: set the thread (for blocking until animation has finished)
            event.start_animation_thread = animation_thread

    def __stop_animation(self, event=None):
        # if there's already a running animation, stop it
        if self.__current_animation is not None:
            # but only if not a specific animation should be stopped
            if (event is not None and
                    self.__current_animation.default_animation_settings.animation_name !=
                    event.event_settings.animation_settings.animation_name):
                return
            self.__current_animation.stop_animation()
            self.__current_animation = None

    def __resume_animation(self, event):
        event.event_settings.animation_to_resume.resume_animation(event.event_settings.resume_thread)
        self.__current_animation = event.event_settings.animation_to_resume

    def __create_resume_event(self, animation_to_resume, resume_thread):
        resume_event = AnimationController._Event(
            AnimationController._EventType.resume,
            AnimationController.ResumeSettings(animation_to_resume=animation_to_resume,
                                               resume_thread=resume_thread)
        )
        self.__controll_queue.put(resume_event)

        return resume_event

    def start_animation(self, animation_settings,
                        pause_current_animation=False,
                        block_until_started=False, block_until_finished=False):
        start_event = self.__create_start_event(animation_settings,
                                                pause_current_animation=pause_current_animation)

        # check blocking until started
        if block_until_started:
            start_event.wait()

        # check blocking until finished
        if block_until_finished:
            # first wait until started
            start_event.wait()
            # then get the thread object from the start animation
            if start_event.start_animation_thread is not None:
                # wait until the thread/animation finishes
                start_event.start_animation_thread.join()

    def __create_start_event(self, animation_settings, pause_current_animation=False):
        start_event = AnimationController._Event(
            AnimationController._EventType.start,
            AnimationController.StartStopSettings(animation_settings=animation_settings,
                                                  pause_current_animation=pause_current_animation)
        )
        self.__controll_queue.put(start_event)

        return start_event

    def stop_animation(self, animation_name=None, blocking=False):
        self.__create_stop_event(animation_name=animation_name, blocking=blocking)

    def __create_stop_event(self, animation_name=None, blocking=False):
        # by default the current animation should be stopped
        animation_to_stop = self.__current_animation
        if animation_to_stop is None:
            # nothing can be stopped
            return None
        # check if the current animation is the one that should be stopped
        if (animation_name is not None and
                animation_to_stop.default_animation_settings.animation_name != animation_name):
            # otherwise do nothing
            return None

        # create and schedule the stop event
        stop_event = AnimationController._Event(
            AnimationController._EventType.stop,
            AnimationController.StartStopSettings(animation_settings=animation_to_stop.animation_settings)
        )
        self.__controll_queue.put(stop_event)

        # check blocking
        if blocking:
            stop_event.wait()

        return stop_event

    @property
    def all_animations(self):
        return self.__all_animations

    def is_animation_running(self, animation_name):
        try:
            # get the animation
            animation = self.__all_animations[animation_name]
        except KeyError:
            eprint("The animation '%s' could not be found!" % animation_name)
            return False

        return animation.is_running()

    def get_current_animation_name(self):
        cur_a = self.__current_animation
        if cur_a:
            return cur_a.default_animation_settings.animation_name
        else:
            return ""

    def run(self):
        # on start show default animation
        self.__create_start_event(self.__default_animation_settings)

        while not self.__stop_event.is_set():
            # get the next event
            event = self.__controll_queue.get()

            # sometimes get can take a while to return, so check the stop flag again here
            if self.__stop_event.is_set():
                self.__controll_queue.task_done(event)
                break

            # check the event type
            if event.event_type == AnimationController._EventType.start:
                self.__start_animation(event)
            elif event.event_type == AnimationController._EventType.resume:
                self.__resume_animation(event)
            elif event.event_type == AnimationController._EventType.stop:
                self.__stop_animation(event)
                # special case on stop event:
                # after the animation was stopped check if this was the last task (for now)
                if self.__controll_queue.last_task_running:
                    # if so, resume an paused animations or start the default one
                    new_event = self.__on_last_element_processed()
                    # link the new event to the old one
                    # this is needed for a blocking stop event
                    event.chain(new_event)

            # the event is processed now
            self.__controll_queue.task_done(event)

    def stop(self):
        self.__stop_event.set()
        # add a new element into the control_queue to force returning of get method in loop
        self.__controll_queue.put(None)
        self.join()

        # after the control thread has stopped, there could be an animation thread remaining
        # so stop this animation
        self.__stop_animation()


if __name__ == "__main__":
    # cli parser
    parser = argparse.ArgumentParser(description="LED-Matrix main control application.")
    parser.add_argument("-f", "--config-file", type=Path,
                        help="The path of the configuration file.")

    # get config path
    args = parser.parse_args(sys.argv[1:])

    # load the main application
    app = Main(args.config_file)

    app.mainloop()
