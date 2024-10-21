"""Base logging application."""
import logging
import os
import sys

current_dir: str = os.path.dirname(os.path.abspath(__file__))
parent_dir: str = os.path.dirname(current_dir)
sys.path.append(parent_dir)


class FixedWidthFormatter(logging.Formatter):
    """Log formatter with fixed width fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log message with fixed width fields.

        Args:
            record (LogRecord): The record to format

        Returns:
            (str): The formatted log message
        """
        # Format the log message with fixed width fields
        # Fixed width for levelname
        levelname = f"{record.levelname:<8}"
        # Fixed width for timestamp
        asctime = f"{self.formatTime(record, self.datefmt):<23}"
        # Fixed width for logger name
        name = f"{record.name}"
        # Fixed width for function name
        funcName = f"{record.funcName}"
        # Fixed width for line number
        lineno = f"{record.lineno}"
        message = record.getMessage()

        # Combine the formatted fields into the final log message
        if record.levelno == logging.DEBUG:
            formatted_message = (
                f"{asctime} {levelname} {name}.{funcName}.{lineno} {message}"
            )
        else:
            formatted_message = (
                f"{asctime} {levelname} {message} {name}.{funcName}.{lineno}"
            )
        return formatted_message


class RelayerLogging:
    """Base Relayer logging class."""

    # A class-level dictionary to store loggers and avoid duplicate handlers
    loggers = {}

    def __init__(
        self,
        level: str = 'INFO',
        log_file: str = 'relayer',
        log_dir: str = 'data',
    ):
        """Init logger."""
        self.level = level.upper()

        self.log_file = f"{log_file}.log"
        self.log_err_file = f"{log_file}.err.log"
        self.log_debug_file = f"{log_file}.debug.log"

        # Check if logger already exists to avoid re-creating it
        if self.log_file in RelayerLogging.loggers:
            self.logger = RelayerLogging.loggers[self.log_file]
        else:
            # Initialize logger with a unique name based on the class
            # #and instance id
            self.logger = logging.getLogger(
                f"{self.__class__.__name__}_{id(self)}"
            )
            self.logger.setLevel(self.level)

            # File handler for INFO logs (only add if not already present)
            if not any(
                isinstance(h, logging.FileHandler)
                and h.baseFilename == self.log_file
                for h in self.logger.handlers
            ):
                file_handler_info = logging.FileHandler(self.log_file)
                file_handler_info.setLevel(logging.INFO)
                file_handler_info.setFormatter(FixedWidthFormatter())
                self.logger.addHandler(file_handler_info)

            # File handler for ERROR logs (only add if not already present)
            if not any(
                isinstance(h, logging.FileHandler)
                and h.baseFilename == self.log_err_file
                for h in self.logger.handlers
            ):
                file_handler_error = logging.FileHandler(self.log_err_file)
                file_handler_error.setLevel(logging.WARNING)
                file_handler_error.setFormatter(FixedWidthFormatter())
                self.logger.addHandler(file_handler_error)

            # Optionally add a DEBUG log handler
            if self.level == 'DEBUG' and not any(
                isinstance(h, logging.FileHandler)
                and h.baseFilename == self.log_debug_file
                for h in self.logger.handlers
            ):
                file_handler_debug = logging.FileHandler(self.log_debug_file)
                file_handler_debug.setLevel(logging.DEBUG)
                file_handler_debug.setFormatter(FixedWidthFormatter())
                self.logger.addHandler(file_handler_debug)

            # Save the logger in the class-level dictionary
            RelayerLogging.loggers[self.log_file] = self.logger
