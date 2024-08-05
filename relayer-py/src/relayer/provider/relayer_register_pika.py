"""
Provider that aims to manage and register events.

Events are sent to RabbitMQ, a messaging and streaming broker.
https://www.rabbitmq.com/
"""
from typing import Any, Callable, Union

from pika import (
    BasicProperties,
    BlockingConnection,
    ConnectionParameters,
    DeliveryMode,
    PlainCredentials,
)
from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError

from src.relayer.interface.relayer import IRelayerRegister
from src.relayer.config.config import get_register_config
from src.relayer.domain.exception import (
    BridgeRelayerRegisterChannelError,
    BridgeRelayerRegisterConnectionError,
    BridgeRelayerRegisterCredentialError,
    BridgeRelayerRegisterDeclareQueueError,
    BridgeRelayerRegisterEventFailed,
    BridgeRelayerReadEventFailed,
)
from src.relayer.application.base_logging import RelayerLogging


class RelayerRegisterEvent(RelayerLogging, IRelayerRegister):
    """Relayer register provider

    RabbitMQ is used as messaging and streaming broker.
    """

    def __init__(self) -> None:
        """Init RelayerRegisterEvent.

        Args:
            debug (bool, optional): Enable/disable logging. Defaults to False.
        """
        super().__init__()
        self.relayer_register_config = get_register_config()
        self.queue_name: str = self.relayer_register_config.queue_name
        self.callback: Callable

    # ------------------------------------------------------------------
    # Implemented functions
    # ------------------------------------------------------------------
    def register_event(self, event: bytes) -> None:
        """Register the event.

        Args:
            event (bytes): An event

        Raises:
            BridgeRelayerRegisterEventFailed
        """
        self.logger.info("Register message to RabbitMQ")
        self.logger.debug(f'event=${event}')

        try:
            self._send_message(
                routing_key=self.queue_name,
                message=event
            )
        except Exception as e:
            self.logger.error(
                f"Failed registering message to RabbitMQ! "
                f"event={event}, error={e}")
            raise BridgeRelayerRegisterEventFailed(e)

    def read_events(self, callback: Callable) -> None:
        """Consume event tasks.

        Args:
            callback (Callable): A callback function

        Raises:
            BridgeRelayerReadEventFailed
        """
        self.logger.info("Read messages from RabbitMQ")
        self.logger.debug(f'callback=${callback}')

        try:
            self._consume_message(
                routing_key=self.queue_name, 
                callback=callback
            )

        except Exception as e:
            self.logger.error(f"Failed Reading message from RabbitMQ! {e}")
            raise BridgeRelayerReadEventFailed(e)

    # ------------------------------------------------------------------
    # Internal functions
    # ------------------------------------------------------------------
    def _get_credentials(self) -> PlainCredentials:
        """Get the plain credentials.

        Returns:
            PlainCredentials: The plain credentials instance
        """
        return PlainCredentials(
            self.relayer_register_config.user,
            self.relayer_register_config.password,
        )

    def _get_connection_parameters(
        self,
        credentials: PlainCredentials
    ) -> ConnectionParameters:
        """Get the connection parameters.

        Args:
            credentials (PlainCredentials): A plain credentials instance

        Raises:
            BridgeRelayerRegisterCredentialError:

        Returns:
            ConnectionParameters: The connection parameters instance
        """
        self.logger.info('Set parameters connection to RabbitMQ')

        try:
            connection_parameters = ConnectionParameters(
                host=self.relayer_register_config.host,
                port=self.relayer_register_config.port,
                virtual_host="/",
                credentials=credentials,
            )
            self.logger.debug(f'connection_parameters=${connection_parameters}')
            return connection_parameters
        
        except TypeError as e:
            self.logger.error(
                f"Error setting parameters connection to RabbitMQ! Error={e}"
            )
            raise BridgeRelayerRegisterCredentialError(e)

    def _get_connection(
        self,
        params: ConnectionParameters
    ) -> BlockingConnection:
        """Get the blocking connection instance.

        Args:
            params (ConnectionParameters): A connection parameters instance

        Raises:
            BridgeRelayerRegisterConnectionError:

        Returns:
            BlockingConnection: The blocking connection instance
        """
        self.logger.info('Connect to RabbitMQ')

        try:
            blocking_connection = BlockingConnection(params)
            self.logger.debug(f'blocking_connection=${blocking_connection}')
            return blocking_connection

        except ValueError as e:
            self.logger.error(f"Error connecting to RabbitMQ! Error={e}")
            raise BridgeRelayerRegisterConnectionError(e)

    def _get_channel(self, connection: BlockingConnection) -> BlockingChannel:
        """Get the blockcing channel instance.

        Args:
            connection (BlockingConnection): A blocking connection instance

        Raises:
            BridgeRelayerRegisterChannelError:

        Returns:
            BlockingChannel: the blockcing channel instance.
        """
        self.logger.info('Create channel to RabbitMQ')

        try:
            blocking_connection = connection.channel()
            self.logger.debug(f'blocking_connection=${blocking_connection}')
            return blocking_connection

        except AttributeError as e:
            self.logger.error(f"Failed Creating channel to RabbitMQ! Error={e}")
            raise BridgeRelayerRegisterChannelError(e)

    def _declare_queue(
        self,
        channel: BlockingChannel,
        queue_name: str
    ) -> BlockingChannel:
        """Declare the queue name and get the blockcing channel instance.

        Args:
            channel (BlockingChannel): A blockcing channel instance
            queue_name (str): The queue name

        Raises:
            BridgeRelayerRegisterDeclareQueueError:

        Returns:
            BlockingChannel: The blockcing channel instance
        """
        self.logger.info('Declare durable queue to RabbitMQ')

        try:
            channel.queue_declare(queue=queue_name, durable=True)
            self.logger.debug(f'channel=${channel}')
            return channel

        except AttributeError as e:
            self.logger.error(
                f"Failed declaring durable queue to RabbitMQ! Error={e}")
            raise BridgeRelayerRegisterDeclareQueueError(e)

    def _connect(self) -> BlockingConnection:
        """Connect to RabbitMQ and get the blocking connection instance.

        Raises:
            BridgeRelayerRegisterConnectionError:

        Returns:
            BlockingConnection: A blocking connection instance
        """
        self.logger.info('Connect to RabbitMQ')

        credentials: PlainCredentials = self._get_credentials()
        self.logger.debug(f'credentials=${credentials}')
        
        parameters: ConnectionParameters = self._get_connection_parameters(
            credentials)
        self.logger.debug(f'parameters=${parameters}')

        try:
            blocking_connection = self._get_connection(parameters)
            self.logger.debug(f'blocking_connection=${blocking_connection}')
            return blocking_connection

        except AMQPConnectionError as e:
            self.logger.error(f"Failed connecting to RabbitMQ! Error={e}")
            raise BridgeRelayerRegisterConnectionError(e)

    def _send_message(
        self,
        routing_key: str,
        message: Union[str, bytes],
        exchange: str = "",
    ) -> None:
        """Send a message to RabbitMQ.

        Args:
            routing_key (str): The routing key name
            message (Union[str, bytes]): The message
            exchange (str, optional): The exchange name. Defaults to "".
        """
        self.logger.info('Send message to RabbitMQ')

        try:
            connection: BlockingConnection = self._connect()
            self.logger.debug(f'connection=${connection}')
            
            channel: BlockingChannel = self._get_channel(connection=connection)
            self.logger.debug(f'channel=${channel}')
            
            channel: BlockingChannel = self._declare_queue(
                channel=channel, queue_name=routing_key)
            self.logger.debug(f'channel=${channel}')

            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message,
                properties=BasicProperties(
                    delivery_mode=DeliveryMode.Persistent
                )
            )

            connection.close()
        except Exception as e:
            self.logger.error(f'Error Sending message to RabbitMQ! Error={e}')
            raise

    def _callback(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: Any
    ) -> None:
        """Handle the message consume from RabbitMQ.

        This method execute another callback set in the application layer.

        Args:
            channel (BlockingChannel): A blockcing channel instance
            method (Basic.Deliver): A Basic.Deliver instance
            properties (BasicProperties): A BasicProperties instance
            body (Any): The message body
        """
        self.logger.info('Handle the message consume from RabbitMQ')
        # Handle message body
        self.callback(body)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def _set_channel_qos(
        self,
        channel: BlockingChannel,
        prefetch_count: int = 1
    ) -> BlockingChannel:
        """Set the channel QoS.

        Args:
            channel (BlockingChannel): A blocking channel
            prefetch_count (int, optional): A prefetch count. Defaults to 1.

        Returns:
            BlockingChannel: _description_
        """
        self.logger.info('Set channel qos to RabbitMQ')
        channel.basic_qos(prefetch_count=prefetch_count)
        return channel


    def _consume_message(
        self,
        routing_key: str,
        callback: Callable,
        auto_ack: bool = False,
    ) -> None:
        """Consume event tasks.

        Args:
            routing_key (str): The routing key
            callback (Callable): A callback function
            auto_ack (bool, optional): Enable/disable auto acknowledge.
                Defaults to False.
        """
        self.logger.info('Receive message from RabbitMQ')

        try:
            connection: BlockingConnection = self._connect()
            channel: BlockingChannel = self._get_channel(connection=connection)
            channel = self._set_channel_qos(channel=channel)
            self.callback = callback

            channel.basic_consume(
                queue=routing_key,
                auto_ack=auto_ack,
                on_message_callback=self._callback
            )
            channel.start_consuming()

        except Exception as e:
            self.logger.error(f'Error Receiving message from RabbitMQ! Error={e}')
            raise

    def _set_queue_name(self, queue_name: str) -> None:
        """Set a queue name to register messages.

        Args:
            queue_name (str): A queue name
        """
        self.logger.info('Set queue name to RabbitMQ')
        self.queue_name = queue_name
