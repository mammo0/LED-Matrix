#!/usr/bin/env python3

from configparser import NoSectionError, NoOptionError
from enum import Enum
import os
from pathlib import Path
import queue
import sys
import threading
import time

from simple_plugin_loader import Loader

from animation.abstract import AbstractAnimationController
from common import eprint
from common.config import Configuration
from display.abstract import AbstractDisplay
from server.http_server import HttpServer
from server.rest_server import RestServer
from server.tpm2_net import Tpm2NetServer


# TODO:
# add timer that displays a textmessage from predefined list of messages
# restructure other animations
# make mood light animation
BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
CONFIG_FILE = BASE_DIR / "config.ini"
RESOURCES_DIR = BASE_DIR / "resources"


class Main():
    def __init__(self):
        # load config
        self.config = Configuration(allow_no_value=True)
        with open(CONFIG_FILE, "r") as f:
            self.config.read_file(f)

        # get [MAIN] options
        try:
            hardware = self.config.get("MAIN", option="Hardware")
            self.display_width = self.config.getint("MAIN", option="DisplayWidth")
            self.display_height = self.config.getint("MAIN", option="DisplayHeight")
        except (NoSectionError, NoOptionError):
            raise RuntimeError("The configuration file '{}' is not valid!".format(CONFIG_FILE))

        # get [DEFAULTANIMATION] options
        try:
            self.default_animation = self.config.get("DEFAULTANIMATION", option="Animation")
        except (NoSectionError, NoOptionError):
            raise RuntimeError("The configuration file '{}' is not valid!".format(CONFIG_FILE))
        self.default_animation_variant = self.config.get("DEFAULTANIMATION", option="Variant", fallback=None)
        self.default_animation_parameter = self.config.get("DEFAULTANIMATION", option="Parameter", fallback=None)
        self.default_animation_repeat = self.config.getint("DEFAULTANIMATION", option="Repeat", fallback=0)

        # load display plugins
        display_loader = Loader()
        display_loader.load_plugins((BASE_DIR / "display").resolve(), plugin_base_class=AbstractDisplay)

        try:
            self.display = display_loader.plugins[hardware.casefold()](self.display_width,
                                                                       self.display_height,
                                                                       config=self.config.get_section(hardware))
        except KeyError:
            raise RuntimeError("Display hardware '{}' not known.".format(hardware))

        # this is the queue that holds the frames to display
        self.frame_queue = queue.Queue(maxsize=1)

        # animation controller
        self.animation_controller = AnimationController(self.display_width, self.display_height, self.frame_queue)

        # server interfaces
        self.http_server = None
        self.rest_server = None
        self.tpm2_net_server = None

    def __start_servers(self):
        # HTTP server
        if self.config.getboolean("MAIN", "HttpServer"):
            self.http_server = HttpServer(self)
            threading.Thread(target=self.http_server.serve_forever, daemon=True).start()

        # REST server
        if self.config.getboolean("MAIN", "RestServer"):
            self.rest_server = RestServer(self)
            self.rest_server.start()

        # TPM2Net server
        if self.config.getboolean("MAIN", "TPM2NetServer"):
            self.tpm2_net_server = Tpm2NetServer(self)
            threading.Thread(target=self.tpm2_net_server.serve_forever, daemon=True).start()

    def __stop_servers(self):
        # stop only the servers that are started
        # HTTP server
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()

        # REST server
        if self.rest_server:
            self.rest_server.stop()

        # TPM2Net server
        if self.tpm2_net_server:
            self.tpm2_net_server.shutdown()
            self.tpm2_net_server.server_close()

    def __show_default_animation(self):
        self.animation_controller.start_animation(self.default_animation,
                                                  variant=self.default_animation_variant,
                                                  parameter=self.default_animation_parameter,
                                                  repeat=self.default_animation_repeat)

    def __clear_display(self):
        self.display.clear_buffer()
        self.display.show()

    def start_animation(self, animation_name, variant=None, parameter=None, repeat=0):
        self.animation_controller.start_animation(animation_name, variant=variant, parameter=parameter, repeat=repeat)

    def stop_animation(self, animation_name=None):
        self.animation_controller.stop_animation(animation_name)

        # check if this method was called from start_animation above
        if (sys._getframe().f_back.f_code !=  # code object of the calling method
                self.start_animation.__code__):  # the code object of the above start_animation method
            # if it's NOT called from above, show the default animation
            # because then no other animation will be started afterwards
            self.__show_default_animation()
        else:
            self.__clear_display()

    def is_animation_running(self, animation_name):
        return self.animation_controller.is_animation_running(animation_name)

    def mainloop(self):
        # start the animation controller
        self.animation_controller.start()

        # start the server interfaces
        self.__start_servers()

        # show the default animation
        self.__show_default_animation()

        try:
            while True:
                # check if there is a frame that needs to be displayed
                if not self.frame_queue.empty():
                    # get frame and display it
                    self.display.buffer = self.frame_queue.get()
                    self.frame_queue.task_done()
                    self.display.show(gamma=True)

                # to limit CPU usage do not go faster than 60 "fps"
                time.sleep(1/60)
        except KeyboardInterrupt:
            pass

        self.__clear_display()

        # stop the server interfaces
        self.__stop_servers()


