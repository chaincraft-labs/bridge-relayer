import logging
import pytest
from unittest.mock import MagicMock, patch
from pika import (
    BasicProperties,
    BlockingConnection,
    ConnectionParameters,
    PlainCredentials,
)
from pika.spec import Basic
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError

from src.relayer.domain.exception import (
    RelayerReadEventFailed,
    RelayerRegisterChannelError,
    RelayerRegisterConnectionError,
    RelayerRegisterCredentialError,
    RelayerRegisterDeclareQueueError,
    RelayerRegisterEventFailed
)
from src.relayer.domain.relayer import EventDTO
from src.relayer.domain.config import RelayerRegisterConfigDTO
from src.relayer.provider.relayer_register_pika import (
    RelayerRegisterEvent,
)
from src.utils.converter import to_bytes
from tests.conftest import DATA_TEST

# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(autouse=True)
def disable_logging():
    # Désactiver les logs pendant les tests
    logging.disable(logging.CRITICAL)
    yield
    # Réactiver les logs après les tests
    logging.disable(logging.NOTSET)

@pytest.fixture(scope="function")
def register_config():
    return RelayerRegisterConfigDTO(
        host="localhost",
        port=5672,
        user="guest",
        password="guest",
        queue_name="bridge.relayer.dev",
    )

@pytest.fixture(scope="function")
def provider(register_config):
    with patch(
        'src.relayer.provider.relayer_register_pika.get_register_config', 
        return_value=register_config
    ):
        provider = RelayerRegisterEvent()
        return provider

@pytest.fixture(scope="function")
def event_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    block_key = f"{event.blockNumber}-{event.transactionHash.hex()}-{event.logIndex}"
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args,  # type: ignore
        block_key=block_key
    )

# -----------------------------------------------------------------
# T E S T S
# -----------------------------------------------------------------
def test_relayer_register_event_init(register_config):
    """
        Test RelayerRegisterEvent init
    """
    with patch(
        'src.relayer.provider.relayer_register_pika.get_register_config', 
        return_value=register_config
    ):
        provider = RelayerRegisterEvent()
        assert isinstance(
            provider.relayer_register_config, RelayerRegisterConfigDTO)
        assert provider.queue_name == "bridge.relayer.dev"

def test_register_event_fail_with_exception(provider, event_dto):
    """
        Test register_event that raises BridgeRelayerRegisterEventFailed 
        exception on error while executing _send_message method
    """
    event_bytes = to_bytes(event_dto)
    provider._send_message = MagicMock(side_effect=Exception("fake error"))
    with pytest.raises(RelayerRegisterEventFailed) as e:
        provider.register_event(event=event_bytes)

    assert str(e.value.args[0]) == "fake error"

def test_register_event_send_message_with_success(provider, event_dto):
    """
        Test register_event that sends a message successfully 
        to the message queuing.
        Calls _send_message method
    """
    event_bytes = to_bytes(event_dto)
    provider._send_message = MagicMock()
    provider.register_event(event=event_bytes)

    provider._send_message.assert_called_with(
        routing_key=provider.queue_name,
        message=event_bytes
    )

def test_read_events_fail_with_exception(
    provider
):
    """
        Test read_events that raises BridgeRelayerReadEventFailed
        exception while reading message queuing provider
    """
    def callback():
        pass

    provider._consume_message = MagicMock(side_effect=Exception("fake error"))
    with pytest.raises(RelayerReadEventFailed) as e:
        provider.read_events(callback=callback)

    assert str(e.value.args[0]) == "fake error"

def test_read_events_read_message_with_success(
    provider
):
    """
        Test read_events that raises BridgeRelayerReadEventFailed
        exception while reading message queuing provider
    """
    def callback():
        pass

    provider._consume_message = MagicMock()
    provider.read_events(callback=callback)
    provider._consume_message.assert_called_with(
        routing_key=provider.queue_name,
        callback=callback
    )

def test_get_credentials(provider):
    """
        Test _get_credentials that returns a pika PlainCredentials instance
        user and password are set in .env.config.dev and .env.config.prod
    """
    credentials = provider._get_credentials()
    assert isinstance(credentials, PlainCredentials)
    assert credentials.username == 'guest'
    assert credentials.password == 'guest'

