"""Provider to manage and register events.

Events are sent to RabbitMQ, a messaging and streaming broker.
https://www.rabbitmq.com/

The library used is pika
"""
from typing import Any, Callable
import asyncio

from src.relayer.interface.relayer_register import IRelayerRegister
from src.relayer.config.config import Config


class RelayerRegisterProvider(IRelayerRegister):
    """Relayer register provider.

    RabbitMQ is used as messaging and streaming broker.
    """

    def __init__(self) -> None:
        """Init RelayerRegisterEvent.

        Args:
            log_level (str): The log level. Defaults to 'info'.
        """
        # Load config (singleton)
        self.config = Config()
        self.relayer_register_config = self.config.get_register_config()
        self.queue_name: str = self.relayer_register_config.queue_name
        self.callback: Callable
        self.stop_event = asyncio.Event()
        self.semaphore = asyncio.Semaphore(10)
        self.tasks = 0

    async def register_event(self, event: bytes) -> None:
        """Register the event.

        Args:
            event (bytes): An event.

        Raises:
            RelayerRegisterEventFailed
        """
        raise NotImplementedError

    async def read_events(self, callback: Callable[..., Any]) -> None:
        """Read all event tasks.

        Args:
            callback (Callable): A callback function.

        Raises:
            BridgeRelayerReadEventFailed
        """
        raise NotImplementedError
