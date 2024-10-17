"""Provider to manage and register events.

Events are sent to RabbitMQ, a messaging and streaming broker.
https://www.rabbitmq.com/

The library used is pika
"""
import signal
from typing import Callable, Union
import asyncio
import aio_pika

from src.relayer.interface.relayer_register import IRelayerRegister
from src.relayer.config.config import Config
from src.relayer.domain.exception import (
    RelayerRegisterEventFailed,
    RelayerReadEventFailed,
)


class RelayerRegisterEvent(IRelayerRegister):
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

    # ------------------------------------------------------------------
    # Implemented functions
    # ------------------------------------------------------------------
    async def register_event(self, event: bytes) -> None:
        """Register the event.

        Args:
            event (bytes): An event.

        Raises:
            RelayerRegisterEventFailed
        """
        try:
            await self._send_message(message=event)

        except Exception as e:
            raise RelayerRegisterEventFailed(e)

    async def read_events(self, callback: Callable) -> None:
        """Read all event tasks.

        Args:
            callback (Callable): A callback function.

        Raises:
            BridgeRelayerReadEventFailed
        """
        try:
            self._callback = callback
            loop = asyncio.get_running_loop()

            # Capture the Ctrl+C signal and call shutdown
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda sig=sig: asyncio.create_task(
                        self.shutdown(loop, sig)
                    )
                )

            try:
                await self._consume_message()
            finally:
                pass

        except Exception as e:
            raise RelayerReadEventFailed(e)

    # ------------------------------------------------------------------
    # Internal functions
    # ------------------------------------------------------------------
    async def _connection(self) -> aio_pika.RobustConnection:
        """Connect to RabbitMQ.

        Returns:
            (aio_pika.RobustConnection): The connection
        """
        user = self.relayer_register_config.user
        password = self.relayer_register_config.password
        host = self.relayer_register_config.host
        port = self.relayer_register_config.port
        url = f"amqp://{user}:{password}@{host}:{port}/"
        return await aio_pika.connect(url)

    async def _send_message(self, message: Union[str, bytes]) -> None:
        """Send a message to RabbitMQ.

        Args:
            message (Union[str, bytes]): The message

        Raises:
            Exception
        """
        try:
            connection: aio_pika.RobustConnection = await self._connection()
            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(
                    self.queue_name,
                    durable=True,
                )
                await channel.default_exchange.publish(
                    aio_pika.Message(body=message),
                    routing_key=queue.name,
                )

        except Exception:
            raise

    async def _consume_message(self) -> None:
        """Consume event tasks.

        Args:
            callback (Callable): A callback function

        Raises:
            Exception
        """
        try:
            connection: aio_pika.RobustConnection = await self._connection()
            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(
                    self.queue_name,
                    durable=True
                )
                await queue.consume(self.callback)
                await asyncio.Future()
        except Exception:
            raise

    def stop(self):
        """Signal the event to stop consuming messages."""
        self.stop_event.set()

    async def callback(self, message: aio_pika.IncomingMessage) -> None:
        """Process the received message and update a file."""
        async with message.process():
            try:
                message_data = message.body
                await self._callback(message_data)
            except Exception:
                return

    async def shutdown(self, loop, signal=None):
        """Cleanup tasks gracefully after receiving a signal."""
        if signal:
            print(f"Received exit signal {signal.name}...")

        tasks = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task()
        ]

        print(f"Cancelling {len(tasks)} outstanding tasks")
        for task in tasks:
            task.cancel()

        # Wait until all tasks are cancelled
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"Cancelled tasks results: {results}")

        loop.stop()
