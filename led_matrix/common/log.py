from __future__ import annotations

import logging
from importlib import resources
from logging import Formatter, Logger
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from led_matrix.common.alpine import IS_ALPINE_LINUX

# logging file
LOG_FILE_PATH: Path
if IS_ALPINE_LINUX:
    LOG_FILE_PATH = Path("/") / "var" / "log" / "led-matrix"
else:
    with resources.as_file(resources.files("led_matrix")) as LOG_FILE_PATH:
        LOG_FILE_PATH = LOG_FILE_PATH.resolve().parent / "logs"
# first create the logging directory
LOG_FILE_PATH.mkdir(parents=True, exist_ok=True)
# then define the final path to the file
LOG_FILE_PATH = LOG_FILE_PATH / "led-matrix.log"


class _LOGMeta(type):
    def __init__(cls, name: str, bases: tuple[type, ...], classdict: dict[str, Any]) -> None:
        super().__init__(name, bases, classdict)

        cls._handler: TimedRotatingFileHandler = TimedRotatingFileHandler(LOG_FILE_PATH,
                                                    when="H",
                                                    backupCount=7,
                                                    encoding="utf-8")
        cls._handler.setFormatter(
            Formatter(fmt="%(asctime)s - %(levelname)-8s :: %(name)s :: %(message)s")
        )


class LOG(metaclass=_LOGMeta):
    @classmethod
    def create(cls, name: str, level: int=logging.NOTSET) -> Logger:
        logger: Logger = Logger(name, level)
        logger.addHandler(cls._handler)

        return logger
