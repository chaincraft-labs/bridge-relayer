
from datetime import datetime, timezone
import logging
import pathlib
from unittest.mock import AsyncMock

import pytest
from src.relayer.domain.exception import (
    RepositoryErrorOnGet, 
    RepositoryErrorOnSave
)
from src.relayer.domain.event_db import BridgeTaskDTO, EventDTO, EventDataDTO
from src.relayer.provider.mock_relayer_repository_leveldb import (
    RelayerRepositoryProvider
)
from src.relayer.application.repository import Repository

from tests.conftest import EVENT_DATA_SAMPLE as event_data

PATH_APP = 'src.relayer.application.consume_events'
TEST_ROOT_PATH = pathlib.Path(__file__).parent.parent.parent
TEST_REPOSITORY_NAME = 'test.db'
DB_TEST = str(TEST_ROOT_PATH / TEST_REPOSITORY_NAME)


# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(autouse=True)
def disable_logging():
    # Disable logging during tests
    logging.disable(logging.CRITICAL)
    yield
    # Enable loggin after tests
    logging.disable(logging.NOTSET)

@pytest.fixture(scope="function")
def repository_provider():
    return RelayerRepositoryProvider()

@pytest.fixture(scope="function")
def repository(repository_provider):
    return Repository(repository_provider)

@pytest.fixture
def example_event():
    """Create an example event."""
    return EventDTO(
        chain_id=1,
        event_name=event_data["event"],
        block_number=event_data["blockNumber"],
        tx_hash=event_data["transactionHash"].hex(),
        log_index=event_data["logIndex"],
        block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810),
        handled=None,
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
    )

