# Protocol Reference
# https://gist.github.com/jblang/89e24e2655be6c463c56

import socketserver
import time
from threading import Timer
import numpy as np


class Tpm2NetServer(socketserver.UDPServer):
    def __init__(self, main_app, display_width, display_height):
        self.__main_app = main_app
        self.__display_width = display_width
        self.__display_height = display_height

        self.__dummy_animation = self.__main_app.available_animations["dummy"]

        self.__tmp_buffer = np.zeros((self.__display_height, self.__display_width, 3),
                                     dtype=np.uint8)
        self.__tmp_buffer_index = 0

        # glediator is ok
        # but pixelcontroller is counting the packets wrong.
        # when detected that the stream is misheaving then count also wrong
        self.__misbehaving = False

        self.__timeout = 3  # seconds
        self.__last_time_received = None
        self.__timeout_timer = None

        super().__init__(('', 65506), Tpm2NetHandler, bind_and_activate=True)

    @property
    def main_app(self):
        return self.__main_app

    @property
    def dummy_animation(self):
        return self.__dummy_animation

    @property
    def tmp_buffer(self):
        return self.__tmp_buffer

    @property
    def tmp_buffer_index(self):
        return self.__tmp_buffer_index

    @tmp_buffer_index.setter
    def tmp_buffer_index(self, value):
        self.__tmp_buffer_index = value

    @property
    def is_misbehaving(self):
        return self.__misbehaving

    def update_time(self):
        if not self.__last_time_received:
            # start a timer if there is None
            if not self.__timeout_timer:
                self.__timeout_timer = Timer(0.5, self.__check_for_timeout)
                self.__timeout_timer.start()
        # to detect timeout store current time
        self.__last_time_received = time.time()

    def __check_for_timeout(self):
        if self.__last_time_received:
            if self.__last_time_received + self.__timeout < time.time():
                # stop dummy animation
                self.__main_app.stop_animation(self.__dummy_animation.default_animation_settings.animation_name)
                self.__last_time_received = None
                self.__timeout_timer = None
                self.__misbehaving = False
            else:
                # restart a timer
                self.__timeout_timer = None
                self.__timeout_timer = Timer(0.5, self.__check_for_timeout)
                self.__timeout_timer.start()


class Tpm2NetHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        data_length = len(data)
        # check packet start byte 0x9C
        if not data_length >= 8 and data[0] == 0x9c:
            return
        packet_type = data[1]
        frame_size = (data[2] << 8) + data[3]
        # check consistency of length and proper frame ending
        if not (data_length - 7 == frame_size) and data[-1] == 0x36:
            return

        packet_number = data[4]
        number_of_packets = data[5]

        if packet_type == 0xDA:  # data frame
            # tell main_app that tpm2_net data is received
            if not self.server.dummy_animation.is_running:
                # use dummy animation, because the frame_queue gets filled here
                self.server.main_app.start_animation(self.server.dummy_animation.default_animation_settings,
                                                     pause_current_animation=True)
            self.server.update_time()

            if packet_number == 0:
                self.server.is_misbehaving = True
            if packet_number == (1 if not self.server.is_misbehaving else 0):
                self.server.tmp_buffer_index = 0

            upper = min(self.server.tmp_buffer.size,
                        self.server.tmp_buffer_index + frame_size)
            arange = np.arange(self.server.tmp_buffer_index,
                               upper)
            np.put(self.server.tmp_buffer, arange, list(data[6:-1]))
            self.server.tmp_buffer_index += frame_size
            if packet_number == (number_of_packets if not self.server.is_misbehaving else number_of_packets - 1):
                self.server.dummy_animation.display_frame(self.server.tmp_buffer.copy())
        elif data[1] == 0xC0:  # command
            # NOT IMPLEMENTED
            return
        elif data[1] == 0xAA:  # request response
            # NOT IMPLEMENTED
            return
        else:  # no valid tmp2 packet type
            return
