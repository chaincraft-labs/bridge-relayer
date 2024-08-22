"""Base logging application."""
import logging


class FixedWidthFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """Format the log message with fixed width fields

        Args:
            record (LogRecord): The record to format

        Returns:
            (str): The formatted log message
        """
        # Format the log message with fixed width fields
        levelname = f"{record.levelname:<8}"  # Fixed width for levelname
        asctime = f"{self.formatTime(record, self.datefmt):<23}"  # Fixed width for timestamp
        name = f"{record.name}"  # Fixed width for logger name
        funcName = f"{record.funcName}"  # Fixed width for function name
        lineno = f"{record.lineno}"  # Fixed width for line number
        message = record.getMessage()

        # Combine the formatted fields into the final log message
        if record.levelno == logging.DEBUG:
            formatted_message = f"{asctime} {levelname} {name}.{funcName}.{lineno} {message}"
        else:
            formatted_message = f"{asctime} {levelname} {message} {name}.{funcName}.{lineno}"
        return formatted_message


class RelayerLogging:
    """Base Relayer logging class."""

    def __init__(
        self,
        level: str = 'INFO',
        log_file: str = 'relayer',
    ):
        """Init logger.

        Args:
            level (str, optional): The logging level. Defaults to 'INFO'.
            log_file (str, optional):The log file. Defaults to 'relayer.log'.
        """
        self.level = level.upper()
        self.log_file = f"{log_file}.log"
        self.log_err_file = f"{log_file}.err.log"
        self.log_debug_file = f"{log_file}.debug.log"
        # Use a unique logger name for each instance
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{id(self)}")
        self.logger.setLevel(self.level)

        # Check if the logger already has handlers to avoid duplicating them
        if not self.logger.hasHandlers():
            # Console handler for INFO and DEBUG level logs to stdout
            file_handler_info = logging.FileHandler(self.log_file)
            file_handler_info.setLevel(self.level)
            file_handler_info.addFilter(
                lambda record: record.levelno == logging.INFO)
            file_handler_info.setFormatter(FixedWidthFormatter())
            self.logger.addHandler(file_handler_info)

            # File handler for ERROR level logs to stderr
            file_handler_error = logging.FileHandler(self.log_err_file)
            file_handler_error.setLevel(logging.WARNING)
            file_handler_error.addFilter(
                lambda record: record.levelno >= logging.WARNING)
            file_handler_error.setFormatter(FixedWidthFormatter())
            self.logger.addHandler(file_handler_error)

            if self.level == 'DEBUG':
                # Console handler for DEBUG level logs to stdout
                file_handler_debug = logging.FileHandler(self.log_debug_file)
                file_handler_debug.setLevel(self.level)
                file_handler_debug.addFilter(
                    lambda record: record.levelno <= logging.DEBUG)
                file_handler_debug.setFormatter(FixedWidthFormatter())
                self.logger.addHandler(file_handler_debug)