from datetime import datetime, timezone
import logging
import pathlib
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest

from src.relayer.application.repository import Repository
from src.relayer.config.config import Config
from src.relayer.domain.event_db import (
    BridgeTaskActionDTO, 
    BridgeTaskDTO, 
    EventDTO, 
    EventDataDTO, 
    EventScanDTO,
)
from src.relayer.application.consume_events import ConsumeEvents, EventStatus
from src.relayer.domain.exception import (
    RelayerBlockFinalityTimeExceededError,
    RelayerBlockValidationFailed,
    RelayerBlockchainFailedExecuteSmartContract,
    RelayerBridgeTaskInvalidStatus,
    RelayerCalculateBLockFinalityError,
    RelayerConfigBlockchainDataMissing,
    RelayerConfigEventRuleKeyError,
    RelayerRegisterEventFailed,
    RepositoryErrorOnGet,
    RepositoryErrorOnSave,
    EventConverterTypeError
)
from src.relayer.provider.mock_relayer_blockchain_web3 import RelayerBlockchainProvider
from src.relayer.provider.mock_relayer_register_aio_pika import RelayerRegisterProvider
from src.relayer.provider.mock_relayer_repository_leveldb import RelayerRepositoryProvider


from src.relayer.domain.config import (
    EventRuleConfig,
    RelayerBlockchainConfigDTO,
    RelayerRegisterConfigDTO, 
)

from src.utils.converter import to_bytes
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
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)

@pytest.fixture(scope="function")
def blockchain_provider():
    return RelayerBlockchainProvider

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
def blockchain_config():
    config = RelayerBlockchainConfigDTO(
        chain_id=1,
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=0,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        smart_contract_deployment_block=666, 
        abi=[{}], 
        client='middleware'
    )
    return config

@pytest.fixture(scope="function")
def event_filters():
    return [
        'OperationCreated',
        'FeesDepositConfirmed',
        'FeesDeposited',
        'FeesDepositConfirmed',
        'FeesLockedAndDepositConfirmed',
        'OperationFinalized'
    ]

@pytest.fixture(scope="function")
def event_rule():
    return EventRuleConfig(
        event_name='OperationCreated', 
        origin='chainIdFrom', 
        has_block_finality=True, 
        chain_func_name='chainIdTo', 
        func_name='sendFeesLockConfirmation', 
        func_condition=None, 
        depends_on='FeesDeposited'
    )


@pytest.fixture(scope="function")
def config(
    blockchain_config,
    register_config,
    event_filters,
    event_rule,
):
    config = Config()
    config.get_register_config = MagicMock()
    config.get_register_config.return_value = register_config
    config.get_blockchain_config = MagicMock()
    config.get_blockchain_config.return_value = blockchain_config
    config.get_relayer_events = MagicMock()
    config.get_relayer_events.return_value = event_filters
    config.get_data_path = MagicMock()
    config.get_data_path.return_value = TEST_ROOT_PATH
    config.get_repository_name = MagicMock()
    config.get_repository_name.return_value = TEST_REPOSITORY_NAME
    config.get_relayer_event_rule = MagicMock()
    config.get_relayer_event_rule.return_value = event_rule

    return config

@pytest.fixture(scope="function")
def repository():
    repository = Repository(RelayerRepositoryProvider)
    repository.setup = AsyncMock()
    repository.get_last_scanned_block = AsyncMock()
    repository.get_last_scanned_block.return_value = 111
    repository.store_events = AsyncMock()
    repository.store_events.return_value = False
    repository.set_last_scanned_block = AsyncMock()
    repository.is_event_registered = AsyncMock()
    repository.is_event_registered.return_value = False
    repository.set_event_as_registered = AsyncMock()

    return repository

@pytest.fixture(scope="function")
def consume_events(config, repository):
     with patch(f'{PATH_APP}.Config', return_value=config):
        app = ConsumeEvents(
            relayer_blockchain_provider=RelayerBlockchainProvider,
            relayer_register_provider=RelayerRegisterProvider,
            relayer_repository_provider=RelayerRepositoryProvider,
            sleep=1,
            allocated_time=1200,
            log_level="INFO",
        )
        app.repository = repository
     return app


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
        operation_hash=event_data.args["operationHash"].hex(),
        event_name=event_data["event"],
        status="OperationCreated",
        datetime=datetime.now(timezone.utc),
    )

