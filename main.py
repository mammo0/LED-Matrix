#!/usr/bin/env python3

import argparse
from enum import Enum
from pathlib import Path
import queue
import signal
import sys
import threading

from simple_plugin_loader import Loader

from animation.abstract import AbstractAnimationController
from common import BASE_DIR, RESOURCES_DIR, DEFAULT_CONFIG_FILE, eprint
from common.config import Configuration, Config
from display.abstract import AbstractDisplay
from server.http_server import HttpServer
from server.rest_server import RestServer
from server.tpm2_net import Tpm2NetServer


# TODO:
# add timer that displays a textmessage from predefined list of messages
# restructure other animations
# make mood light animation
class Main():
    def __init__(self, config_file_path=None):
        # catch SIGINT, SIGQUIT and SIGTERM
        self.quit_signal = threading.Event()
        signal.signal(signal.SIGINT, self.__quit)
        signal.signal(signal.SIGQUIT, self.__quit)
        signal.signal(signal.SIGTERM, self.__quit)

        # needed for 'set_brightness' method
        self.display = None

        # load config
        if config_file_path is None:
            config_file_path = DEFAULT_CONFIG_FILE
        self.config = Configuration(config_file_path=config_file_path, allow_no_value=True)
        self.__load_settings()

        # this is the queue that holds the frames to display
        self.frame_queue = queue.Queue(maxsize=1)

        # animation controller
        self.animation_controller = AnimationController(self.display_width, self.display_height, self.frame_queue)

        # server interfaces
        self.http_server = None
        self.rest_server = None
        self.tpm2_net_server = None

        self.reload_signal = threading.Event()

    def __load_settings(self):
        # get [MAIN] options
        hardware = self.config.get(Config.MAIN.Hardware)
        self.display_width = self.config.get(Config.MAIN.DisplayWidth)
        self.display_height = self.config.get(Config.MAIN.DisplayHeight)
        self.set_brightness(self.config.get(Config.MAIN.Brightness))

        # get [DEFAULTANIMATION] options
        self.default_animation = self.config.get(Config.DEFAULTANIMATION.Animation)
        self.default_animation_variant = self.config.get(Config.DEFAULTANIMATION.Variant)
        self.default_animation_parameter = self.config.get(Config.DEFAULTANIMATION.Parameter)
        self.default_animation_repeat = self.config.get(Config.DEFAULTANIMATION.Repeat)

        # load display plugins
        display_loader = Loader()
        display_loader.load_plugins((BASE_DIR / "display").resolve(), plugin_base_class=AbstractDisplay)

        try:
            self.display = display_loader.plugins[hardware.casefold()](self.display_width,
                                                                       self.display_height,
                                                                       self.display_brightness,
                                                                       config=self.config)
        except KeyError:
            raise RuntimeError("Display hardware '{}' not known.".format(hardware))

    def __start_servers(self):
        # HTTP server
        if (self.config.get(Config.MAIN.HttpServer) and
                # if the variable is set, that means we're in a reload phase
                # so the server is already started
                self.http_server is None):
            self.http_server = HttpServer(self)
            self.http_server.start()

        # REST server
        if (self.config.get(Config.MAIN.RestServer) and
                # if the variable is set, that means we're in a reload phase
                # so the server is already started
                self.rest_server is None):
            self.rest_server = RestServer(self)
            self.rest_server.start()

        # TPM2Net server
        if self.config.get(Config.MAIN.TPM2NetServer):
            self.tpm2_net_server = Tpm2NetServer(self, self.display_width, self.display_height)
            threading.Thread(target=self.tpm2_net_server.serve_forever, daemon=True).start()

    def __stop_servers(self):
        # stop only the servers that are started
        # except on reload, then do not stop the HTTP and REST server
        if not self.reload_signal.is_set():
            # HTTP server
            if self.http_server:
                self.http_server.stop()

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

    def __quit(self, *_):
        print("Exiting...")
        self.quit_signal.set()

    def reload(self):
        print("Reloading...")

        # set the reload and quit signal to exit mainloop
        self.reload_signal.set()
        self.quit_signal.set()

        # wait until the the reload_signal is unset
        with self.reload_signal._cond:
            self.reload_signal._cond.wait_for(lambda: not self.reload_signal.is_set())

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

    @property
    def available_animations(self):
        return self.animation_controller.available_animations

    def is_animation_running(self, animation_name):
        return self.animation_controller.is_animation_running(animation_name)

    def set_brightness(self, brightness):
        if not 0 <= brightness <= 100:
            eprint("Invalid brightness value '%d'! Using default value '85'." % self.display_brightness)
            self.display_brightness = 85
        else:
            self.display_brightness = brightness

        # apply to the current display if it's already initialized
        if self.display:
            self.display.set_brightness(brightness)

    def mainloop(self):
        # start the animation controller
        self.animation_controller = AnimationController(self.display_width, self.display_height, self.frame_queue)
        self.animation_controller.start()

        # start the server interfaces
        self.__start_servers()

        # show the default animation
        self.__show_default_animation()

        first_loop = True
        # run until '__quit' method was called
        while not self.quit_signal.is_set():
            # check if there is a frame that needs to be displayed
            if not self.frame_queue.empty():
                # get frame and display it
                self.display.buffer = self.frame_queue.get()
                self.frame_queue.task_done()
                self.display.show(gamma=True)

                # after the first frame is displayed, clear the reload signal
                if first_loop:
                    self.reload_signal.clear()
                    # notify reload method, that reloading is done
                    with self.reload_signal._cond:
                        self.reload_signal._cond.notify_all()

            # to limit CPU usage do not go faster than 60 "fps"
            self.quit_signal.wait(1/60)

        self.animation_controller.stop()
        self.__clear_display()

        # stop the server interfaces
        self.__stop_servers()

        if self.reload_signal.is_set():
            # reload settings
            self.__load_settings()

            # clear quit signal
            # the reload signal gets cleared after the first frame is displayed again
            self.quit_signal.clear()

            # restart mainloop
            self.mainloop()


