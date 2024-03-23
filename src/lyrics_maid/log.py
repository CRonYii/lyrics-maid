import logging

from colorlog import ColoredFormatter

formatter = ColoredFormatter(
    "[%(name)s] %(log_color)s%(message)s%(reset)s",
    datefmt=None,
    reset=True,
    log_colors={
        "DEBUG": "black",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    secondary_log_colors={},
    style="%",
)

logger = logging.getLogger("lyrics-maid")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)
