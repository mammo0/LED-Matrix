# Protocol Reference
# https://gist.github.com/jblang/89e24e2655be6c463c56

from __future__ import annotations

import operator
import time
from functools import reduce
from socket import socket
from socketserver import BaseRequestHandler, UDPServer
from threading import Timer
from typing import TYPE_CHECKING, Any, Final, Literal, cast

import numpy as np
from numpy.typing import NDArray

from led_matrix.animation import DUMMY_ANIMATION_NAME
from led_matrix.animation.dummy import DummyController

if TYPE_CHECKING:
    from led_matrix.main import MainController


class Tpm2NetServer(UDPServer):
    def __init__(self, main_app: MainController):
        self.__main_app: MainController = main_app

        self.__dummy_animation: DummyController = cast(DummyController,
                                                       self.__main_app.all_animation_controllers[DUMMY_ANIMATION_NAME])

        self.__tmp_buffer_shape: Final[tuple[int, int, Literal[3]]] = (self.__main_app.config.main.display_height,
                                                                       self.__main_app.config.main.display_width,
                                                                       3)
        self.__tmp_buffer_index: int = 0

        # glediator is ok
        # but pixelcontroller is counting the packets wrong.
        # when detected that the stream is misheaving then count also wrong
        self.__misbehaving: bool = False

        self.__timeout: int = 3  # seconds
        self.__last_received_time: float | None = None

        super().__init__(('', 65506), BaseRequestHandler, bind_and_activate=True)

    def process_request(self, request: tuple[bytes, socket], client_address: Any) -> None:
        """
        Override BaseServer.process_request() method.

        UDPServer.shutdown_request() does nothing, so it's not needed to be called in the process_request() method.
        """
        data: bytes = request[0].strip()
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
            if not self.__dummy_animation.is_running:
                # use dummy animation, because the frame_queue gets filled here
                self.__main_app.start_animation(
                    animation_name=self.__dummy_animation.animation_name,
                    animation_settings=self.__dummy_animation.default_settings,
                    pause_current_animation=True,
                    block_until_started=True
                )

            if packet_number == 0:
                self.__misbehaving = True
            if packet_number == (1 if not self.__misbehaving else 0):
                self.__tmp_buffer_index = 0

            upper: int = min(reduce(operator.mul, self.__tmp_buffer_shape),
                             self.__tmp_buffer_index + frame_size)
            tmp_buffer: NDArray[np.uint8] = np.frombuffer(data,
                                                          dtype=np.uint8,
                                                          count=upper, offset=6).reshape(self.__tmp_buffer_shape)

            self.__tmp_buffer_index += frame_size

            if packet_number == (number_of_packets if not self.__misbehaving else number_of_packets - 1):
                self.__dummy_animation.display_frame(tmp_buffer)

            # set the flag that a data package was received and processed
            self.__package_received_and_processed()

        elif data[1] == 0xC0:  # command
            # NOT IMPLEMENTED
            return
        elif data[1] == 0xAA:  # request response
            # NOT IMPLEMENTED
            return
        else:  # no valid tmp2 packet type
            return

    def __package_received_and_processed(self) -> None:
        # save the current timestamp
        if self.__last_received_time is None:
            self.__last_received_time = time.time()

            # also start the timeout timer
            Timer(self.__timeout, self.__check_for_timeout).start()
        else:
            self.__last_received_time = time.time()

    def __clear_last_received_time(self) -> None:
        self.__last_received_time = None

    def __check_for_timeout(self) -> None:
        # get the current time
        current_time: float = time.time()
        # and the timestamp of the last received package
        last_received_time: float | None = self.__last_received_time

        if last_received_time is not None:
            time_diff: float = current_time - last_received_time

            # check if the time difference
            if time_diff >= self.__timeout:
                # stop dummy animation
                self.__main_app.stop_animation(self.__dummy_animation.animation_name)

                self.__clear_last_received_time()
                self.__misbehaving = False

            # restart the timeout timer
            elif time_diff < 1:
                Timer(self.__timeout, self.__check_for_timeout).start()
            else:
                Timer(time_diff, self.__check_for_timeout).start()
