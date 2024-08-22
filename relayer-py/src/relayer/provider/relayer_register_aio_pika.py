"""
Provider to manage and register events.

Events are sent to RabbitMQ, a messaging and streaming broker.
https://www.rabbitmq.com/

The library used is pika
"""
from typing import Callable, Union
import asyncio
import aio_pika

from src.relayer.interface.relayer_register import IRelayerRegister
from src.relayer.config.config import get_register_config
from src.relayer.domain.exception import (
    RelayerRegisterEventFailed,
    RelayerReadEventFailed,
)
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.application import BaseApp


class RelayerRegisterEvent(RelayerLogging, BaseApp, IRelayerRegister):
    """Relayer register provider

    RabbitMQ is used as messaging and streaming broker.
    """

    def __init__(self, log_level: str = 'info',) -> None:
        """Init RelayerRegisterEvent.

        Args:
            log_level (str): The log level. Defaults to 'info'.
        """
        super().__init__(level=log_level)
        self.relayer_register_config = get_register_config()
        self.queue_name: str = self.relayer_register_config.queue_name
        self.callback: Callable

    # ------------------------------------------------------------------
    # Implemented functions
    # ------------------------------------------------------------------
    async def register_event(self, event: bytes) -> None:
        """Register the event.

        Args:
            event (bytes): An event

        Raises:
            BridgeRelayerRegisterEventFailed
        """
        self.logger.debug(
            f"{self.Emoji.info.value} "
            f"Register message to RabbitMQ "
            f"event={event}"
        )

        try:
            await self._send_message(message=event)

        except Exception as e:
            msg = (
                f"Failed to register message to RabbitMQ "
                f"event={event}, error={e}"
            )
            self.logger.debug(f"{self.Emoji.fail.value} {msg}")
            raise RelayerRegisterEventFailed(e)

    async def read_events(self, callback: Callable) -> None:
        """Consume event tasks.

        Args:
            callback (Callable): A callback function

        Raises:
            BridgeRelayerReadEventFailed
        """
        self.logger.debug(
            f"{self.Emoji.info.value} "
            f"Read message from RabbitMQ "
            f"callback=${callback}"
        )

        try:
            await self._consume_message(callback=callback)

        except Exception as e:
            self.logger.debug(
                f"{self.Emoji.fail.value} "
                f"Failed to read message from RabbitMQ! error={e}"
            )
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
        connection = await aio_pika.connect_robust(url)
        return connection

    async def _send_message(
        self,
        message: Union[str, bytes],
    ) -> None:
        """Send a message to RabbitMQ.

        Args:
            message (Union[str, bytes]): The message

        Raises:
            Exception
        """

        try:
            connection = await self._connection()

            async with connection:
                channel = await connection.channel()

                # Declare queue
                queue = await channel.declare_queue(
                    self.queue_name, durable=True
                )

                # Send message
                await channel.default_exchange.publish(
                    aio_pika.Message(body=message),
                    routing_key=queue.name,
                )
            
            self.logger.debug(
                f"{self.Emoji.info.value} "
                f"Send message to RabbitMQ "
                f"connection={connection} "
                f"channel={channel}"
            )

        except Exception as e:
            self.logger.debug(
                f"{self.Emoji.fail.value} "
                f"Failed to send message to RabbitMQ! error={e}"
            )
            raise

    async def _consume_message(
        self,
        callback: Callable,
    ) -> None:
        """Consume event tasks.

        Args:
            callback (Callable): A callback function

        Raises:
            Exception
        """
        self.logger.debug('Receive message from RabbitMQ')

        try:
            self.callback = callback
            connection = await self._connection()

            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(
                    self.queue_name, 
                    durable=True
                )
                await queue.consume(self._callback)
                await asyncio.Future()

        except Exception as e:
            self.logger.debug(
                f"{self.Emoji.fail.value} "
                f"Failed to receive message from RabbitMQ! error={e}"
            )
            raise

    async def _callback(
        self,
        message: aio_pika.IncomingMessage
    ) -> Union[str, bytes]:
        
        async with message.process():
            await self.callback(message.body)