@pytest.fixture
def example_events_scan(example_event):
    """Create an example of EventScanDTO."""
    events = []
    for i in range(10):
        example_event.block_number = i
        events.append(example_event)

    return EventScanDTO(
        events=events,
        chunks_scanned=10
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

# -------------------------------------------------------
# Test init
# -------------------------------------------------------
def test_consume_event_task_init(consume_events, config, repository):
    """Test ConsumeEventTask init."""
    assert consume_events.log_level == 'INFO'
    assert consume_events.operation_hash_events == {}
    assert consume_events.sleep == 1
    assert consume_events.allocated_time == 1200
    assert consume_events.providers == {}
    assert consume_events.blockchain_provider == RelayerBlockchainProvider
    assert type(consume_events.register_provider) is RelayerRegisterProvider
    assert consume_events.config == config
    assert consume_events.repository == repository

# -------------------------------------------------------
# Private methods
# -------------------------------------------------------
# Test _async_setup
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_async_setup(consume_events):
    """Test async_setup."""    
    await consume_events._async_setup()
    consume_events.config.get_data_path.assert_called_once()
    consume_events.config.get_repository_name.assert_called_once()
    consume_events.repository.setup.assert_called_once()

# -------------------------------------------------------
# Test _chain_connector
# -------------------------------------------------------
def test_chain_connector(consume_events, blockchain_provider):
    """Test chain_connector."""
    blockchain_provider.connect_client = MagicMock()
    providers = set()
    for _ in range(5):
        providers.add(consume_events._chain_connector(chain_id=123))

    blockchain_provider.connect_client.assert_called_with(chain_id=123)
    assert len(providers) == 1
    assert isinstance(list(providers)[0], RelayerBlockchainProvider)

# -------------------------------------------------------
# Test _save_event_operation
# manage repository.save_bridge_task
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_save_event_operation(
    consume_events,
    example_event,
):
    """Test save_event_operation."""
    consume_events._async_setup = AsyncMock()
    consume_events.repository.save_bridge_task = AsyncMock()

    await consume_events._save_event_operation(
        event=example_event,
        status=EventStatus.PROCESSING.value
    )

    consume_events._async_setup.assert_called_once()
    consume_events.repository.save_bridge_task.assert_called_once()

@pytest.mark.asyncio
async def test_save_event_operation_invalid_status_raise_exception(
    consume_events,
    example_event,
):
    """Test save_event_operation."""
    consume_events._async_setup = AsyncMock()
    consume_events.repository.save_bridge_task = AsyncMock()

    with pytest.raises(RelayerBridgeTaskInvalidStatus):
        await consume_events._save_event_operation(
            event=example_event,
            status="INVALID"
        )

@pytest.mark.asyncio
async def test_save_event_operation_save_bridge_task_raise_exception(
    consume_events,
    example_event,
):
    """Test save_event_operation."""
    consume_events._async_setup = AsyncMock()
    consume_events.repository.save_bridge_task = AsyncMock()
    consume_events.repository.save_bridge_task.side_effect = RepositoryErrorOnSave("Error")

    with pytest.raises(RepositoryErrorOnSave):
        await consume_events._save_event_operation(
            event=example_event,
            status=EventStatus.PROCESSING.value
        )

# -------------------------------------------------------
# Test calculate_wait_block_validation
# mamage calcul
# manage RelayerConfigBlockchainDataMissing
# -------------------------------------------------------
@pytest.mark.parametrize('params', [
    {
        # block_finality - current_block_number = 6
        'wait_block_validation': 6,
        'block_validation_second_per_block': 12,
        'current_block_number': 123111,
        'block_finality': 123117,
        'expected': 60
    },
    {
        # block_finality - current_block_number = 2 (>1)
        'wait_block_validation': 6,
        'block_validation_second_per_block': 12,
        'current_block_number': 123115,
        'block_finality': 123117,
        'expected': 12
    },
    {
        # block_finality - current_block_number = 1
        'wait_block_validation': 6,
        'block_validation_second_per_block': 12,
        'current_block_number': 123116,
        'block_finality': 123117,
        'expected': int(12 / 2)
    },
    {
        # block_finality - current_block_number = 1
        'wait_block_validation': 6,
        'block_validation_second_per_block': 0,
        'current_block_number': 123116,
        'block_finality': 123117,
        'expected': 1
    },
    
])
def test_calculate_wait_block_validation(
    blockchain_config,
    example_event,
    config,
    params,
):
    """Test calculate_wait_block_validation."""
    blockchain_config.wait_block_validation = params['wait_block_validation']
    blockchain_config.block_validation_second_per_block = params['block_validation_second_per_block']

    config.get_blockchain_config = MagicMock(return_value=blockchain_config)

    with patch(f'{PATH_APP}.Config', return_value=config):
        app = ConsumeEvents(
            relayer_blockchain_provider=RelayerBlockchainProvider,
            relayer_register_provider=RelayerRegisterProvider,
            relayer_repository_provider=RelayerRepositoryProvider,
            sleep=1,
            allocated_time=1200,
            log_level="INFO",
        )
        app.get_current_block_number = MagicMock(return_value=params['current_block_number'])

        wait = app.calculate_wait_block_validation(
            event=example_event,
            block_finality=params['block_finality'],
        )
        assert wait == params['expected']


def test_calculate_wait_block_validation_raise_exception(
    consume_events,
    example_event
):
    """
    Test calculate_block_finality.
    
    manage RelayerConfigBlockchainDataMissing
    """
    consume_events.config.get_blockchain_config = MagicMock()
    consume_events.config.get_blockchain_config.side_effect = RelayerConfigBlockchainDataMissing("Error")

    with pytest.raises(RelayerCalculateBLockFinalityError):
        consume_events.calculate_wait_block_validation(
            event=example_event,
            block_finality=123456,
        )

# -------------------------------------------------------
# Test calculate_block_finality
# mamage calcul
# manage RelayerConfigBlockchainDataMissing
# -------------------------------------------------------
def test_calculate_block_finality(
    consume_events,
    example_event
):
    """
    Test calculate_block_finality.
    
    wait_block_validation = 6
    second_per_block = 0
    block_finality_in_sec = 0
    block_finality = 6 + 123111 = 123117
    """
    (
        block_finality, 
        block_finality_in_sec
    ) = consume_events.calculate_block_finality(event=example_event)
    
    assert block_finality == 123117
    assert block_finality_in_sec == 0

def test_calculate_block_finality_raise_exception(
    consume_events,
    example_event
):
    """
    Test calculate_block_finality.
    
    manage RelayerConfigBlockchainDataMissing
    """
    consume_events.config.get_blockchain_config = MagicMock()
    consume_events.config.get_blockchain_config.side_effect = RelayerConfigBlockchainDataMissing("Error")

    with pytest.raises(RelayerCalculateBLockFinalityError):
        consume_events.calculate_block_finality(event=example_event)
    
# -------------------------------------------------------
# Test validate_block_finality
# manage RelayerBlockFinalityTimeExceededError
# -------------------------------------------------------
current_block = 2
@pytest.mark.asyncio
async def test_validate_block_finality(
    consume_events,
    example_event
):
    """
    Test validate_block_finality.
    Loop until the current block is equal to bock finality (target)
    Wait for n seconds between each check
    For testing wait is 0 seconds
    """
    def increment_current_block(any):
        global current_block
        current_block += 1
        return current_block

    consume_events.calculate_wait_block_validation = MagicMock(return_value=0)
    consume_events.get_current_block_number = MagicMock()
    consume_events.get_current_block_number.side_effect = increment_current_block

    block_number = await consume_events.validate_block_finality(
        event=example_event,
        block_finality=10,
    )

    consume_events.get_current_block_number.call_count == 11
    assert block_number == 11

@pytest.mark.asyncio
async def test_validate_block_finality_raise_exception(
    consume_events,
    example_event
):
    """
    Test validate_block_finality.
    raise RelayerBlockFinalityTimeExceededError
    """
    consume_events.allocated_time = 0
    consume_events.get_current_block_number = MagicMock()
    consume_events.get_current_block_number.return_value = 5
    
    with pytest.raises(RelayerBlockFinalityTimeExceededError):
        await consume_events.validate_block_finality(
            event=example_event,
            block_finality=10,
        )

# -------------------------------------------------------
# Test manage_validate_block_finality
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_manage_validate_block_finality(
    consume_events,
    example_event
):
    """
    Test manage_validate_block_finality.
    """
    consume_events.calculate_block_finality = MagicMock()
    consume_events.calculate_block_finality.return_value = (123117, 0)

    consume_events.validate_block_finality = AsyncMock()
    consume_events.validate_block_finality.return_value = 123117

    block_number = await consume_events.manage_validate_block_finality(
        event=example_event
    )

    assert block_number == 123117
    consume_events.calculate_block_finality.assert_called_once_with(
        event=example_event
    )
    consume_events.validate_block_finality.assert_called_once_with(
        event=example_event,
        block_finality=123117,
    )

@pytest.mark.asyncio
async def test_manage_validate_block_finality_raise_exception_1(
    consume_events,
    example_event
):
    """
    Test manage_validate_block_finality.
    Raise RelayerBlockValidationFailed
    """
    consume_events.calculate_block_finality = MagicMock()
    consume_events.calculate_block_finality.side_effect = RelayerCalculateBLockFinalityError("Error")
    with pytest.raises(RelayerBlockValidationFailed):
        await consume_events.manage_validate_block_finality(
            event=example_event
        )


@pytest.mark.asyncio
async def test_manage_validate_block_finality_raise_exception_2(
    consume_events,
    example_event
):
    """
    Test manage_validate_block_finality.
    Raise RelayerBlockValidationFailed
    """
    consume_events.calculate_block_finality = MagicMock()
    consume_events.calculate_block_finality.return_value = (123117, 0)
    consume_events.validate_block_finality = AsyncMock()
    consume_events.validate_block_finality.side_effect = RelayerBlockFinalityTimeExceededError("Error")

    with pytest.raises(RelayerBlockValidationFailed):
        await consume_events.manage_validate_block_finality(
            event=example_event
        )

# -------------------------------------------------------
# Test depend_on_event
# -------------------------------------------------------
def test_depend_on_event_returns_event_name(consume_events, event_rule):
    """Test depend_on_event."""
    assert consume_events.depend_on_event(event_name="OperationCreated") == event_rule.depends_on

def test_depend_on_event_return_none(consume_events, event_rule):
    """Test depend_on_event."""
    event_rule.depends_on = None
    consume_events.config.get_relayer_event_rule = MagicMock()
    consume_events.config.get_relayer_event_rule.return_value = event_rule
    assert consume_events.depend_on_event(event_name="OperationCreated") is None

def test_depend_on_event_return_none_with_exception(consume_events):
    """Test depend_on_event."""
    consume_events.config.get_relayer_event_rule.side_effect = Exception("Error")
    assert consume_events.depend_on_event(event_name="OperationCreated") is None

# -------------------------------------------------------
# Test get_bridge_task_status
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_bridge_task_status(consume_events, example_bridge_task):
    """Test get bridge task status."""
    consume_events.repository.get_bridge_task = AsyncMock()
    consume_events.repository.get_bridge_task.return_value = example_bridge_task
    
    status = await consume_events.get_bridge_task_status(
        example_bridge_task.operation_hash,
        example_bridge_task.event_name,
    )

    assert status == example_bridge_task.status

@pytest.mark.asyncio
async def test_get_bridge_task_status_returns_none(consume_events, example_bridge_task):
    """Test get bridge task status."""
    consume_events.repository.get_bridge_task = AsyncMock()
    consume_events.repository.get_bridge_task.side_effect = RepositoryErrorOnGet("Error")
    
    status = await consume_events.get_bridge_task_status(
        example_bridge_task.operation_hash,
        example_bridge_task.event_name,
    )

    assert status is None


# -------------------------------------------------------
# Test execute_smart_contract_function_for_event
# -------------------------------------------------------
def test_execute_smart_contract_function_for_event(consume_events, example_event):
    """Test execute smart contract function."""    
    bridge_task_action_dto = BridgeTaskActionDTO(
        operation_hash=example_event.data.operation_hash_str,
        func_name='func_name', 
        params={
            "operationHash": example_event.data.operation_hash_bytes,
            "params": example_event.data.raw_params(),
            "blockStep": example_event.data.block_step,
        }
    )

    with patch(f'{PATH_APP}.ExecuteContracts') as mock_execute_contracts:
        mock_execute_contracts.__call__ = MagicMock()

        consume_events.execute_smart_contract_function_for_event(
            chain_id=123,
            event=example_event,
            func_name='func_name',
        )

        mock_execute_contracts.assert_called_once_with(
            relayer_blockchain_provider=consume_events.blockchain_provider,
            log_level=consume_events.log_level
        )

        mock_execute_contracts().assert_called_once_with(
            chain_id=123,
            bridge_task_action_dto=bridge_task_action_dto
        )

def test_execute_smart_contract_function_for_event_raise_exception(
    consume_events, 
    example_event
):
    """Test execute smart contract function."""    
    with patch(f'{PATH_APP}.ExecuteContracts') as mock_execute_contracts:
        mock_execute_contracts.__call__ = MagicMock()
        mock_execute_contracts().side_effect = RelayerBlockchainFailedExecuteSmartContract("Error")

        with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
            consume_events.execute_smart_contract_function_for_event(
                chain_id=123,
                event=example_event,
                func_name='func_name',
            )

# -------------------------------------------------------
# Test callback
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_callback(consume_events, example_event):
    """Test callback."""
    consume_events.manage_event_with_rules = AsyncMock()
    
    await consume_events.callback(event=to_bytes(example_event))

    consume_events.manage_event_with_rules.assert_called_once_with(
        event=example_event
    )

@pytest.mark.asyncio
async def test_callback_return_manage_exception_1(consume_events, example_event):
    """Test callback."""
    consume_events.manage_event_with_rules = AsyncMock()
    consume_events.manage_event_with_rules.side_effect = RepositoryErrorOnSave("Error")
    consume_events.logger = MagicMock()
    consume_events.logger.error = MagicMock()

    await consume_events.callback(event=to_bytes(example_event))

    consume_events.logger.error.assert_called_once_with(
        f"{consume_events.Emoji.fail.value} Error"
    )

@pytest.mark.asyncio
async def test_callback_return_manage_exception_2(consume_events, example_event):
    """Test callback."""
    consume_events.manage_event_with_rules = AsyncMock()
    consume_events.manage_event_with_rules.side_effect = EventConverterTypeError("Error")
    consume_events.logger = MagicMock()
    consume_events.logger.error = MagicMock()

    await consume_events.callback(event=to_bytes(example_event))

    consume_events.logger.error.assert_called_once_with(
        f"{consume_events.Emoji.fail.value} Error"
    )


# -------------------------------------------------------
# Test manage_event_with_rules
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_manage_event_with_rules_manage_exception_1(consume_events, example_event):
    """
        Test manage_event_with_rules.

        Return None when getting exception RelayerConfigEventRuleKeyError
    
    """
    consume_events.print_log = MagicMock()
    consume_events.config.get_relayer_event_rule = MagicMock()
    consume_events.config.get_relayer_event_rule.side_effect = RelayerConfigEventRuleKeyError("Error")
    consume_events.logger = MagicMock()
    consume_events.logger.warning = MagicMock()
    # act
    assert await consume_events.manage_event_with_rules(event=example_event) is None
    # assert
    consume_events.logger.warning.assert_called_once_with(
        f"{consume_events.Emoji.alert.value}Unknown event={example_event.event_name}. Error"
    )

@pytest.mark.asyncio
async def test_manage_event_with_rules_manage_exception_2(
    consume_events, 
    example_event
):
    """
        Test manage_event_with_rules.
    
        Raise RepositoryErrorOnSave when getting exception RepositoryErrorOnSave
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events._save_event_operation.side_effect = RepositoryErrorOnSave("Error")
    # assert
    with pytest.raises(RepositoryErrorOnSave):
        await consume_events.manage_event_with_rules(event=example_event)

@pytest.mark.asyncio
async def test_manage_event_with_rules_manage_exception_3(
    consume_events, 
    example_event
):
    """
        Test manage_event_with_rules.
    
        Raise RelayerBridgeTaskInvalidStatus when getting exception RelayerBridgeTaskInvalidStatus
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events._save_event_operation.side_effect = RelayerBridgeTaskInvalidStatus("Error")
    # assert
    with pytest.raises(RelayerBridgeTaskInvalidStatus):
        await consume_events.manage_event_with_rules(event=example_event)

@pytest.mark.asyncio
async def test_manage_event_with_rules_manage_exception_4(
    consume_events, 
    example_event
):
    """
        Test manage_event_with_rules.
    
        Raise RelayerBlockValidationFailed when getting exception RelayerBlockValidationFailed
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events.manage_validate_block_finality = AsyncMock()
    consume_events.manage_validate_block_finality.side_effect = RelayerBlockValidationFailed("Error")
    # assert
    with pytest.raises(RelayerBlockValidationFailed):
        await consume_events.manage_event_with_rules(event=example_event)
    
@pytest.mark.asyncio
async def test_manage_event_with_rules_manage_exception_5(
    consume_events, 
    example_event,
):
    """
        Test manage_event_with_rules.

        Depends on the event "A"
        Get the status of the event "A" => status is FAILED
        Raise RelayerBlockValidityError
        Set status of event "B" as Failed when status of event "A" is Failed

        -> set status of event "B" as Failed
        -> return None
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events.manage_validate_block_finality = AsyncMock()
    # Get the status of event "A"
    consume_events.get_bridge_task_status = AsyncMock()
    consume_events.get_bridge_task_status.return_value = EventStatus.FAILED.value
    consume_events.logger = MagicMock()
    consume_events.logger.error = MagicMock()

    id_msg = (
        f"chain_id={example_event.chain_id} "
        f"operation_hash={example_event.data.operation_hash_str} "
        f"event={example_event.event_name} "
    )
    cfg = consume_events.config.get_relayer_event_rule(example_event.event_name)
    error = f"{id_msg}event {cfg.depends_on} has failed!"

    #  act
    assert await consume_events.manage_event_with_rules(event=example_event) is None
    
    # assert
    consume_events.logger.error.assert_called_once_with(
        f"{consume_events.Emoji.fail.value}{id_msg}"
        f"Failed to manage event. "
        f"{error}"
    )
    
    expected_calls = [
        call(event=example_event, status=EventStatus.PROCESSING.value),
        call(event=example_event, status=EventStatus.FAILED.value)
    ]
    consume_events._save_event_operation.assert_has_calls(expected_calls)

@pytest.mark.asyncio
async def test_manage_event_with_rules_save_status_success(
    consume_events, 
    example_event,
):
    """
        Test manage_event_with_rules.
    
        Depends on the event "A"
        Get the status of the event "A" => status is PROCESSING

        -> Set the status of the event "B" as SUCCESS 
        -> return None

        This means that if event "A" depends on event "B" then they both need to be 
        SUCCESS to continue (execute smart contract). 
        If one of them is PROCESSING then the other one is SUCCESS.
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events.manage_validate_block_finality = AsyncMock()
    consume_events.get_bridge_task_status = AsyncMock()
    # Get the status of event "A"
    consume_events.get_bridge_task_status.return_value = EventStatus.PROCESSING.value
    consume_events.execute_smart_contract_function_for_event = MagicMock()

    # act
    assert await consume_events.manage_event_with_rules(event=example_event) is None
    
    # assert
    expected_calls = [
        call(event=example_event, status=EventStatus.PROCESSING.value),
        call(event=example_event, status=EventStatus.SUCCESS.value)
    ]
    consume_events._save_event_operation.assert_has_calls(expected_calls)

@pytest.mark.asyncio
async def test_manage_event_with_rules_execute_smart_contract_function(
    consume_events, 
    example_event,
):
    """
        Test manage_event_with_rules.
    
        Depends on the event "A"
        Get the status of the event "A" => status is SUCCESS

        -> excute smart contract
        -> Set the status of the event "B" as SUCCESS 
        -> return None
    """
    consume_events.print_log = MagicMock()
    consume_events._save_event_operation = AsyncMock()
    consume_events.manage_validate_block_finality = AsyncMock()
    consume_events.get_bridge_task_status = AsyncMock()
    consume_events.get_bridge_task_status.return_value = EventStatus.SUCCESS.value
    consume_events.execute_smart_contract_function_for_event = MagicMock()

    # act
    assert await consume_events.manage_event_with_rules(event=example_event) is None
    
    # assert
    expected_calls = [
        call(event=example_event, status=EventStatus.PROCESSING.value),
        call(event=example_event, status=EventStatus.SUCCESS.value)
    ]
    consume_events._save_event_operation.assert_has_calls(expected_calls)
    consume_events.execute_smart_contract_function_for_event.assert_called_once()


# -------------------------------------------------------
#  Public methods
# -------------------------------------------------------
# Test get_incomplete_bridge_tasks
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_get_incomplete_bridge_tasks_no_incomplete_tasks(
    consume_events, 
    example_bridge_task
):
    """Test get_incomplete_bridge_tasks."""
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_bridge_tasks = AsyncMock()
    consume_events.repository.get_bridge_tasks.return_value = [example_bridge_task]
    list_bridge_tasks = await consume_events.get_incomplete_bridge_tasks()
    consume_events.repository.get_bridge_tasks.assert_called_once()
    consume_events._async_setup.assert_called_once()
    assert list_bridge_tasks == []

@pytest.mark.asyncio
async def test_get_incomplete_bridge_tasks_empty_list_when_exception(
    consume_events
):
    """Test get_incomplete_bridge_tasks."""
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_bridge_tasks = AsyncMock()
    consume_events.repository.get_bridge_tasks.side_effect = RepositoryErrorOnGet("Error")
    list_bridge_tasks = await consume_events.get_incomplete_bridge_tasks()
    consume_events.repository.get_bridge_tasks.assert_called_once()
    consume_events._async_setup.assert_called_once()
    assert list_bridge_tasks == []

@pytest.mark.asyncio
async def test_get_incomplete_bridge_tasks_with_incomplete_tasks(
    consume_events, 
    example_bridge_task
):
    """
    Test get_incomplete_bridge_tasks.
    bridge_task with status is FAILED
    """
    consume_events._async_setup = AsyncMock()
    example_bridge_task.status = EventStatus.FAILED.value
    consume_events.repository.get_bridge_tasks = AsyncMock()
    consume_events.repository.get_bridge_tasks.return_value = [example_bridge_task]
    list_bridge_tasks = await consume_events.get_incomplete_bridge_tasks()
    consume_events.repository.get_bridge_tasks.assert_called_once()
    consume_events._async_setup.assert_called_once()
    assert list_bridge_tasks == [example_bridge_task]

# -------------------------------------------------------
# Test resume_incomplete_bridge_tasks
# manage RepositoryErrorOnGet
# manage bridge_tasks is empty
# manage RelayerRegisterEventFailed
# manage bridge_tasks is not empty
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_incomplete_bridge_tasks_register_event(
    consume_events,
    example_bridge_task,
    example_event,
):
    """
        Test resume_incomplete_bridge_tasks.

        Get the incomplete bridge task
        Get the event from the repository
        Register the event to be processed
    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    # Get the incomplete bridge task that needs to be resumed
    consume_events.get_incomplete_bridge_tasks = AsyncMock()
    consume_events.get_incomplete_bridge_tasks.return_value = [example_bridge_task]
    # get the event from the repository
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    # Register the event to be processed
    consume_events.register_provider.register_event = AsyncMock()

    # act
    await consume_events.resume_incomplete_bridge_tasks(chain_id=1)
    
    # assert
    consume_events._async_setup.assert_called_once()
    consume_events.get_incomplete_bridge_tasks.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_bridge_task.as_id()
    )
    consume_events.register_provider.register_event.assert_called_once_with(
        event=to_bytes(example_event)
    )

