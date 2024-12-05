import asyncio
from datetime import datetime
import signal
import aio_pika
from aiormq import AMQPConnectionError
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.relayer.domain.exception import (
    RelayerReadEventFailed, 
    RelayerRegisterEventFailed
)
from src.relayer.domain.event_db import EventDTO, EventDataDTO
from src.relayer.provider.relayer_register_aio_pika import RelayerRegisterEvent
from src.relayer.domain.config import RelayerRegisterConfigDTO
from src.utils.converter import to_bytes

from tests.conftest import EVENT_DATA_SAMPLE as event_data

APP_PATH = "src.relayer.provider.relayer_register_aio_pika"
# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(scope="function")
def register_config():
    return RelayerRegisterConfigDTO(
        host="fake-localhost",
        port=9999,
        user="fake-guest",
        password="fake-guest",
        queue_name="bridge.relayer.test",
    )

@pytest.fixture
def example_event_dto_as_bytes():
    """Create an example event."""
    return to_bytes(EventDTO(
        chain_id=1,
        event_name=event_data["event"],
        block_number=event_data["blockNumber"],
        tx_hash=event_data["transactionHash"].hex(),
        log_index=event_data["logIndex"],
        block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810),
        data=EventDataDTO(
            from_=event_data.args.params["from"],
            to=event_data.args.params["to"],
            chain_id_from=event_data.args.params["chainIdFrom"],
            chain_id_to=event_data.args.params["chainIdTo"],
            token_name=event_data.args.params["tokenName"],
            amount=event_data.args.params["amount"],
            nonce=event_data.args.params["nonce"],
            signature_str=event_data.args.params["signature"].hex(),
            signature_bytes=event_data.args.params["signature"],
            operation_hash_str=event_data.args["operationHash"].hex(),
            operation_hash_bytes=event_data.args["operationHash"],
            block_step=event_data.args["blockStep"],
        ),
    ))

@pytest.fixture(scope="function")
def provider(register_config):
    provider = RelayerRegisterEvent()
    mock_config = MagicMock()
    provider.config = mock_config
    provider.relayer_register_config = register_config
    provider.queue_name = register_config.queue_name
    return provider

# -----------------------------------------------------------------
# T E S T S
# -----------------------------------------------------------------
def test_relayer_register_event_init(provider):
    """
        Test RelayerRegisterEvent init
    """
    assert provider.queue_name == "bridge.relayer.test"
    assert provider.tasks == 0

# -----------------------------------------------------------------
# Private methods
# -----------------------------------------------------------------

# -------------------- _connection -------------------------------------
@pytest.mark.asyncio
@patch(f'{APP_PATH}.aio_pika.connect')
async def test_connection(mock_connect, provider):
    mock_connect.return_value = AsyncMock()
    connection = await provider._connection()
    expected_url = (
        f"amqp://{provider.relayer_register_config.user}:"
        f"{provider.relayer_register_config.password}@"
        f"{provider.relayer_register_config.host}:"
        f"{provider.relayer_register_config.port}/"
    )
    mock_connect.assert_awaited_once_with(expected_url)
    assert connection == mock_connect.return_value
# -------------------- _send_message -----------------------------------
@pytest.mark.asyncio
@patch(f'{APP_PATH}.aio_pika.connect')
async def test_send_message(mock_connect, provider):
    """
        Test _send_message
    """
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()
    mock_exchange = AsyncMock()
    mock_connect.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_queue.return_value = mock_queue
    mock_channel.default_exchange = mock_exchange
    message = b'a fake message'

    # act
    await provider._send_message(message=message)

    # assert
    mock_connect.assert_awaited_once()
    # Check that the channel and the queue have been declared
    mock_connection.channel.assert_awaited_once()
    mock_channel.declare_queue.assert_awaited_once_with(provider.queue_name, durable=True)
    # Check that the message has been published in the exchange
    mock_exchange.publish.assert_awaited_once()
    # Check the content of the message sent
    assert mock_exchange.publish.call_args[0][0].body == message  # conversion en bytes


@pytest.mark.asyncio
@patch(f'{APP_PATH}.aio_pika.connect')
async def test_send_message_raise_exception(mock_connect, provider):
    """
        Test _send_message that raises any exception
    """
    mock_connect.side_effect = AMQPConnectionError('Error')
    message = b'a fake message'

    with pytest.raises(AMQPConnectionError, match="Error"):
        await provider._send_message(message=message)


# -------------------- _consume_message -------------------------------------
@pytest.mark.asyncio
@patch(f'{APP_PATH}.aio_pika.connect')
async def test_consume_message(mock_connect, provider):
    """
        Test _consume_message that raises an exception
    """
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()

    mock_connect.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_queue.return_value = mock_queue

    callback_mock = AsyncMock()
    provider.callback = callback_mock

    consume_task = asyncio.create_task(provider._consume_message())

    try:
        # Use asyncio.wait_for to limit the execution time of the task
        await asyncio.wait_for(consume_task, timeout=0.1)
    except asyncio.TimeoutError:
        # This is normal because we have an infinite Future in _consume_message
        pass

    # assert
    # Check that the connection and the channel have been called
    mock_connect.assert_awaited_once()
    # Check that the channel has been opened
    mock_connection.channel.assert_awaited_once()
    # Check that the queue has been declared
    mock_channel.declare_queue.assert_awaited_once_with(provider.queue_name, durable=True)
    # Check that the callback has been called
    mock_queue.consume.assert_awaited_once_with(provider.callback)

    consume_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consume_task

