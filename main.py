#!/usr/bin/env python3

from configparser import NoSectionError, NoOptionError
import os
from pathlib import Path
import queue
import threading
import time

from simple_plugin_loader import Loader

from animation.abstract import AbstractAnimationController
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
        # TODO: remove this later; use absolute paths for loading resources below
        os.chdir(BASE_DIR)

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

        # get all available animations
        self.animations = self.__load_animations()

        # the current running animation
        self.current_animation = None
        self.animation_lock = threading.RLock()

        # this is the queue that holds the frames to display
        self.frame_queue = queue.Queue(maxsize=1)

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

    def __load_animations(self):
        animation_loader = Loader()
        animation_loader.load_plugins((BASE_DIR / "animation").resolve(), AbstractAnimationController)

        animations = {}

        # use module names to identify the animations not the class names
        for _name, cls in animation_loader.plugins.items():
            name = cls.__module__.rpartition(".")[-1]
            animations[name] = cls(width=self.display_width, height=self.display_height,
                                   frame_queue=self.frame_queue,
                                   resources_path=RESOURCES_DIR)

        return animations

    def __show_default_animation(self):
        # TODO: make this method thread-safe (animation_lock)
        pass

    def start_animation(self, animation_name, variant=None, parameter=None, repeat=0):
        # TODO: this is for the servers
        # TODO: make this method thread-safe (animation_lock)
        pass

    def stop_animation(self):
        # TODO: this is for the servers
        # TODO: make this method thread-safe (animation_lock)
        pass

    def mainloop(self):
        # start the server interfaces
        self.__start_servers()

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

        self.display.clear_buffer()
        self.display.show()

        # stop the server interfaces
        self.__stop_servers()


if __name__ == "__main__":
    app = Main()
    app.display.show()

    app.mainloop()