@pytest.mark.asyncio
async def test_resume_incomplete_bridge_tasks_no_task_for_chain_id(
    consume_events,
    example_bridge_task,
    example_event,
):
    """
        Test resume_incomplete_bridge_tasks.

        Get the incomplete bridge task
        Chain id is not the same as the task chain id
        Do not Get the event from the repository
        Do not Register the event to be processed
    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    # Get the incomplete bridge task that needs to be resumed
    consume_events.get_incomplete_bridge_tasks = AsyncMock()
    consume_events.get_incomplete_bridge_tasks.return_value = [example_bridge_task]
    # get the event from the repository
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    # Register the event to be processed
    consume_events.register_provider.register_event = AsyncMock()

    # act
    await consume_events.resume_incomplete_bridge_tasks(chain_id=123)
    
    # assert
    consume_events._async_setup.assert_called_once()
    consume_events.get_incomplete_bridge_tasks.assert_called_once()
    consume_events.repository.get_event.assert_not_called()
    consume_events.register_provider.register_event.assert_not_called()

@pytest.mark.asyncio
async def test_resume_incomplete_bridge_tasks_get_event_raise_exception(
    consume_events,
    example_bridge_task,
):
    """
        Test resume_incomplete_bridge_tasks.

        Get the incomplete bridge task that needs to be resumed
        Raise RepositoryErrorOnGet when getting event from the repository
        Do no register the event and continue to the next bridge task
    """
    consume_events._async_setup = AsyncMock()
    consume_events.get_incomplete_bridge_tasks = AsyncMock()
    # Get the incomplete bridge task that needs to be resumed
    consume_events.get_incomplete_bridge_tasks.return_value = [example_bridge_task]
    # Raise RepositoryErrorOnGet when getting event from the repository
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.side_effect = RepositoryErrorOnGet("Error")
    consume_events.register_provider.register_event = AsyncMock()

    await consume_events.resume_incomplete_bridge_tasks(chain_id=1)
    # assert
    consume_events._async_setup.assert_called_once()
    consume_events.get_incomplete_bridge_tasks.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_bridge_task.as_id()
    )
    consume_events.register_provider.register_event.assert_not_called()

@pytest.mark.asyncio
async def test_resume_incomplete_bridge_tasks_register_event_raise_exception(
    consume_events,
    example_bridge_task,
    example_event,
):
    """
        Test resume_incomplete_bridge_tasks.
        
        Get the incomplete bridge task that needs to be resumed
        Get the event from the repository
        Raise RelayerRegisterEventFailed when registering the event to be processed
        Do no register the event and continue to the next bridge task
    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    # Get the incomplete bridge task that needs to be resumed
    consume_events.get_incomplete_bridge_tasks = AsyncMock()
    consume_events.get_incomplete_bridge_tasks.return_value = [example_bridge_task]
    # get the event from the repository
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    # Raise RelayerRegisterEventFailed when registering the event to be processed
    consume_events.register_provider.register_event = AsyncMock()
    consume_events.register_provider.register_event.side_effect = RelayerRegisterEventFailed('Error')

    await consume_events.resume_incomplete_bridge_tasks(chain_id=1)
    
    consume_events._async_setup.assert_called_once()
    consume_events.get_incomplete_bridge_tasks.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_bridge_task.as_id()
    )
    consume_events.register_provider.register_event.assert_called_once_with(
        event=to_bytes(example_event)
    )

