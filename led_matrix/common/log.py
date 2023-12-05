import logging
import sys
from logging import Formatter, Logger, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from led_matrix.common.alpine import IS_ALPINE_LINUX


class _LOGMeta(type):
    def __init__(cls, name: str, bases: tuple[type, ...], classdict: dict[str, Any]) -> None:
        super().__init__(name, bases, classdict)

        cls.__handler: StreamHandler
        if IS_ALPINE_LINUX:
            log_file_path: Path = Path("/") / "var" / "log" / "led-matrix"

            # first create the logging directory
            log_file_path.mkdir(parents=True, exist_ok=True)
            # then define the final path to the file
            log_file_path = log_file_path / "led-matrix.log"

            cls.__handler = TimedRotatingFileHandler(log_file_path,
                                                     when="H",
                                                     backupCount=7,
                                                     encoding="utf-8")
        else:
            cls.__handler = StreamHandler(stream=sys.stdout)

        cls.__handler.setFormatter(
            Formatter(fmt="%(asctime)s - %(levelname)-8s :: %(name)s :: %(message)s")
        )

    @property
    def handler(cls) -> StreamHandler:
        return cls.__handler


class LOG(metaclass=_LOGMeta):
    @classmethod
    def create(cls, name: str, level: int=logging.NOTSET) -> Logger:
        logger: Logger = Logger(name, level)
        logger.addHandler(cls.handler)

        return logger
