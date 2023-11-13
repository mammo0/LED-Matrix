from logging import Logger, StreamHandler, getLogger
import logging


def get_logger(name: str) -> Logger:
    logger: Logger = getLogger(name)

    sh: StreamHandler = StreamHandler()
    sh.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
    sh.setFormatter(formatter)

    logger.addHandler(sh)

    return logger