@pytest.mark.asyncio
async def test_resume_incomplete_bridge_tasks_does_not_register_event(
    consume_events,
):
    """
        Test resume_incomplete_bridge_tasks.
        
        Get no incomplete bridge task that needs to be resumed
        Do not get the event from the repository
        Do not register the event
    """
    consume_events._async_setup = AsyncMock()
    #  Get no incomplete bridge task that needs to be resumed
    consume_events.get_incomplete_bridge_tasks = AsyncMock()
    consume_events.get_incomplete_bridge_tasks.return_value = []
    # Do not get the event from the repository
    consume_events.repository.get_event = AsyncMock()
    # Do not register the event
    consume_events.register_provider.register_event = AsyncMock()

    # act
    await consume_events.resume_incomplete_bridge_tasks(chain_id=1)
    # assert
    consume_events._async_setup.assert_called_once()
    consume_events.get_incomplete_bridge_tasks.assert_called_once()
    consume_events.repository.get_event.assert_not_called()
    consume_events.register_provider.register_event.assert_not_called()

# -------------------------------------------------------
# Test resume_bridge_task
# 
# manage repository get_event
# manage RepositoryErrorOnGet -> exit
# manage register_event
# manage repository save_event 
# manage RelayerRegisterEventFailed -> exit
# manage RepositoryErrorOnSave
# -------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_bridge_task(
    consume_events,
    example_event
):
    """
        Test resume_bridge_task.

    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    consume_events.register_provider.register_event = AsyncMock()
    consume_events.repository.save_event = AsyncMock()
    example_event.handled = "registered"

    await consume_events.resume_bridge_task(
        chain_id=example_event.chain_id,
        block_number=example_event.block_number,
        tx_hash=example_event.tx_hash,
        log_index=example_event.log_index
    )
    # assert
    consume_events._async_setup.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_event.as_key()
    )
    consume_events.register_provider.register_event.assert_called_once_with(
        event=to_bytes(example_event)
    )
    consume_events.repository.save_event.assert_called_once_with(
        event=example_event
    )

@pytest.mark.asyncio
async def test_resume_bridge_task_get_event_raise_exception(
    consume_events,
    example_event
):
    """
        Test resume_bridge_task.
    """
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.side_effect = RepositoryErrorOnGet("Error")
    consume_events.register_provider.register_event = AsyncMock()
    consume_events.repository.save_event = AsyncMock()

    await consume_events.resume_bridge_task(
        chain_id=example_event.chain_id,
        block_number=example_event.block_number,
        tx_hash=example_event.tx_hash,
        log_index=example_event.log_index
    )
    
    consume_events._async_setup.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_event.as_key()
    )
    consume_events.register_provider.register_event.assert_not_called()
    consume_events.repository.save_event.assert_not_called()

@pytest.mark.asyncio
async def test_resume_bridge_task_register_event_raise_exception(
    consume_events,
    example_event
):
    """
        Test resume_bridge_task.
    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    consume_events.register_provider.register_event = AsyncMock()
    consume_events.register_provider.register_event.side_effect = RelayerRegisterEventFailed('Error')
    consume_events.repository.save_event = AsyncMock()
    example_event.handled = "registered"

    await consume_events.resume_bridge_task(
        chain_id=example_event.chain_id,
        block_number=example_event.block_number,
        tx_hash=example_event.tx_hash,
        log_index=example_event.log_index
    )
    
    consume_events._async_setup.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_event.as_key()
    )
    consume_events.register_provider.register_event.assert_called_once_with(
        event=to_bytes(example_event)
    )
    consume_events.repository.save_event.assert_not_called()

