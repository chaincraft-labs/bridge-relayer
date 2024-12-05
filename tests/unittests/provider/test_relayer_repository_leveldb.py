import asyncio
from datetime import datetime, timezone
import shutil
import pytest
from unittest.mock import patch
import pathlib

from src.relayer.domain.exception import (
    RepositoryDatabaseNotProvided, 
    RepositoryErrorOnDelete, 
    RepositoryErrorOnGet, 
    RepositoryErrorOnSave, 
)
from src.relayer.domain.event_db import (
    BridgeTaskDTO, EventDataDTO, EventDTO
)
from src.relayer.provider.relayer_repository_leveldb import RelayerRepositoryProvider
from tests.conftest import EVENT_DATA_SAMPLE as event_data

PATH = "src.relayer.provider.relayer_event_storage_leveldb"
TEST_ROOT_PATH = pathlib.Path(__file__).parent.parent.parent
DB_TEST = str(TEST_ROOT_PATH / 'test.db')

@pytest.fixture
def mock_db():
    """Mock for the plyvel.DB object."""
    with patch('plyvel.DB') as mock:
        yield mock


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


@pytest.fixture
def repository():
    """Fixture to setup and teardown the database."""
    repository = RelayerRepositoryProvider()
    asyncio.run(repository.setup(name=DB_TEST))

    yield repository
    
    # Delete DB
    repository.db.close()
    shutil.rmtree(DB_TEST)


# -------------------------------------------------
# Init Database
# -------------------------------------------------
@pytest.mark.asyncio
async def test_setup():
    """Test that the database setup works."""
    repository = RelayerRepositoryProvider()
    await repository.setup(name=DB_TEST)
    assert repository.db is not None
    
    repository.db.close()
    shutil.rmtree(DB_TEST)

@pytest.mark.parametrize("dbname", [None, ""])
@pytest.mark.asyncio
async def test_setup_database_that_raise_exception(dbname):
    """Test setup database.
    Raise an exception if the database name is not set
    """
    repository = RelayerRepositoryProvider()
    with pytest.raises(RepositoryDatabaseNotProvided):
        await repository.setup(dbname)


@pytest.mark.asyncio
async def test_setup_database_more_than_once(mock_db):
    """Test setup database more than once.

    repo.db is already set so no new DB is created
    """
    repository = RelayerRepositoryProvider()
    status_before = repository.db
    repository.db = mock_db.return_value
    status_after = repository.db
    assert status_before is None
    assert status_after is not None

    await repository.setup(name="test_db")
    await repository.setup(name="test_db")
    assert mock_db.call_count == 0

# ------------------------------------------------------------------------------
# Internal : Event
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_save_event_raise_exception(
    example_event: EventDTO
):
    """Test save event and raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception
    
    with pytest.raises(RepositoryErrorOnSave):
        await repository.save_event(example_event)

@pytest.mark.asyncio
async def test_save_and_get_event(
    repository,
    example_event: EventDTO
):
    """Test save and get event."""
    await repository.save_event(example_event)
    event = await repository.get_event(id=example_event.as_key())

    assert event.chain_id == example_event.chain_id
    assert event.block_number == example_event.block_number
    assert event.tx_hash == example_event.tx_hash


@pytest.mark.asyncio
async def test_get_event_raise_exception(
    example_event: EventDTO
):
    """Test get event raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnGet):
        await repository.get_event(id=example_event.as_key())

@pytest.mark.asyncio
async def test_get_events(
    repository, 
    example_event: EventDTO
):
    """Test get event."""
    for i in range(10):
        example_event.block_number = i
        example_event.tx_hash = i
        example_event.log_index = i
        await repository.save_event(example_event)

    events = await repository.get_events()

    assert len(events) == 10
    assert events[0].chain_id == 1
    assert events[0].block_number == 0
    assert events[0].tx_hash == 0
    assert events[0].log_index == 0

    assert events[-1].chain_id == 1
    assert events[-1].block_number == 9
    assert events[-1].tx_hash == 9
    assert events[-1].log_index == 9

@pytest.mark.asyncio
async def test_get_events_with_exception():
    """Test get events raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnGet):
        await repository.get_events()

@pytest.mark.asyncio
async def test_delete_event(
    repository,
    example_event: EventDTO
):
    """Test delete event."""
    for i in range(10):
        example_event.block_number = i
        await repository.save_event(example_event)
        
    await repository.delete_event(id=example_event.as_key())

    events = await repository.get_events()
    assert len(events) == 9

@pytest.mark.asyncio
async def test_delete_raise_exception(
    repository,
    example_event: EventDTO
):
    """Test delete event."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnDelete):
        await repository.delete_event(id=example_event.as_key())


#  ------------------------------------------------------------------------------
#  Bridge task
#  ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_save_bridge_task_raise_exception(
    example_bridge_task
):
    """Test save bridge task and raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception
    
    with pytest.raises(RepositoryErrorOnSave):
        await repository.save_bridge_task(example_bridge_task)

@pytest.mark.asyncio
async def test_save_and_get_bridge_task(
    repository,
    example_bridge_task
):
    """Test save and get bridge task."""
    await repository.save_bridge_task(example_bridge_task)
    bridge_task = await repository.get_bridge_task(id=example_bridge_task.as_key())

    assert bridge_task.chain_id == example_bridge_task.chain_id
    assert bridge_task.block_number == example_bridge_task.block_number
    assert bridge_task.tx_hash == example_bridge_task.tx_hash
    assert bridge_task.log_index == example_bridge_task.log_index
    assert bridge_task.operation_hash == example_bridge_task.operation_hash
    assert bridge_task.event_name == example_bridge_task.event_name
    assert bridge_task.status == example_bridge_task.status


@pytest.mark.asyncio
async def test_get_bridge_task_raise_exception(
    example_bridge_task
):
    """Test get bridge_task raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnGet):
        await repository.get_bridge_task(id=example_bridge_task.as_key())

@pytest.mark.asyncio
async def test_get_bridge_tasks(
    repository, 
    example_bridge_task
):
    """Test get bridge_tasks."""
    for i in range(10):
        example_bridge_task.event_name = f"EventName{i}"
        await repository.save_bridge_task(example_bridge_task)

    bridge_task = await repository.get_bridge_tasks()

    assert len(bridge_task) == 10
    assert bridge_task[0].chain_id == 1
    assert bridge_task[0].event_name == "EventName0"

    assert bridge_task[-1].chain_id == 1
    assert bridge_task[-1].event_name == "EventName9"

@pytest.mark.asyncio
async def test_get_bridge_tasks_with_exception():
    """Test get bridge_tasks raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnGet):
        await repository.get_bridge_tasks()


#  ------------------------------------------------------------------------------
#  Last scanned block
#  ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_set_last_scanned_block_raise_exception():
    """Test set last scanned block and raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception
    
    with pytest.raises(RepositoryErrorOnSave):
        await repository.set_last_scanned_block(chain_id=1, block_numer=123)

@pytest.mark.asyncio
async def test_set_and_get_last_scanned_block(repository):
    """Test set and get last_scanned_block."""
    await repository.set_last_scanned_block(chain_id=1, block_numer=123)
    last_scanned_block = await repository.get_last_scanned_block(chain_id=1)
    assert last_scanned_block == 123


@pytest.mark.asyncio
async def test_get_last_scanned_block_raise_exception():
    """Test get last_scanned_block raise exception."""
    repository = RelayerRepositoryProvider()
    repository.db = mock_db.side_effect=Exception

    with pytest.raises(RepositoryErrorOnGet):
        await repository.get_last_scanned_block(chain_id=1)
