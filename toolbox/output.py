import logging
import sys
from logging import Formatter

import click

CMD_LEVEL = 25
logging.addLevelName(CMD_LEVEL, "CMD")


class _ColoredFormatter(logging.Formatter):
    COLORS: dict[str, str] = {
        "DEBUG": "bright_cyan",
        "INFO": "bright_blue",
        "CMD": "bright_green",
        "WARNING": "bright_yellow",
        "ERROR": "bright_red",
        "CRITICAL": "bright_white",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datefmt = "%Y-%m-%d %H:%M:%S"  # Customize this string

    def format(self, record: logging.LogRecord) -> object:
        record.msg = click.style(
            str(record.msg), fg=self.COLORS.get(record.levelname, "bright_white")
        )
        pretty = f"{record.levelname}:"
        record.levelname = click.style(
            f"{pretty:<5}",
            bold=True,
            fg=self.COLORS.get(record.levelname, "bright_white"),
        )

        record.asctime = self.formatTime(record)
        record.asctime = click.style(record.asctime, fg="red")

        # Call the parent class format method
        return super().format(record)


class _Logger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(_Logger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "is_initialized"):
            handler = logging.StreamHandler(sys.stdout)

            # if output is a terminal, use colored formatter else use plain formatter
            if sys.stdout.isatty():
                formatter: ColoredFormatter = _ColoredFormatter(
                    "%(levelname)s  %(message)s"
                )
            else:
                formatter: Formatter = logging.Formatter(
                    "%(asctime)s  %(levelname)s  %(message)s"
                )

            handler.setFormatter(formatter)
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

            self.is_initialized = True

    def info(self, message: str) -> None:
        self.logger.info(message)

    def cmd(self, message: str) -> None:
        self.logger.log(CMD_LEVEL, message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)
        sys.exit(1)


l = _Logger()

if __name__ == "__main__":
    l = _Logger()
    l.info("This is an info message.")