@pytest.mark.asyncio
async def test_resume_bridge_task_save_event_raise_exception(
    consume_events,
    example_event
):
    """
    Test resume_bridge_task.
    """
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    consume_events.repository.get_event = AsyncMock()
    consume_events.repository.get_event.return_value = example_event
    consume_events.register_provider.register_event = AsyncMock()
    consume_events.repository.save_event = AsyncMock()
    consume_events.repository.save_event.side_effect = RepositoryErrorOnSave("Error")
    example_event.handled = "registered"

    await consume_events.resume_bridge_task(
        chain_id=example_event.chain_id,
        block_number=example_event.block_number,
        tx_hash=example_event.tx_hash,
        log_index=example_event.log_index
    )
    
    consume_events._async_setup.assert_called_once()
    consume_events.repository.get_event.assert_called_once_with(
        id=example_event.as_key()
    )
    consume_events.register_provider.register_event.assert_called_once_with(
        event=to_bytes(example_event)
    )
    consume_events.repository.save_event.assert_called_once_with(
        event=example_event
    )

# -------------------------------------------------------
# Test __call__
# -------------------------------------------------------
@pytest.mark.asyncio
async def test___call__(consume_events):
    """Test __call__."""
    consume_events.print_log = MagicMock()
    consume_events._async_setup = AsyncMock()
    consume_events.register_provider.read_events = AsyncMock()

    await consume_events()
    # assert
    consume_events.register_provider.read_events.assert_called_once_with(
        callback=consume_events.callback
    )
    consume_events._async_setup.assert_called_once()