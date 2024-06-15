"""
Provider that aims to manage and register events.

Events are sent to RabbitMQ, a messaging and streaming broker.
https://www.rabbitmq.com/
"""
import logging
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
from src.relayer.config import get_register_config
from src.relayer.domain.exception import (
    BridgeRelayerRegisterChannelError,
    BridgeRelayerRegisterConnectionError,
    BridgeRelayerRegisterCredentialError,
    BridgeRelayerRegisterDeclareQueueError,
    BridgeRelayerRegisterEventFailed,
    BridgeRelayerReadEventFailed,
)


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER: logging.Logger = logging.getLogger(__name__)


class RelayerRegisterEvent(IRelayerRegister):
    """Relayer register provider
    
    RabbitMQ is used as messaging and streaming broker. 
    """

    def __init__(self, debug: bool = False) -> None:
        """Init RelayerRegisterEvent.

        Args:
            debug (bool, optional): Enable/disable logging. Defaults to False.
        """
        self._debug = debug
        self.relayer_register_config = get_register_config()
        self.queue_name: str = self.relayer_register_config.queue_name
        self.callback: Callable
        
        # Set Logging
        self._set_logging(debug)
            
    @property
    def debug(self) -> bool:
        """Get the debug value.

        Returns:
            bool: The debug value
        """
        return self._debug
    
    @debug.setter
    def debug(self, value: bool) -> None:
        """Set the debug value and enable disable the logging.

        Args:
            value (bool): The debug value
        """
        print(f"debug : {value}")
        self._set_logging(value)
    
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
        LOGGER.info(f"Registering message to RabbitMQ with event: {event}")
        
        try:
            routing_key: str = self.queue_name
            message: bytes = event
            
            self._send_message(
                routing_key=routing_key, 
                message=message
            )
        except Exception as e:
            LOGGER.critical(
                f"Failed Registering message to RabbitMQ! "
                f"event: {event}, error: {e}")
            BridgeRelayerRegisterEventFailed(e)
    
    def read_events(self, callback: Callable) -> None:
        """Consume event tasks.

        Args:
            callback (Callable): A callback function
            
        Raises:
            BridgeRelayerReadEventFailed
        """
        LOGGER.info("Reading messages from RabbitMQ ...")
                
        try:
            routing_key: str = self.queue_name
            self._consume_message(routing_key=routing_key, callback=callback)
        
        except Exception as e:
            LOGGER.critical(f"Failed Reading message from RabbitMQ! {e}")
            BridgeRelayerReadEventFailed(e)

    # ------------------------------------------------------------------
    # Internal functions
    # ------------------------------------------------------------------
    def _set_logging(self, value: bool) -> None:
        """Enable or disable the logging.

        Args:
            value (bool): A value indicating the logging on/off
        """
        if value is True:
            logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
            LOGGER.propagate = True
        else:
            LOGGER.propagate = False
    
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
        LOGGER.info('Setting parameters connection to RabbitMQ ...')
        
        try:
            return ConnectionParameters(
                host=self.relayer_register_config.host,
                port=self.relayer_register_config.port,
                virtual_host="/",
                credentials=credentials,
            )
        except TypeError as e:
            LOGGER.critical(
                f"Error setting parameters connection to RabbitMQ! error : {e}"
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
        LOGGER.info('Connecting to RabbitMQ ...')
        
        try:
            return BlockingConnection(params)

        
        except ValueError as e:
            LOGGER.critical(f"Error connectiing to RabbitMQ! error : {e}")
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
        LOGGER.info('Creating channel to RabbitMQ ...')
        
        try:
            return connection.channel()
        
        except AttributeError as e:
            LOGGER.critical(f"Failed Creating channel to RabbitMQ! error : {e}")
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
        LOGGER.info('Declaring durable queue to RabbitMQ ...')
        
        try:
            channel.queue_declare(queue=queue_name, durable=True)
            return channel
            
        except AttributeError as e:
            LOGGER.critical(
                f"Failed declaring durable queue to RabbitMQ! error {e}")
            raise BridgeRelayerRegisterDeclareQueueError(e)

    def _connect(self) -> BlockingConnection:
        """Connect to RabbitMQ and get the blocking connection instance.

        Raises:
            BridgeRelayerRegisterConnectionError:

        Returns:
            BlockingConnection: A blocking connection instance
        """
        LOGGER.info('Connecting to RabbitMQ ...')
        
        credentials: PlainCredentials = self._get_credentials()
        parameters: ConnectionParameters = self._get_connection_parameters(
            credentials)
        
        try:
            return self._get_connection(parameters)
            
        except AMQPConnectionError as e:
            LOGGER.critical(f"Failed connecting to RabbitMQ! error : {e}")
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
        LOGGER.info('Sending message to RabbitMQ ...')

        try:
            connection: BlockingConnection = self._connect()
            channel: BlockingChannel = self._get_channel(connection=connection)
            channel: BlockingChannel = self._declare_queue(
                channel=channel, queue_name=routing_key)

            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message,
                properties=BasicProperties(
                    delivery_mode = DeliveryMode.Persistent
                )
            )
            
            connection.close()
        except Exception as e:
            LOGGER.critical('Error Sending message to RabbitMQ!')
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
        # Handle message body
        self.callback(body)
        channel.basic_ack(delivery_tag = method.delivery_tag)

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
        channel.basic_qos(prefetch_count=prefetch_count)
        return  channel


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
        LOGGER.info('Receiving message from RabbitMQ ...')
        
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
            LOGGER.critical('Error Receiving message from RabbitMQ!')
            raise
   
    def _set_queue_name(self, queue_name: str) -> None:
        """Set a queue name to register messages.

        Args:
            queue_name (str): A queue name
        """
        self.queue_name = queue_name
 