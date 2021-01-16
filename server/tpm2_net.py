# Protocol Reference
# https://gist.github.com/jblang/89e24e2655be6c463c56

import socketserver
import time
from threading import Timer
import numpy as np


class Tpm2NetServer(socketserver.UDPServer):
    def __init__(self, main_app, display_width, display_height):
        super().__init__(('', 65506), Tpm2NetHandler, bind_and_activate=True)
        self.main_app = main_app
        self.tmp_buffer = np.zeros((display_height, display_width, 3),
                                   dtype=np.uint8)
        self.tmp_buffer_index = 0
        self.timeout = 3  # seconds
        self.last_time_received = None
        self.timeout_timer = None
        # glediator is ok
        # but pixelcontroller is counting the packets wrong.
        # when detected that the stream is misheaving then count also wrong
        self.misbehaving = False

    def update_time(self):
        if not self.last_time_received:
            # start a timer if there is None
            if not self.timeout_timer:
                self.timeout_timer = Timer(0.5, self.check_for_timeout)
                self.timeout_timer.start()
        # to detect timeout store current time
        self.last_time_received = time.time()

    def check_for_timeout(self):
        if self.last_time_received:
            if self.last_time_received + self.timeout < time.time():
                # stop dummy animation
                self.main_app.stop_animation("dummy")
                self.last_time_received = None
                self.timeout_timer = None
                self.misbehaving = False
            else:
                # restart a timer
                self.timeout_timer = None
                self.timeout_timer = Timer(0.5, self.check_for_timeout)
                self.timeout_timer.start()


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
            if not self.server.main_app.is_animation_running("dummy"):
                # use dummy animation, because the frame_queue gets filled here
                self.server.main_app.start_animation("dummy")
            self.server.update_time()

            if packet_number == 0:
                self.server.misbehaving = True
            if packet_number == (1 if not self.server.misbehaving else 0):
                self.server.tmp_buffer_index = 0

            upper = min(self.server.tmp_buffer.size,
                        self.server.tmp_buffer_index + frame_size)
            arange = np.arange(self.server.tmp_buffer_index,
                               upper)
            np.put(self.server.tmp_buffer, arange, list(data[6:-1]))
            self.server.tmp_buffer_index = self.server.tmp_buffer_index + frame_size
            if packet_number == (number_of_packets if not self.server.misbehaving else number_of_packets - 1):
                if self.server.main_app.is_animation_running("dummy"):
                    self.server.main_app.frame_queue.put(self.server.tmp_buffer.copy())
        elif data[1] == 0xC0:  # command
            # NOT IMPLEMENTED
            return
        elif data[1] == 0xAA:  # request response
            # NOT IMPLEMENTED
            return
        else:  # no valid tmp2 packet type
            return
