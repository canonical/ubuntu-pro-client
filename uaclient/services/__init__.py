import logging
import sys

from uaclient.defaults import DEFAULT_LOG_FORMAT


def setup_logging(console_level, log_level, log_file, logger):
    logger.setLevel(log_level)

    logger.handlers = []

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(console_level)
    console_handler.set_name("ua-console")
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    file_handler.set_name("ua-file")
    logger.addHandler(file_handler)