@pytest.mark.asyncio
@patch(f'{APP_PATH}.aio_pika.connect')
async def test_consume_message_raise_exception(mock_connect, provider):
    """
        Test _consume_message that raises an exception
    """
    mock_connect.side_effect = Exception('Error')
    with pytest.raises(Exception, match="Error"):
        await provider._consume_message()

# -------------------- stop -------------------------------------
@pytest.mark.asyncio
async def test_stop(provider):
    # Simulate a stop event like an asyncio.Event() 
    provider.stop_event = asyncio.Event()
    # Check thet the event is not set
    assert not provider.stop_event.is_set()
    # act
    provider.stop()

    assert provider.stop_event.is_set()
# -------------------- callback -------------------------------------

@pytest.mark.asyncio
async def test_callback(provider):
    """
        Test callback
    """
    # Simulate an initial task
    provider.tasks = 0
    # Create a simulated incoming message
    message_mock = MagicMock(spec=aio_pika.IncomingMessage)
    message_mock.body = b"test_message"
    
    # Simulate the context of the process()    
    message_mock.process.__aenter__.return_value = None
    message_mock.process.__aexit__.return_value = None

    # Simulate the _callback method
    provider._callback = AsyncMock()

    # act
    await provider.callback(message_mock)
    
    # Check that the tasks are incremented and decremented
    assert provider.tasks == 0
    provider._callback.assert_awaited_once_with(b"test_message")

@pytest.mark.asyncio
async def test_callback_returns_none_onxception(provider):
    """
        Test callback that returns None on exception
    """
    # Simulate an initial task
    provider.tasks = 0
    # Create a simulated incoming message
    message_mock = MagicMock(spec=aio_pika.IncomingMessage)
    message_mock.body = b"test_message"
    
    # Simulate the context of the process()    
    message_mock.process.__aenter__.return_value = None
    message_mock.process.__aexit__.return_value = None

    # Simulate the _callback method
    provider._callback = AsyncMock(side_effect=Exception('Error'))

    # act
    assert await provider.callback(message_mock) is None

# -------------------- shutdown ------------------------------------
@pytest.mark.asyncio
async def test_shutdown(provider, mocker):
    """Test the shutdown method."""
    loop = asyncio.get_event_loop()

    # Create a dummy task to test shutdown
    async def dummy_task():
        await asyncio.sleep(5)

    # Schedule the dummy task
    task = loop.create_task(dummy_task())

    # Ensure the task is running
    await asyncio.sleep(0.5)  # Give it a moment to start

    # Mock the print function to capture output
    mock_print = mocker.patch('builtins.print')

    # Call the shutdown method
    await provider.shutdown(loop, signal.SIGINT)

    # Check that the task was cancelled
    assert task.done()  # The task should be marked as done
    assert task.cancelled()  # The task should be cancelled

    # Check that the print function was called with expected messages
    assert mock_print.call_count >= 2  # At least two print calls should happen
    assert any("Cancelling" in call[0][0] for call in mock_print.call_args_list)
    assert any("Received exit signal" in call[0][0] for call in mock_print.call_args_list)


# -------------------------------------------------------------------
# Public methods
# -------------------------------------------------------------------

# ---------------- register_event ----------------------------------
@pytest.mark.asyncio
async def test_register_event(provider, example_event_dto_as_bytes):
    """
        Test register_event
    """
    provider._send_message = AsyncMock()

    # act
    await provider.register_event(event=example_event_dto_as_bytes)
    
    provider._send_message.assert_awaited_once_with(
        message=example_event_dto_as_bytes
    )


@pytest.mark.asyncio
async def test_register_event_raise_exception(
    provider, 
    example_event_dto_as_bytes
):
    """
        Test register_event
    """
    provider._send_message = AsyncMock(side_effect=Exception('Error'))

    # act
    with pytest.raises(RelayerRegisterEventFailed):
        await provider.register_event(event=example_event_dto_as_bytes)

# ---------------- read_events -------------------------------------
@pytest.mark.asyncio
async def test_read_events(provider):
    """
        Test read_events
    """
    mock_callback = AsyncMock()
    provider._consume_message = AsyncMock()

    # act
    await provider.read_events(callback=mock_callback)
    
    provider._consume_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_events_raise_exception(provider):
    """
        Test read_events
    """
    mock_callback = AsyncMock()
    provider._consume_message = AsyncMock(side_effect=Exception('Error'))

    # act
    with pytest.raises(RelayerReadEventFailed):
        await provider.read_events(callback=mock_callback)