@patch('src.relayer.provider.relayer_register_pika.ConnectionParameters')
def test_get_connection_parameters_raise_exception(mock_pika, provider):
    """
        Test _get_connection_parameters that raises BridgeRelayerRegisterCredentialError
        on TypeError exception.
    """
    credentials = provider._get_credentials()
    mock_pika.side_effect = TypeError("fake error")    
    with pytest.raises(RelayerRegisterCredentialError) as e:
        provider._get_connection_parameters(credentials=credentials)

    assert str(e.value.args[0]) == "fake error"

def test_get_connection_parameters_with_success(provider):
    """
        Test _get_connection_parameters that returns a ConnectionParameters
        instance.
    """
    credentials = provider._get_credentials()
    connection_parameters = provider._get_connection_parameters(
        credentials=credentials
    )
    assert isinstance(connection_parameters, ConnectionParameters)
    assert connection_parameters.host == 'localhost'
    assert connection_parameters.port == 5672
    assert connection_parameters.virtual_host == '/'
    assert connection_parameters.credentials.username == 'guest'
    assert connection_parameters.credentials.password == 'guest'

@patch('src.relayer.provider.relayer_register_pika.BlockingConnection')
def test_get_connection_raise_exception(mock_pika, provider):
    """
        Test _get_connection that raises BridgeRelayerRegisterConnectionError
        on ValueError exception
    """
    credentials = provider._get_credentials()
    connection_parameters = provider._get_connection_parameters(
        credentials=credentials
    )
    mock_pika.side_effect = ValueError("fake value error")
    with pytest.raises(RelayerRegisterConnectionError) as e:
        provider._get_connection(params=connection_parameters)
    
    assert str(e.value.args[0]) == "fake value error"

@patch('src.relayer.provider.relayer_register_pika.BlockingConnection')
def test_get_connection_with_success(mock_pika, provider):
    """
        Test get_connection that returns a BlockingConnection instance
    """
    mock_connection = MagicMock(spec=BlockingConnection)
    mock_pika.return_value = mock_connection
    params = ConnectionParameters(host='localhost')  
    connection = provider._get_connection(params)
    mock_pika.assert_called_once_with(params)
    assert connection == mock_connection

def test_get_channel_raise_exception(provider):
    """
        Test _get_channel that raises BridgeRelayerRegisterChannelError
        on AttributeError exception
    """
    connection = MagicMock()
    connection.channel = MagicMock(side_effect=AttributeError("fake attr error"))
    with pytest.raises(RelayerRegisterChannelError) as e:
        provider._get_channel(connection=connection)

    assert str(e.value.args[0]) == "fake attr error"

def test_get_channel_with_success(provider):
    """
        Test _get_channel that returns BlockingChannel
    """
    channel_impl = MagicMock()
    connection = MagicMock()
    expected_blocking_connection = BlockingChannel(channel_impl, connection)
    connection.channel = MagicMock(return_value=expected_blocking_connection)
    
    blocking_connection = provider._get_channel(connection=connection)
    
    assert isinstance(blocking_connection, BlockingChannel)
    assert blocking_connection == connection.channel.return_value

def test_declare_queue_raise_exception(provider):
    """
        Test _declare_queue that raises BridgeRelayerRegisterChannelError
        on AttributeError exception
    """
    channel = MagicMock()
    channel.queue_declare = MagicMock(side_effect=AttributeError("fake attr error"))
    with pytest.raises(RelayerRegisterDeclareQueueError) as e:
        provider._declare_queue(channel, "a.queue.name")

    assert str(e.value.args[0]) == "fake attr error"

def test_declare_queue_with_success(provider):
    """
        Test _declare_queue that returns BlockingChannel
    """
    channel_impl = MagicMock()
    connection = MagicMock()
    channel = BlockingChannel(channel_impl, connection)
    channel.queue_declare = MagicMock(return_value=channel)
    
    result_channel = provider._declare_queue(channel, "a.queue.name")
    
    assert isinstance(result_channel, BlockingChannel)
    assert result_channel == channel.queue_declare.return_value

def test_connect_raise_exception(provider):
    """
        Test _connect that raises BridgeRelayerRegisterConnectionError
        on AttributeError exception
    """
    provider._get_credentials = MagicMock()
    provider._get_connection_parameters = MagicMock()
    provider._get_connection = MagicMock(side_effect=AMQPConnectionError("fake error"))
    
    with pytest.raises(RelayerRegisterConnectionError) as e:
        provider._connect()

    assert str(e.value.args[0]) == "fake error"