class AnimationController(threading.Thread):
    class _Event():
        def __init__(self, event_type, parameter):
            self.event_type = event_type
            self.event_parameter = parameter

    class _EventType(Enum):
        start = 1
        stop = 2

    def __init__(self, display_width, display_height, display_frame_queue):
        super().__init__(daemon=True)

        self.display_width = display_width
        self.display_height = display_height
        self.display_frame_queue = display_frame_queue

        self.stop_event = threading.Event()
        self.controll_queue = queue.Queue()

        # the current running animation
        self.current_animation = None
        self.animation_lock = threading.RLock()

        # get all available animations
        self.animations = self.__load_animations()

    def __load_animations(self):
        animation_loader = Loader()
        animation_loader.load_plugins((BASE_DIR / "animation").resolve(), AbstractAnimationController)

        animations = {}

        # use module names to identify the animations not the class names
        for _name, cls in animation_loader.plugins.items():
            animations[cls.animation_name] = cls(width=self.display_width, height=self.display_height,
                                                 frame_queue=self.display_frame_queue,
                                                 resources_path=RESOURCES_DIR)

        return animations

    def __start_animation(self, animation_name, variant=None, parameter=None, repeat=0):
        with self.animation_lock:
            # stop any currently running animation
            self.__stop_animation()

            try:
                # get the new animation
                animation = self.animations[animation_name]
            except KeyError:
                eprint("The animation '%s' could not be found!" % animation_name)
            else:
                # start it
                animation.start_animation(variant=variant, parameter=parameter, repeat=repeat)
                self.current_animation = animation

    def __stop_animation(self, animation_name=None):
        with self.animation_lock:
            # if there's already a running animation, stop it
            if self.current_animation is not None:
                # but only if not a specific animation should be stopped
                if (animation_name is not None and
                        self.current_animation.animation_name != animation_name):
                    return
                self.current_animation.stop_animation()
                self.current_animation = None

    def start_animation(self, animation_name, variant=None, parameter=None, repeat=0):
        start_event = AnimationController._Event(AnimationController._EventType.start, {
            "animation_name": animation_name,
            "variant": variant,
            "parameter": parameter,
            "repeat": repeat
        })
        self.controll_queue.put(start_event)

    def stop_animation(self, animation_name=None):
        stop_event = AnimationController._Event(AnimationController._EventType.stop, {
            "animation_name": animation_name
        })
        self.controll_queue.put(stop_event)

    def is_animation_running(self, animation_name):
        try:
            # get the animation
            animation = self.animations[animation_name]
        except KeyError:
            eprint("The animation '%s' could not be found!" % animation_name)
            return False

        return animation.animation_running.is_set()

    def run(self):
        while not self.stop_event.is_set():
            # get the next event
            event = self.controll_queue.get()

            # check the event type
            if event.event_type == AnimationController._EventType.start:
                self.__start_animation(**event.event_parameter)
            elif event.event_type == AnimationController._EventType.stop:
                self.__stop_animation(**event.event_parameter)

            self.controll_queue.task_done()

    def stop(self):
        self.stop_event.set()
        self.join()


if __name__ == "__main__":
    app = Main()
    app.display.show()

    app.mainloop()
