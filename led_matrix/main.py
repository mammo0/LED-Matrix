import signal
from datetime import datetime
from importlib import resources
from logging import Logger
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread

import numpy as np
import pytz
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from numpy.typing import NDArray
from simple_plugin_loader import Loader

from led_matrix.animation.abstract import (AbstractAnimationController,
                                           AnimationSettings)
from led_matrix.animation.controller import MainAnimationController
from led_matrix.common.log import LOG
from led_matrix.common.schedule import ScheduleEntry
from led_matrix.common.threading import EventWithUnsetSignal
from led_matrix.config import Configuration
from led_matrix.config.types import ColorTemp
from led_matrix.display.abstract import AbstractDisplay
from led_matrix.server.http_server import HttpServer
from led_matrix.server.tpm2_net import Tpm2NetServer

_log: Logger = LOG.create("Main")


# TODO:
# add timer that displays a textmessage from predefined list of messages
# restructure other animations
# make mood light animation
class MainController:
    __quit_signal: Event = Event()
    __reload_signal: EventWithUnsetSignal = EventWithUnsetSignal()

    def __init__(self, config_file_path: Path) -> None:
        _log.info("Initialize LED-Matrix")

        # catch SIGINT, SIGQUIT and SIGTERM
        signal.signal(signal.SIGINT, self.__quit)
        signal.signal(signal.SIGQUIT, self.__quit)
        signal.signal(signal.SIGTERM, self.__quit)
        # catch SIGHUP to reload configuration
        signal.signal(signal.SIGHUP, self.__reload)

        # load config
        self.__config_file_path: Path = config_file_path
        self.__config: Configuration = Configuration(config_file_path=self.__config_file_path)

        # this is the queue that holds the frames to display
        self.__frame_queue: Queue[NDArray[np.uint8]] = Queue(maxsize=1)

        # create the display object
        self.__display: AbstractDisplay = self.__initialize_display()

        # animation controller
        # gets initialized in mainloop method
        self.__animation_controller: MainAnimationController = MainAnimationController(
            config=self.config,
            display_frame_queue=self.__frame_queue
        )

        # the animation scheduler
        self.__schedule_table: list[ScheduleEntry]
        self.__animation_scheduler: BackgroundScheduler = self.__create_scheduler()
        self.__schedule_lock: Lock = Lock()

        # the nighttime scheduler
        self.__sun_scheduler: BackgroundScheduler = BackgroundScheduler()
        self.__sunrise_job: Job = self.__sun_scheduler.add_job(
            func=self.apply_day_night,
            # prevent running now
            trigger=DateTrigger(datetime.min.replace(tzinfo=pytz.UTC))
        )
        self.__sunset_job: Job = self.__sun_scheduler.add_job(
            func=self.apply_day_night,
            # prevent running now
            trigger=DateTrigger(datetime.min.replace(tzinfo=pytz.UTC))
        )
        self.__sun_scheduler.add_job(func=self.__refresh_sun_scheduler,
                                     trigger=CronTrigger(hour="0,12",
                                                         minute=0,
                                                         second=0))
        self.__refresh_sun_scheduler()
        self.apply_day_night()
        self.__sun_scheduler.start()

        # server interfaces
        self.__http_server: HttpServer | None = None
        self.__tpm2_net_server: Tpm2NetServer | None = None

    def __create_scheduler(self) -> BackgroundScheduler:
        _log.info("Initialize animation scheduler")

        # start with an empty table
        self.__schedule_table = []

        # create the scheduler
        scheduler: BackgroundScheduler = BackgroundScheduler()

        # load saved jobs
        saved_jobs: list[ScheduleEntry] = (
            self.__config.get_scheduled_animations_table(self.all_animation_controllers)
        )

        entry: ScheduleEntry
        for entry in saved_jobs:
            # add job to the scheduler
            scheduler.add_job(func=self.start_animation,
                              trigger=CronTrigger(year=entry.cron_structure.year,
                                                  month=entry.cron_structure.month,
                                                  day=entry.cron_structure.day,
                                                  week=entry.cron_structure.week,
                                                  day_of_week=entry.cron_structure.day_of_week,
                                                  hour=entry.cron_structure.hour,
                                                  minute=entry.cron_structure.minute,
                                                  second=entry.cron_structure.second),
                              args=(entry.animation_name,
                                    entry.animation_settings),
                              kwargs={"pause_current_animation": True,
                                      "block_until_finished": True},
                              id=entry.job_id)

            # add it to the internal schedule table
            # no lock is needed here, because when this method is called only the main thread is running
            self.__schedule_table.append(entry)

        return scheduler

    def __initialize_display(self) -> AbstractDisplay:
        _log.info("Initialize display")

        with resources.as_file(resources.files("led_matrix.display")) as displays_dir:
            # load display plugins
            display_loader: Loader = Loader()
            display_loader.load_plugins(str(displays_dir.resolve()), plugin_base_class=AbstractDisplay)

        # create it
        try:
            display: AbstractDisplay = display_loader.plugins[self.__config.main.hardware.name.casefold()](
                config=self.__config
            )
            display.clear()
        except KeyError as e:
            raise RuntimeError(f"Display hardware '{self.__config.main.hardware.name}' not known.") from e

        return display

    def __refresh_sun_scheduler(self):
        _log.info("Refreshing sunrise sunset times")

        self.__config.main.refresh_sunset_sunrise()

        # apply sunrise / sunset times
        self.__sunrise_job.reschedule(trigger=DateTrigger(run_date=self.__config.main.sunrise))
        self.__sunset_job.reschedule(trigger=DateTrigger(run_date=self.__config.main.sunset))

    def __start_servers(self) -> None:
        _log.info("Starting servers")

        # HTTP server
        if (
            self.__config.main.http_server and
            # if the following variable is set, that means we're in a reload phase
            # so the server is already started
            self.__http_server is None
        ):
            self.__http_server = HttpServer(main_app=self)
            self.__http_server.start()

        # TPM2Net server
        if self.__config.main.tpm2net_server:
            self.__tpm2_net_server = Tpm2NetServer(main_app=self)
            Thread(target=self.__tpm2_net_server.serve_forever, daemon=True).start()

    def __stop_servers(self) -> None:
        _log.info("Stopping servers")

        # stop only the servers that are started
        # except on reload, then do not stop the HTTP
        if not self.__reload_signal.is_set():
            # HTTP server
            if self.__http_server is not None:
                self.__http_server.stop()

        # TPM2Net server
        if self.__tpm2_net_server:
            self.__tpm2_net_server.shutdown()
            self.__tpm2_net_server.server_close()

    def __save_schedule_table(self) -> None:
        _log.info("Saving schedule table to config file")

        # this method should be surrounded by a lock
        # save the table in the config
        self.__config.set_scheduled_animations_table(self.__schedule_table)
        self.__config.save()

    @classmethod
    def quit(cls) -> None:
        cls.__quit()

    @classmethod
    def __quit(cls, *_) -> None:
        _log.info("Exit request received. Start cleaning up...")
        MainController.__quit_signal.set()

    @property
    def config(self) -> Configuration:
        """
        Access to the configuration object.
        """
        return self.__config

    @property
    def frame_queue(self) -> Queue[NDArray[np.uint8]]:
        """
        Access to the frame queue.
        Needed by the animation classes.
        """
        return self.__frame_queue

    def __reload(self, *_) -> None:
        _log.info("Reloading application")

        # set the reload and quit signal to exit mainloop
        MainController.__reload_signal.set()
        MainController.__quit_signal.set()

    def reload(self) -> None:
        """
        Call this method to reload the configuration and restart the default animation.
        """
        # start reload process
        self.__reload()

        # wait until the the __reload_signal is unset
        MainController.__reload_signal.wait_unset()

    def start_animation(self,
                        animation_name: str,
                        animation_settings: AnimationSettings,
                        pause_current_animation: bool=False,
                        block_until_started: bool=False,
                        block_until_finished: bool=False) -> None:
        """
        Start a specific animation. See the respective animation class for which options are available.
        @param animation_name: The name of the animation to start.
        @param animation_settings: Instance of _AnimationSettingsStructure.
        @param pause_current_animation: If set to True, just pause the current animation and resume
                                          after the new animation finishes.
        @param block_until_started: If set to True, wait until the animation is running. Otherwise return immediately.
        @param block_until_finished: If set to True, wait until the animation has finished.
                                     Otherwise return immediately.
        """
        self.__animation_controller.start_animation(animation_name=animation_name,
                                                    animation_settings=animation_settings,
                                                    pause_current_animation=pause_current_animation,
                                                    block_until_started=block_until_started,
                                                    block_until_finished=block_until_finished)

    def schedule_animation(self, entry: ScheduleEntry) -> None:
        """
        Schedule an animation.
        @param entry: An instance of ScheduleEntry that defines when to run a certain animation.
        """
        with self.__schedule_lock:
            job = self.__animation_scheduler.add_job(func=self.start_animation,
                                                     trigger=CronTrigger(year=entry.cron_structure.year,
                                                                         month=entry.cron_structure.month,
                                                                         day=entry.cron_structure.day,
                                                                         week=entry.cron_structure.week,
                                                                         day_of_week=entry.cron_structure.day_of_week,
                                                                         hour=entry.cron_structure.hour,
                                                                         minute=entry.cron_structure.minute,
                                                                         second=entry.cron_structure.second),
                                                     args=(entry.animation_name,
                                                           entry.animation_settings),
                                                     kwargs={"pause_current_animation": True,
                                                             "block_until_finished": True})

            # add the job ID to the entry
            entry.job_id = job.id

            # add it to the schedule table
            self.__schedule_table.append(entry)

            # save the new entry in the config
            self.__save_schedule_table()

        _log.info("Scheduled animation '%s'",
                  entry.animation_name)

    def stop_animation(self,
                       animation_name: str | None=None,
                       blocking: bool=False):
        """
        Stop the current or a specific animation (if it's the current one).
        @param animation_name: Optional, the name of the animation to stop. If it's not the current animation,
                               nothing happens.
                               If no name is provided, the current animation will be stopped.
        @param blocking: If set to True, wait until the animation is stopped. Otherwise return immediately.
                         It also waits until the default animation is started again.
        """
        self.__animation_controller.stop_animation(animation_name=animation_name, blocking=blocking)

    def remove_scheduled_animation(self, schedule_job_id: str) -> None:
        """
        Remove an animation from the schedule table.
        @param schedule_id: The id for the scheduled animation.
                            Possible values can be observed with the scheduled_animations property.
        """
        with self.__schedule_lock:
            job_found: bool = False

            i: int
            entry: ScheduleEntry | None = None
            for i, entry in enumerate(self.__schedule_table):
                if entry.job_id == schedule_job_id:
                    job_found = True
                    self.__animation_scheduler.remove_job(schedule_job_id)

                    # remove the entry from the table
                    del self.__schedule_table[i]
                    break

            if not job_found:
                _log.warning("No scheduled animation with ID '%s' found!",
                             {str(schedule_job_id)})
            else:
                # save the modified table
                self.__save_schedule_table()

            if entry is not None:
                _log.info("Removed scheduled animation '%s'",
                          entry.animation_name)

    def modify_scheduled_animation(self, schedule_entry: ScheduleEntry) -> None:
        """
        Modify a scheduled animation.
        @param schedule_entry: A instance of ScheduleEntry that contains the new settings.
                               The JOB_ID variable must match an existing scheduled job. Otherwise this method
                               will do nothing.
        """
        with self.__schedule_lock:
            job_found: bool = False

            i: int
            entry: ScheduleEntry | None = None
            for i, entry in enumerate(self.__schedule_table):
                if entry.job_id == schedule_entry.job_id:
                    job_found = True
                    # modify the arguments
                    self.__animation_scheduler.modify_job(
                        schedule_entry.job_id,
                        args=(schedule_entry.animation_name,
                              schedule_entry.animation_settings)
                    )

                    # and also reschedule it
                    self.__animation_scheduler.reschedule_job(
                        schedule_entry.job_id,
                        trigger=CronTrigger(year=schedule_entry.cron_structure.year,
                                            month=schedule_entry.cron_structure.month,
                                            day=schedule_entry.cron_structure.day,
                                            week=schedule_entry.cron_structure.week,
                                            day_of_week=schedule_entry.cron_structure.day_of_week,
                                            hour=schedule_entry.cron_structure.hour,
                                            minute=schedule_entry.cron_structure.minute,
                                            second=schedule_entry.cron_structure.second)
                    )

                    # replace the schedule table entry
                    self.__schedule_table[i] = schedule_entry
                    break

            if not job_found:
                _log.warning("No scheduled animation with ID '%s' found!",
                             str(schedule_entry.job_id))
            else:
                # save the modified table
                self.__save_schedule_table()

            if entry is not None:
                _log.info("Modified scheduled animation '%s'",
                          entry.animation_name)

    @property
    def all_animation_controllers(self) -> dict[str, AbstractAnimationController]:
        """
        Get a dict of the available animations.
        @return: Key: the animation name
                 Value: the corresponding AbstractAnimationController object
        """
        return self.__animation_controller.all_animation_controllers

    @property
    def scheduled_animations(self) -> list[ScheduleEntry]:
        """
        @return: A list of ScheduleEntry instances.
        """
        return self.__schedule_table

    def is_animation_running(self, animation_name: str) -> bool:
        """
        @param animation_name: The name of the animation to check.
        @return: True if the specific animation is currently running, otherwise false.
        """
        return self.__animation_controller.is_animation_running(animation_name)

    @property
    def current_animation_name(self) -> str:
        """
        @return: The name of the currently running animation.
                 Empty string if no animation is running.
        """
        return self.__animation_controller.current_animation_name

    def apply_day_night(self) -> None:
        """
        Applies the brightness and color temperature based on the current time.
        """
        self.preview_brightness(self.__config.main.brightness)
        self.preview_color_temp(self.__config.main.color_temp)

    def preview_brightness(self, brightness: int) -> None:
        """
        Directly apply the given brightness value on the current display.
        """
        _log.info("Change display brightness to %d%%",
                  brightness)

        # apply to the current display
        self.__display.set_brightness(brightness)

    def preview_color_temp(self, color_temp: ColorTemp) -> None:
        """
        Directly apply the given colort temperature on the current display.
        """
        _log.info("Change color temperature to %s",
                  color_temp.title)

        # apply to the current display
        self.__display.set_color_temp(color_temp)

    def mainloop(self) -> None:
        # start the animation controller
        self.__animation_controller.start()

        # start the animation scheduler
        self.__animation_scheduler.start()

        # start the server interfaces
        self.__start_servers()

        first_loop: bool = True
        # run until '__quit' method was called
        while not MainController.__quit_signal.is_set():
            # check if there is a frame that needs to be displayed
            if self.__frame_queue.qsize() != 0:
                # get frame and display it
                self.__display.frame_buffer = self.__frame_queue.get()
                self.__frame_queue.task_done()
                self.__display.show(gamma=True)

                # after the first frame is displayed, clear the reload signal
                if first_loop:
                    MainController.__reload_signal.clear()
                    first_loop = False
            else:
                # to limit CPU usage do not go faster than 60 "fps" on empty queue
                MainController.__quit_signal.wait(1/60)

        # first shutdown the animation scheduler, so no new animations will be started
        # do not wait for the scheduler executor; this causes a deadlock if a scheduled animation is currently running
        self.__animation_scheduler.shutdown(wait=False)
        # stop the animation controller (including any currently running animation)
        self.__animation_controller.stop()
        self.__display.clear()

        # stop the server interfaces
        self.__stop_servers()

        if MainController.__reload_signal.is_set():
            _log.info("Reloading application")

            # reload settings
            self.__config = Configuration(config_file_path=self.__config_file_path)

            # recreate the controller
            self.__animation_controller = MainAnimationController(config=self.config,
                                                                  display_frame_queue=self.frame_queue)

            # recreate the scheduler
            self.__animation_scheduler = self.__create_scheduler()

            # re-initialize the display
            self.__display = self.__initialize_display()
            self.apply_day_night()

            # clear quit signal
            # the reload signal gets cleared after the first frame is displayed again
            MainController.__quit_signal.clear()

            # restart mainloop
            self.mainloop()
        else:
            _log.info("Cleanup finished. Exiting now")
