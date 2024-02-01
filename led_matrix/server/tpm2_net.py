# Protocol Reference
# https://gist.github.com/jblang/89e24e2655be6c463c56

from __future__ import annotations

import socketserver
import time
from socketserver import BaseServer
from threading import Timer
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation.dummy import DUMMY_ANIMATION_NAME, DummyController

if TYPE_CHECKING:
    from led_matrix.main import MainController


class Tpm2NetServer(socketserver.UDPServer):
    def __init__(self, main_app: MainController):
        self.__main_app: MainController = main_app

        self.__display_width: int = self.__main_app.config.main.display_width
        self.__display_height: int = self.__main_app.config.main.display_height

        self.__dummy_animation: DummyController = cast(DummyController,
                                                       self.__main_app.all_animation_controllers[DUMMY_ANIMATION_NAME])

        self.__tmp_buffer: NDArray[np.uint8] = np.zeros((self.__display_height, self.__display_width, 3),
                                                        dtype=np.uint8)
        self.__tmp_buffer_index: int = 0

        # glediator is ok
        # but pixelcontroller is counting the packets wrong.
        # when detected that the stream is misheaving then count also wrong
        self.__misbehaving: bool = False

        self.__timeout: int = 3  # seconds
        self.__last_time_received: float | None = None
        self.__timeout_timer: Timer | None = None

        super().__init__(('', 65506), Tpm2NetHandler, bind_and_activate=True)

    @property
    def main_app(self) -> MainController:
        return self.__main_app

    @property
    def dummy_animation(self) -> DummyController:
        return self.__dummy_animation

    @property
    def tmp_buffer(self) -> NDArray[np.uint8]:
        return self.__tmp_buffer

    @property
    def tmp_buffer_index(self) -> int:
        return self.__tmp_buffer_index

    @tmp_buffer_index.setter
    def tmp_buffer_index(self, value: int) -> None:
        self.__tmp_buffer_index = value

    @property
    def is_misbehaving(self) -> bool:
        return self.__misbehaving

    @is_misbehaving.setter
    def is_misbehaving(self, value: bool) -> None:
        self.__misbehaving = value

    def update_time(self) -> None:
        if self.__last_time_received is None and self.__timeout_timer is None:
            self.__timeout_timer = Timer(0.5, self.__check_for_timeout)
            self.__timeout_timer.start()

        # to detect timeout store current time
        self.__last_time_received = time.time()

    def __check_for_timeout(self) -> None:
        if self.__last_time_received is not None:
            if self.__last_time_received + self.__timeout < time.time():
                # stop dummy animation
                self.__main_app.stop_animation(self.__dummy_animation.animation_name)

                self.__last_time_received = None
                self.__timeout_timer = None
                self.__misbehaving = False
            else:
                # restart a timer
                self.__timeout_timer = None
                self.__timeout_timer = Timer(0.5, self.__check_for_timeout)
                self.__timeout_timer.start()


class Tpm2NetHandler(socketserver.BaseRequestHandler):
    def __init__(self, request: Any, client_address: Any, server: BaseServer) -> None:
        super().__init__(request, client_address, server)

        # for type checking
        self.server: Tpm2NetServer = cast(Tpm2NetServer, self.server)

    def handle(self) -> None:
        data: bytearray = self.request[0].strip()
        data_length: int = len(data)

        # check packet start byte 0x9C
        if not data_length >= 8 and data[0] == 0x9c:
            return

        packet_type: int = data[1]
        frame_size: int = (data[2] << 8) + data[3]

        # check consistency of length and proper frame ending
        if not (data_length - 7 == frame_size) and data[-1] == 0x36:
            return

        packet_number: int = data[4]
        number_of_packets: int = data[5]

        if packet_type == 0xDA:  # data frame
            # tell main_app that tpm2_net data is received
            if not self.server.dummy_animation.is_running:
                # use dummy animation, because the frame_queue gets filled here
                self.server.main_app.start_animation(
                    animation_name=self.server.dummy_animation.animation_name,
                    animation_settings=self.server.dummy_animation.default_settings,
                    pause_current_animation=True
                )

            self.server.update_time()

            if packet_number == 0:
                self.server.is_misbehaving = True
            if packet_number == (1 if not self.server.is_misbehaving else 0):
                self.server.tmp_buffer_index = 0

            upper: int = min(self.server.tmp_buffer.size,
                             self.server.tmp_buffer_index + frame_size)
            arange: NDArray[np.int_] = np.arange(self.server.tmp_buffer_index,
                                                 upper,
                                                 dtype=np.int_)
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