class AnimationController(threading.Thread):
    class _Event():
        def __init__(self, event_type, animation_name, parameter={}):
            self.event_type = event_type
            self.animation_name = animation_name
            self.event_parameter = parameter

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

    def __init__(self, display_width, display_height, display_frame_queue):
        super().__init__(daemon=True)

        self.display_width = display_width
        self.display_height = display_height
        self.display_frame_queue = display_frame_queue

        self.stop_event = threading.Event()
        self.controll_queue = AnimationController._EventQueue()

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
        start_event = AnimationController._Event(AnimationController._EventType.start,
                                                 animation_name,
                                                 {
                                                     "variant": variant,
                                                     "parameter": parameter,
                                                     "repeat": repeat
                                                 })
        self.controll_queue.put(start_event)

    def stop_animation(self, animation_name=None):
        stop_event = AnimationController._Event(AnimationController._EventType.stop,
                                                animation_name)
        self.controll_queue.put(stop_event)

    @property
    def available_animations(self):
        return self.animations

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

            # sometimes get can take a while to return, so check the stop flag again here
            if self.stop_event.is_set():
                self.controll_queue.task_done()
                break

            # check the event type
            if event.event_type == AnimationController._EventType.start:
                self.__start_animation(event.animation_name, **event.event_parameter)
            elif event.event_type == AnimationController._EventType.stop:
                self.__stop_animation(event.animation_name, **event.event_parameter)

            self.controll_queue.task_done()

    def stop(self):
        self.stop_event.set()
        # add a new element into the control_queue to force returning of get method in loop
        self.controll_queue.put(None)
        self.join()

        # after the control thread has stopped, there could be an animation thread remaining
        # so stop this animation
        self.__stop_animation()


if __name__ == "__main__":
    # cli parser
    parser = argparse.ArgumentParser(description="LED-Matrix main control application.")
    parser.add_argument("-c", "--config-file", type=Path,
                        help="The path of the configuration file.")

    # get config path
    args = parser.parse_args(sys.argv[1:])

    # load the main application
    app = Main(args.config_file)
    app.display.show()

    app.mainloop()
