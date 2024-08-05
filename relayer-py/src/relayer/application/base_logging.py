""""""
import logging


class RelayerLogging:
    """Base Relayer logging class."""

    def __init__(self):
        """Init the logging."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s.%(funcName)s - %(lineno)s - %(levelname)s - %(message)s')

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
