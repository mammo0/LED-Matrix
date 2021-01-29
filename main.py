#!/usr/bin/env python3

from abc import ABC, abstractmethod
import argparse
from enum import Enum
from pathlib import Path
import queue
import signal
import sys
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from simple_plugin_loader import Loader

from animation.abstract import AbstractAnimationController, \
    AnimationSettingsStructure
from common import BASE_DIR, RESOURCES_DIR, DEFAULT_CONFIG_FILE, eprint
from common.config import Configuration, Config
from common.event import EventWithUnsetSignal
from common.schedule import ScheduleEntry, CronStructure
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
    def start_animation(self, animation_settings, blocking=False):
        """
        Start a specific animation. See the respective animation class for which options are available.
        @param animation_settings: Instance of AnimationSettingsStructure.
        @param blocking: If set to True, wait until the animation is running. Otherwise return immediately.
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
        Get a dict of scheduled animations.
        @return: Key: the schedule ID
                 Value: the corresponding AbstractAnimationController object
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
    def get_brightness(self):
        """
        @return: The brightness value of the current display.
        """

    @abstractmethod
    def set_brightness(self, brightness):
        """
        Set the brightness of the current display. It will be applied immediately.
        @param brightness: The new brightness value.
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
    def __init__(self, config_file_path=None, commit_changes=False):
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
        self.__commit_changes = commit_changes
        self.__load_settings()

        # create the display object
        self.__initialize_display()

        # this is the queue that holds the frames to display
        self.__frame_queue = queue.Queue(maxsize=1)

        # animation controller
        # gets initialized in mainloop method
        self.__animation_controller = None

        # the animation scheduler
        self.__animation_scheduler = self.__create_scheduler()

        # server interfaces
        self.__http_server = None
        self.__rest_server = None
        self.__tpm2_net_server = None

        # this signal is set by the reload method
        self.__reload_signal = EventWithUnsetSignal()

    def __load_settings(self):
        self.__config = Configuration(config_file_path=self.__config_file_path, commit_changes=self.__commit_changes,
                                      allow_no_value=True)

        # get [MAIN] options
        self.__conf_hardware = self.__config.get(Config.MAIN.Hardware)
        self.__conf_display_width = self.__config.get(Config.MAIN.DisplayWidth)
        self.__conf_display_height = self.__config.get(Config.MAIN.DisplayHeight)
        self.set_brightness(self.__config.get(Config.MAIN.Brightness))

        # get [DEFAULTANIMATION] options
        self.__default_animation_settings = AnimationSettingsStructure()
        self.__default_animation_settings.animation_name = self.__config.get(Config.DEFAULTANIMATION.Animation)
        self.__default_animation_settings.variant = self.__config.get(Config.DEFAULTANIMATION.Variant)
        self.__default_animation_settings.parameter = self.__config.get(Config.DEFAULTANIMATION.Parameter)
        self.__default_animation_settings.repeat = self.__config.get(Config.DEFAULTANIMATION.Repeat)

    def __create_scheduler(self):
        # create the scheduler
        scheduler = BackgroundScheduler()

        # load saved jobs
        saved_jobs = self.config.get(Config.SCHEDULEDANIMATIONS.ScheduleTable)
        for job in saved_jobs:
            entry = ScheduleEntry(**job)
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
                              id=entry.JOB_ID)

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

    def start_animation(self, animation_settings, blocking=False):
        if self.__animation_controller is not None:
            self.__animation_controller.start_animation(animation_settings=animation_settings,
                                                        blocking=blocking)

    def schedule_animation(self, cron_structure, animation_settings):
        job = self.__animation_scheduler.add_job(func=self.start_animation,
                                                 trigger=CronTrigger(year=cron_structure.YEAR,
                                                                     month=cron_structure.MONTH,
                                                                     day=cron_structure.DAY,
                                                                     week=cron_structure.WEEK,
                                                                     day_of_week=cron_structure.DAY_OF_WEEK,
                                                                     hour=cron_structure.HOUR,
                                                                     minute=cron_structure.MINUTE,
                                                                     second=cron_structure.SECOND),
                                                 args=(animation_settings,))

        # create an entry for the schedule table
        schedule_entry = ScheduleEntry()
        schedule_entry.JOB_ID = job.id
        schedule_entry.CRON_STRUCTURE = cron_structure
        schedule_entry.ANIMATION_SETTINGS = animation_settings

        # save the new entry in the config
        table = self.config.get(Config.SCHEDULEDANIMATIONS.ScheduleTable)
        table.append(ScheduleEntry.as_recursive_dict(schedule_entry))
        self.config.set(Config.SCHEDULEDANIMATIONS.ScheduleTable, table)
        self.config.save()

    def stop_animation(self, animation_name=None, blocking=False):
        if self.__animation_controller is not None:
            self.__animation_controller.stop_animation(animation_name, blocking=blocking)

    def remove_scheduled_animation(self, schedule_id):
        # TODO: implement
        pass

    @property
    def available_animations(self):
        if self.__animation_controller is not None:
            return self.__animation_controller.all_animations
        else:
            return {}

    @property
    def scheduled_animations(self):
        # TODO: implement
        return {}

    def is_animation_running(self, animation_name):
        if self.__animation_controller is not None:
            return self.__animation_controller.is_animation_running(animation_name)
        else:
            return False

    def get_current_animation_name(self):
        if self.__animation_controller is not None:
            return self.__animation_controller.get_current_animation_name()
        else:
            return ""

    def get_brightness(self):
        return self.__display_brightness

    def set_brightness(self, brightness):
        if not 0 <= brightness <= 100:
            eprint("Invalid brightness value '%d'! Using default value '85'." % self.__display_brightness)
            self.__display_brightness = 85
        else:
            self.__display_brightness = brightness

        # apply to the current display if it's already initialized
        if getattr(self, "_%s__display" % self.__class__.__name__, None) is not None:
            self.__display.set_brightness(brightness)

    def mainloop(self):
        # start the animation controller
        self.__animation_controller = AnimationController(self.__conf_display_width, self.__conf_display_height,
                                                          self.frame_queue,
                                                          self.__default_animation_settings)
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

            # to limit CPU usage do not go faster than 60 "fps"
            self.__quit_signal.wait(1/60)

        self.__animation_scheduler.shutdown()
        self.__animation_controller.stop()
        self.__clear_display()

        # stop the server interfaces
        self.__stop_servers()

        if self.__reload_signal.is_set():
            # reload settings
            self.__load_settings()

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
    class _Event():
        def __init__(self, event_type, animation_settings):
            self.event_type = event_type
            self.animation_settings = animation_settings

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

    class _EventQueue(queue.Queue):
        def _put(self, item):
            # check for duplicates
            for event in self.queue:
                # compare event type and the animation name
                if (event.event_type == item.event_type and
                        event.animation_name == item.animation_name):
                    return

            queue.Queue._put(self, item)

        def task_done(self, event):
            # super call
            queue.Queue.task_done(self)

            # mark the corresponding event also as done
            if event is not None:
                event.done()

        @property
        def tasks_remaining(self):
            with self.mutex:
                return self.unfinished_tasks > 0

        @property
        def last_task_running(self):
            with self.mutex:
                return self._qsize() == 0 and self.unfinished_tasks <= 1

    def __init__(self, display_width, display_height, display_frame_queue,
                 default_animation_settings):
        super().__init__(daemon=True)

        # the display settings
        self.__display_width = display_width
        self.__display_height = display_height
        self.__display_frame_queue = display_frame_queue

        # the default animation settings
        self.__default_animation_settings = default_animation_settings

        self.__stop_event = threading.Event()
        self.__controll_queue = AnimationController._EventQueue()

        # the current running animation
        self.__current_animation = None

        # get all available animations
        self.__all_animations = self.__load_animations()

    def __load_animations(self):
        animation_loader = Loader()
        animation_loader.load_plugins((BASE_DIR / "animation").resolve(), AbstractAnimationController)

        animations = {}

        # use module names to identify the animations not the class names
        for _name, cls in animation_loader.plugins.items():
            animations[cls.animation_name] = cls(width=self.__display_width, height=self.__display_height,
                                                 frame_queue=self.__display_frame_queue,
                                                 resources_path=RESOURCES_DIR,
                                                 on_finish_callable=self.__on_animation_finished)

        return animations

    def __start_default_animation(self):
        return self.start_animation(self.__default_animation_settings)

    def __on_animation_finished(self):
        # whenever an animation stops or finishes check if there are unfinished jobs
        if not self.__controll_queue.tasks_remaining:
            # if not, start the default animation
            self.__start_default_animation()

    def __start_animation(self, animation_settings):
        # stop any currently running animation
        self.__stop_animation()

        try:
            # get the new animation
            animation = self.__all_animations[animation_settings.animation_name]
        except KeyError:
            eprint("The animation '%s' could not be found!" % animation_settings.animation_name)
        else:
            # start it
            animation.start_animation(animation_settings)
            self.__current_animation = animation

    def __stop_animation(self, animation_name=None):
        # if there's already a running animation, stop it
        if self.__current_animation is not None:
            # but only if not a specific animation should be stopped
            if (animation_name is not None and
                    self.__current_animation.animation_name != animation_name):
                return
            self.__current_animation.stop_animation()
            self.__current_animation = None

    def start_animation(self, animation_settings, blocking=False):
        start_event = AnimationController._Event(AnimationController._EventType.start,
                                                 animation_settings)
        self.__controll_queue.put(start_event)

        # check blocking
        if blocking:
            start_event.wait()

        return start_event

    def stop_animation(self, animation_name=None, blocking=False):
        # by default the current animation should be stopped
        animation_to_stop = self.__current_animation
        if animation_to_stop is None:
            # nothing can be stopped
            return
        # check if the current animation is the one that should be stopped
        if (animation_name is not None and
                animation_to_stop.animation_name != animation_name):
            # otherwise do nothing
            return

        # create and schedule the stop event
        settings = AnimationSettingsStructure()
        settings.animation_name = animation_to_stop.animation_name
        stop_event = AnimationController._Event(AnimationController._EventType.stop,
                                                settings)
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
            return cur_a.animation_name
        else:
            return ""

    def run(self):
        # on start show default animation
        self.__start_default_animation()

        while not self.__stop_event.is_set():
            # get the next event
            event = self.__controll_queue.get()

            # sometimes get can take a while to return, so check the stop flag again here
            if self.__stop_event.is_set():
                self.__controll_queue.task_done(event)
                break

            # check the event type
            if event.event_type == AnimationController._EventType.start:
                self.__start_animation(event.animation_settings)
            elif event.event_type == AnimationController._EventType.stop:
                self.__stop_animation(event.animation_settings)
                # special case on stop event:
                # after the animation was stopped check if this was the last task (for now)
                if self.__controll_queue.last_task_running:
                    # if so, start the default animation
                    default_start_event = self.__start_default_animation()
                    # link the new event to the old one
                    # this is needed for a blocking stop event
                    event.chain(default_start_event)

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
    parser.add_argument("-c", "--commit-changes", action="store_true",
                        help="Set this flag if changes to the filesystem should be commited with 'lbu'.")

    # get config path
    args = parser.parse_args(sys.argv[1:])

    # load the main application
    app = Main(args.config_file, args.commit_changes)

    app.mainloop()