def test_connect_with_success(provider):
    """
        Test _connect that returns BlockingConnection
    """
    connection = MagicMock()
    provider._get_credentials = MagicMock()
    provider._get_connection_parameters = MagicMock()
    provider._get_connection = MagicMock(return_value=connection)
    
    result_connection = provider._connect()
    assert result_connection == provider._get_connection.return_value

def test_send_message_raise_exception(provider):
    """
        Test _send_message that raises any exception
    """
    channel = MagicMock()
    channel.basic_publish = MagicMock(side_effect=Exception("fake error"))

    provider._connect = MagicMock()
    provider._get_channel = MagicMock()
    provider._declare_queue = MagicMock(return_value=channel)
    
    with pytest.raises(Exception) as e:
        provider._send_message(
            routing_key="a.fake.queue",
            message='a fake message',
        )
    assert str(e.value.args[0]) == "fake error"


def test_send_message_with_success(provider):
    """
        Test _send_message that raises any exception
    """
    channel = MagicMock()
    channel.basic_publish = MagicMock()

    provider._connect = MagicMock()
    provider._get_channel = MagicMock()
    provider._declare_queue = MagicMock(return_value=channel)
    
    provider._send_message(
        routing_key="a.fake.queue",
        message='a fake message',
    )

def test_send_message_success(provider):
    """
        Test _send_message that send a message to RabbitMQ and succeed
    """
    provider._connect = MagicMock()
    provider._get_channel = MagicMock()
    mock_channel = MagicMock(spec=BlockingChannel)
    provider._declare_queue = MagicMock(return_value=mock_channel)

    routing_key = 'test_queue'
    message = 'test_message'
    exchange = 'test_exchange'
    provider._send_message(routing_key, message, exchange)
    mock_channel.basic_publish.assert_called_once()

def test_callback_execute_success(provider, event_dto):
    """
        Test _callback that execute callback and acknowledge message 
    """
    provider.callback = MagicMock()
    mock_channel = MagicMock(spec=BlockingChannel)
    mock_channel.basic_ack = MagicMock(spec=BlockingChannel)

    mock_method = MagicMock(spec=Basic.Deliver)
    mock_method.delivery_tag = MagicMock()
    mock_properties = MagicMock(spec=BasicProperties)    
    event = to_bytes(event_dto)

    provider._callback(
        channel=mock_channel,
        method=mock_method,
        properties=mock_properties,
        body=event
    )

    provider.callback.assert_called()
    mock_channel.basic_ack.assert_called()


def test_set_channel_qos_with_success(provider):
    """
        Test _set_channel_qos that returns a channel
    """
    mock_channel = MagicMock(spec=BlockingChannel)
    mock_channel.basic_qos = MagicMock()

    provider._set_channel_qos(channel=mock_channel)

    mock_channel.basic_qos.assert_called_with(prefetch_count=1)


def test_consume_message_raise_exception(provider):
    """
        Test _consume_message that raises an exception
    """
    def callback():
        pass

    provider._connect = MagicMock()
    mock_channel = MagicMock(spec=BlockingChannel)
    provider._get_channel = MagicMock(return_value=mock_channel)
    provider._set_channel_qos = MagicMock(return_value=mock_channel)
    mock_channel.basic_consume = MagicMock(side_effect=Exception("fake error"))

    with pytest.raises(Exception) as e:
        provider._consume_message(
            routing_key="fake.queue.name",
            callback=callback
        )
    assert str(e.value.args[0]) == "fake error"

def test_consume_message_with_success(provider):
    """
        Test _consume_message that consume message with success
    """
    def callback():
        pass

    provider._connect = MagicMock()
    mock_channel = MagicMock(spec=BlockingChannel)
    provider._get_channel = MagicMock(return_value=mock_channel)
    provider._set_channel_qos = MagicMock(return_value=mock_channel)
    mock_channel.basic_consume = MagicMock()
    
    provider._callback = MagicMock()

    provider._consume_message(
        routing_key="fake.queue.name",
        callback=callback
    )
    mock_channel.basic_consume.assert_called_with(
        queue="fake.queue.name",
        auto_ack=False,
        on_message_callback=provider._callback
    )

def test_set_queue_name_with_success(provider):
    """
        Test _set_queue_name that set a queue name
    """
    provider._set_queue_name(queue_name="fake.queue.name")
    assert provider.queue_name == "fake.queue.name"