@pytest.fixture
def example_bridge_task():
    """Create an example bridge task."""
    return BridgeTaskDTO(
        chain_id=1,
        block_number=event_data["blockNumber"],
        tx_hash=event_data["transactionHash"].hex(),
        log_index=event_data["logIndex"],
        operation_hash="0x123456789",
        event_name="EventName",
        status="OperationCreated",
        datetime=datetime.now(timezone.utc),
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------   

# -------------------------------------------------------
# Test init
# -------------------------------------------------------
def test_init_method(repository):
    """Test init that create a dict to init the struct for events"""
    assert type(repository.provider) is RelayerRepositoryProvider

# -------------------------------------------------------
# Test setup
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_setup_method(repository):
    """Test setup."""
    repository.provider.setup = AsyncMock()
    await repository.setup(repository_name=DB_TEST)
    repository.provider.setup.assert_called_once_with(name=DB_TEST)

# -------------------------------------------------------
# Test get_last_scanned_block
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_last_scanned_block(repository):
    """Test get last_scanned_block."""
    repository.provider.get_last_scanned_block = AsyncMock()
    repository.provider.get_last_scanned_block.return_value = 123
    last_scanned_block = await repository.get_last_scanned_block(chain_id=1)
    assert last_scanned_block == 123

@pytest.mark.asyncio
async def test_get_last_scanned_block_return_zero_with_exception(repository):
    """Test get last_scanned_block that returns zero with exception."""
    repository.provider.get_last_scanned_block = AsyncMock()
    repository.provider.get_last_scanned_block.side_effect = RepositoryErrorOnGet("Error")
    last_scanned_block = await repository.get_last_scanned_block(chain_id=1)
    assert last_scanned_block == 0

# -------------------------------------------------------
# Test set_last_scanned_block
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_set_last_scanned_block(repository):
    """Test set last scanned block."""
    repository.provider.set_last_scanned_block = AsyncMock()
    await repository.set_last_scanned_block(chain_id=1, block_numer=123)
    repository.provider.set_last_scanned_block.assert_called_once_with(
        chain_id=1, 
        block_numer=123
    )

@pytest.mark.asyncio
async def test_set_last_scanned_block_raise_exception(repository):
    """Test set last scanned block that raises RepositoryErrorOnSave."""
    repository.provider.set_last_scanned_block = AsyncMock()
    repository.provider.set_last_scanned_block.side_effect = RepositoryErrorOnSave("Error")
    with pytest.raises(RepositoryErrorOnSave, match="Error"):
        await repository.set_last_scanned_block(chain_id=1, block_numer=123)
    
# -------------------------------------------------------
# Test set_event_as_registered
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_set_event_as_registered(repository, example_event):
    """Test set event as registered."""
    repository.provider.save_event = AsyncMock()
    await repository.set_event_as_registered(event=example_event)
    repository.provider.save_event.assert_called_once_with(event=example_event)

@pytest.mark.asyncio
async def test_set_event_as_registered_raise_Exception(repository, example_event):
    """Test set event as registered that raises RepositoryErrorOnSave."""
    repository.provider.save_event = AsyncMock()
    repository.provider.save_event.side_effect = RepositoryErrorOnSave("Error")
    with pytest.raises(RepositoryErrorOnSave, match="Error"):
        await repository.set_event_as_registered(event=example_event)
# -------------------------------------------------------
# Test get_event
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_event(repository, example_event):
    """Test get event."""
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.return_value = example_event
    event = await repository.get_event(id=example_event.as_key())
    assert event == example_event

@pytest.mark.asyncio
async def test_get_event_raise_exception(repository, example_event):
    """Test get event that raises RepositoryErrorOnGet."""
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.side_effect = RepositoryErrorOnGet("Error")
    with pytest.raises(RepositoryErrorOnGet, match="Error"):
        await repository.get_event(id=example_event.as_key())

# -------------------------------------------------------
# Test is_event_stored
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_is_event_stored_return_true(repository, example_event):
    """Test is event stored return true."""
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.return_value = example_event
    is_stored = await repository.is_event_stored(example_event)
    assert is_stored

@pytest.mark.asyncio
async def test_is_event_stored_return_false(repository, example_event):
    """Test is event stored return false. 
    If event does not exist in the repository it raises RepositoryErrorOnGet.
    """
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.side_effect = RepositoryErrorOnGet("Error")
    is_stored = await repository.is_event_stored(example_event)
    assert is_stored is False
# -------------------------------------------------------
# Test is_event_registered
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_is_event_registered_return_true(repository, example_event):
    """Test is event registered return true."""
    example_event.handled = "registered"
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.return_value = example_event
    is_registered = await repository.is_event_registered(example_event)
    assert is_registered

@pytest.mark.asyncio
async def test_is_event_registered_return_false(repository, example_event):
    """Test is event registered return false."""
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.return_value = example_event
    is_registered = await repository.is_event_registered(example_event)
    assert is_registered is False

@pytest.mark.asyncio
async def test_is_event_registered_return_false_with_exception(repository, example_event):
    """Test is event registered return false.
    If event does not exist in the repository it raises RepositoryErrorOnGet.
    """
    repository.provider.get_event = AsyncMock()
    repository.provider.get_event.side_effect = RepositoryErrorOnGet("Error")
    is_registered = await repository.is_event_registered(example_event)
    assert is_registered is False
# -------------------------------------------------------
# Test store_event
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_store_event(repository, example_event):
    """Test store event."""
    repository.is_event_stored = AsyncMock()
    repository.is_event_stored.return_value = False
    repository.provider.save_event = AsyncMock()

    result = await repository.store_event(event=example_event)
    repository.provider.save_event.assert_called_once_with(event=example_event)
    assert result

@pytest.mark.asyncio
async def test_store_event_does_not_save_when_already_exist(
    repository, 
    example_event
):
    """Test store event."""
    repository.is_event_stored = AsyncMock()
    repository.is_event_stored.return_value = True
    repository.provider.save_event = AsyncMock()
    
    result = await repository.store_event(event=example_event)
    repository.provider.save_event.assert_not_called()
    assert not result
# -------------------------------------------------------
# Test get_bridge_task
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_bridge_task(repository, example_bridge_task):
    """Test get bridge task."""
    repository.provider.get_bridge_task = AsyncMock()
    repository.provider.get_bridge_task.return_value = example_bridge_task
    bridge_task = await repository.get_bridge_task(id=example_bridge_task.as_key())
    assert bridge_task == example_bridge_task

@pytest.mark.asyncio
async def test_get_bridge_task_raise_Exception(repository, example_bridge_task):
    """Test get bridge task that raises RepositoryErrorOnGet."""
    repository.provider.get_bridge_task = AsyncMock()
    repository.provider.get_bridge_task.side_effect = RepositoryErrorOnGet("Error")
    with pytest.raises(RepositoryErrorOnGet, match="Error"):
        await repository.get_bridge_task(id=example_bridge_task.as_key())
    
# -------------------------------------------------------
# Test get_bridge_tasks
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_bridge_tasks(repository, example_bridge_task):
    """Test get bridge_tasks."""
    repository.provider.get_bridge_tasks = AsyncMock()
    repository.provider.get_bridge_tasks.return_value = [example_bridge_task]
    bridge_tasks = await repository.get_bridge_tasks()
    repository.provider.get_bridge_tasks.assert_called_once()
    assert bridge_tasks == [example_bridge_task]

@pytest.mark.asyncio
async def test_get_bridge_tasks_raise_exception(repository, example_bridge_task):
    """Test get bridge_tasks that raises exception."""
    repository.provider.get_bridge_tasks = AsyncMock()
    repository.provider.get_bridge_tasks.side_effect = RepositoryErrorOnGet("Error")
    with pytest.raises(RepositoryErrorOnGet, match="Error"):
        await repository.get_bridge_tasks()
# -------------------------------------------------------
# Test save_event
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_save_event(repository, example_event):
    """Test save event."""
    repository.provider.save_event = AsyncMock()
    await repository.save_event(event=example_event)
    repository.provider.save_event.assert_called_once_with(event=example_event)

@pytest.mark.asyncio
async def test_save_event_raise_Exception(repository, example_event):
    """Test save event that raises RepositoryErrorOnSave."""
    repository.provider.save_event = AsyncMock()
    repository.provider.save_event.side_effect = RepositoryErrorOnSave("Error")
    with pytest.raises(RepositoryErrorOnSave, match="Error"):
        await repository.save_event(event=example_event)

# -------------------------------------------------------
# Test save_bridge_task
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_save_bridge_task(repository, example_bridge_task):
    """Test save bridge task."""
    repository.provider.save_bridge_task = AsyncMock()
    await repository.save_bridge_task(bridge_task=example_bridge_task)
    repository.provider.save_bridge_task.assert_called_once_with(
        bridge_task=example_bridge_task
    )

@pytest.mark.asyncio
async def test_save_bridge_task_raise_exception(repository, example_bridge_task):
    """Test save bridge task that raises RepositoryErrorOnSave."""
    repository.provider.save_bridge_task = AsyncMock()
    repository.provider.save_bridge_task.side_effect = RepositoryErrorOnSave("Error")
    with pytest.raises(RepositoryErrorOnSave, match="Error"):
        await repository.save_bridge_task(bridge_task=example_bridge_task)