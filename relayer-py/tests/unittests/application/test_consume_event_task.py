from unittest.mock import MagicMock, patch
import pytest

from src.relayer.application.consume_event_task import ConsumeEventTask
from src.relayer.domain.exception import (
    BlockFinalityTimeExceededError, 
    EventConverterTypeError
)
from src.relayer.domain.relayer import (
    BlockFinalityResult,
    CalculateBlockFinalityResult,
    DefineChainBlockFinalityResult,
    EventDTO,
)
from src.relayer.provider.mock_relayer_blockchain_web3 import (
    MockRelayerBlockchainProvider
)
from src.relayer.provider.mock_relayer_register_pika import (
    MockRelayerRegisterEvent,
)
from tests.conftest import DATA_TEST
from utils.converter import to_bytes


PATH = 'src.relayer.application.consume_event_task'
EVENT_FILTERS = ['FAKE_EVENT_NAME']

# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(scope="function")
def blockchain_provider(request):
    # parameters for MockChainProvider
    # event, name, exception
    marker = request.node.get_closest_marker("relayer_provider_data")
    if marker:
        return MockRelayerBlockchainProvider(**marker.kwargs)
    return MockRelayerBlockchainProvider()

@pytest.fixture(scope="function")
def register_provider(request):
    # parameters for MockRelayerRegisterEvent
    # event, name, exception
    marker = request.node.get_closest_marker("register_provider_data")
    if marker:
        return MockRelayerRegisterEvent(**marker.kwargs)
    return MockRelayerRegisterEvent()

@pytest.fixture(scope="function")
def event_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args , # type: ignore
    )

@pytest.fixture(scope="function")
def consume_event_task(blockchain_provider, register_provider):
    return ConsumeEventTask(
        relayer_blockchain_provider=blockchain_provider,
        relayer_consumer_provider=register_provider,
        verbose=False
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_consume_event_task_init(blockchain_provider, register_provider):
    """Test ConsumeEventTask init."""
    app = ConsumeEventTask(
        relayer_blockchain_provider=blockchain_provider,
        relayer_consumer_provider=register_provider,
        verbose=False
    )
    assert app.rb_provider == blockchain_provider
    assert app.rr_provider == register_provider
    assert app.verbose is False
    assert app.operation_hash_events == {}

def test__convert_data_from_bytes_success(consume_event_task, event_dto):
    """
        Test _convert_data_from_bytes is converting event 
        from bytes to EventDTO.
    """
    app = consume_event_task
    event_bytes = to_bytes(event_dto)
    event = app._convert_data_from_bytes(event=event_bytes)
    assert event == event_dto

def test__convert_data_from_bytes_failed(consume_event_task):
    """
        Test _convert_data_from_bytes is raising EventConverterTypeError 
        with a bad event.
    """
    app = consume_event_task
    event_bytes = to_bytes({"k": "v"})
    with pytest.raises(EventConverterTypeError):
        app._convert_data_from_bytes(event=event_bytes)

def test_store_operation_hash( consume_event_task, event_dto):
    """
        Test store_operation_hash that is storing operation_hash and event
        data in a dict. If the 
    """
    app = consume_event_task
    op_hash = event_dto.data['operationHash']
    chain_id = event_dto.data['params']['chainIdFrom']
    
    result1 = app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )
    result2 = app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    expected = {
        'chain_id': chain_id,
        'block_step': event_dto.data['blockStep']
    }
    
    assert result1 is True
    assert result2 is False
    assert app.operation_hash_events[op_hash] == expected

@pytest.mark.parametrize('chain_ids, expected', [
    ([80002, 440], 80002),
    ([440, 1337], 440),
    ([440, 80002], 80002),
])
def test_define_chain_for_block_finality_chain_a_success(
    consume_event_task, 
    event_dto,
    chain_ids,
    expected,
):
    """
        Test define_chain_for_block_finality that returns 
        the chain id with the greatest `wait_block_validation` value.
        `wait_block_validation` is defined in 
        src.relayer.config.bridge_relayer_config_dev.toml
        -> How long it takes for a block to be finalized
    """
    print()
    app = consume_event_task
    # chain id 80002  wait_block_validation = 6
    # chain id 440    wait_block_validation = 1
    # chain id 1337   wait_block_validation = 1
    event_dto.data['params']['chainIdFrom'] = chain_ids[0]
    event_dto.data['params']['chainIdTo'] = chain_ids[1]
    result = app.define_chain_for_block_finality(event_dto=event_dto)

    # Tests
    assert isinstance(result, DefineChainBlockFinalityResult)
    assert result.ok == expected

def test_define_chain_for_block_finality_fail_with_invalid_chain_id(     
    consume_event_task, 
    event_dto
):
    """
        Test define_chain_for_block_finality that returns 
        the chain id with the greatest `wait_block_validation` value.
        `wait_block_validation` is defined in 
        src.relayer.config.bridge_relayer_config_dev.toml
        -> How long it takes for a block to be finalized
    """
    app = consume_event_task
    event_dto.data['params']['chainIdFrom'] = 123456
    result = app.define_chain_for_block_finality(event_dto=event_dto)

    # Tests
    assert isinstance(result, DefineChainBlockFinalityResult)
    assert "Invalid chain ID" in result.err

def test_define_block_step_for_block_finality(consume_event_task, event_dto):
    """
        Test define_block_step_for_block_finality that returns the block
        number to use to calculate and validate the block finality.
    """
    app = consume_event_task
    
    # Simulate a first event received
    # chain_id = 80002
    # block_step = 7866062
    app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    block_step_1 = app.define_block_step_for_block_finality(
        chain_id=123,
        current_block_step=123456,
        saved_chain_id=80002,
        saved_block_step=7866062,
    )

    block_step_2 = app.define_block_step_for_block_finality(
        chain_id=80002,
        current_block_step=123456,
        saved_chain_id=80002,
        saved_block_step=7866062,
    )
    
    assert block_step_1 == 123456
    assert block_step_2 == 7866062

def test_calculate_block_finality_success(consume_event_task):
    """
        Test calculate_block_finality that returns the block number target
        to wait until block finality.
        As it reads the config the chain id must exist
    """
    app = consume_event_task
    chain_id = 80002 # wait_block_validation = 6
    
    result = app.calculate_block_finality(
        chain_id=chain_id,
        block_step=10
    )

    assert isinstance(result, CalculateBlockFinalityResult)
    assert result.ok == 16

def test_calculate_block_finality_failed_with_invalid_chai_id(
    consume_event_task
):
    """
        Test calculate_block_finality that returns the block number target
        to wait until block finality.
        As it reads the config the chain id must exist
        In this test we provide an invalid chain id
    """
    app = consume_event_task
    chain_id = 12345
    
    result = app.calculate_block_finality(
        chain_id=chain_id,
        block_step=10
    )

    assert isinstance(result, CalculateBlockFinalityResult)
    assert "Invalid chain ID" in result.err

@pytest.mark.asyncio
async def test_block_validation(blockchain_provider, consume_event_task):
    """
        Test block_validation that is waiting for the current block number
        is equal or sup to the block finality provided.
        
        In this test the mock provider has a block_number = 0 and 
        increment +1 every call of get_block_number 
    """
    blockchain_provider.get_block_number = MagicMock(
        side_effect=blockchain_provider.get_block_number)

    app = consume_event_task
    app.sleep = 0
    app.rb_provider = blockchain_provider

    await app.validate_block_finality(
        chain_id=1337, 
        block_finality=5, 
    )
    
    blockchain_provider.get_block_number.assert_called()
    assert blockchain_provider.get_block_number.call_count == 5

@pytest.mark.asyncio
async def test_block_validation_raise_with_time_exceeded(
    blockchain_provider, 
    consume_event_task
):
    """
        Test block_validation that is waiting for the current block number
        is equal or sup to the block finality provided.
        
        In this test the mock provider has a block_number = 0 and 
        increment +1 every call of get_block_number 
    """
    blockchain_provider.get_block_number = MagicMock(
        side_effect=blockchain_provider.get_block_number)

    app = consume_event_task
    app.sleep = 1
    app.allocated_time = 0
    app.rb_provider = blockchain_provider

    with pytest.raises(BlockFinalityTimeExceededError):
        await app.validate_block_finality(
            chain_id=1337,
            block_finality=5,
        )

def test_manage_validate_block_finality_err_with_time_exceeded(
    consume_event_task, 
    event_dto
):
    """
        Test manage_validate_block_finality that returns error if
        time exceeded while processing block finality
    """
    app = consume_event_task
    app.sleep = 10
    app.allocated_time = 0
    event_dto.data['params']['chainIdTo'] = 1337
    event_dto.data['blockStep'] = 5
    app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    result = app.manage_validate_block_finality(
        event_dto=event_dto,
        saved_chain_id=80002,
        saved_block_step=5,
    )
    assert isinstance(result, BlockFinalityResult)
    assert "Block finality validation has exceeded" in result.err

def test_manage_validate_block_finality_err_with_invalid_chain_id_1(
    consume_event_task, 
    event_dto
):
    """
        Test manage_validate_block_finality that returns error event_dto 
        provide an invalid chain id
    """
    app = consume_event_task
    app.sleep = 0
    event_dto.data['params']['chainIdTo'] = 0
    event_dto.data['blockStep'] = 5
    app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    result = app.manage_validate_block_finality(
        event_dto=event_dto,
        saved_chain_id=80002,
        saved_block_step=5,
    )
    assert isinstance(result, DefineChainBlockFinalityResult)
    assert "Invalid chain ID" in result.err

def test_manage_validate_block_finality_err_with_invalid_chain_id_2(
    consume_event_task, 
    event_dto
):
    """
        Test manage_validate_block_finality that returns error if
        define_chain_for_block_finality returns invalid chain id
    """
    chain_id_result = DefineChainBlockFinalityResult()
    chain_id_result.ok = 0
    app = consume_event_task
    app.sleep = 0
    event_dto.data['params']['chainIdTo'] = 1337
    event_dto.data['blockStep'] = 5
    app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    app.define_chain_for_block_finality = MagicMock(
        return_value=chain_id_result
    )

    result = app.manage_validate_block_finality(
        event_dto=event_dto,
        saved_chain_id=80002,
        saved_block_step=5,
    )
    assert isinstance(result, CalculateBlockFinalityResult)
    assert "Invalid chain ID" in result.err

def test_manage_validate_block_finality_success(
    consume_event_task, 
    event_dto
):
    """
        Test manage_validate_block_finality that returns success after waiting 
        for the current block number is equal to block finality.

        In this test 
        ------------
        for chain id 1337
        blockStep = 5
        wait_block_validation = 1

        for chain id 80002
        blockStep = 5
        wait_block_validation = 6

        The process will choose chain id 80002 because it has the greatest 
        wait_block_validation value (6).

        The the block finality must be blockStep + wait_block_validation = 11
    """
    app = consume_event_task
    app.sleep = 0
    event_dto.data['params']['chainIdTo'] = 1337
    event_dto.data['blockStep'] = 5
    app.store_operation_hash(
        operation_hash=event_dto.data['operationHash'],
        chain_id=event_dto.data['params']['chainIdFrom'],
        block_step=event_dto.data['blockStep'],
    )

    result = app.manage_validate_block_finality(
        event_dto=event_dto,
        saved_chain_id=80002,
        saved_block_step=5,
    )
    assert isinstance(result, BlockFinalityResult)
    assert "Success" in result.ok[0]
    assert result.ok[1] == 11

@pytest.mark.parametrize('func_name', [
    'confirmFeesLockedAndDepositConfirmed'
])
def test_execute_smart_contract_function(
    consume_event_task, 
    func_name
):
    """
        Test execute_smart_contract_function that calls 
        ExecuteContractTask.__call__ successfully 
    """
    app = consume_event_task
    PATH_EXEC_CONTRACT = 'src.relayer.application.execute_contract'
    with patch(f'{PATH_EXEC_CONTRACT}.ExecuteContractTask.__call__') as mock:
        app.execute_smart_contract_function(
            chain_id=80002,
            func_name=func_name,
            params={}
        )
        mock.assert_called()

def test_callback_returns_none_with_invalid_event(consume_event_task):
    """Test _callback is returning None with a bad event."""
    app = consume_event_task
    app._convert_data_from_bytes = MagicMock(side_effect=app._convert_data_from_bytes)

    event_bytes = to_bytes({"k": "v"})
    result = app._callback(event=event_bytes)

    assert result is None
    app._convert_data_from_bytes.assert_called()
    app._convert_data_from_bytes.assert_called_with(event=event_bytes)

@pytest.mark.parametrize('event', [
    'OperationCreated',
    'FeesLockedConfirmed',
])
def test_callback_with_event_OpeartionCreated_only_store_operation_hash(
    consume_event_task,
    event_dto,
    event
):
    """
        Test _callback stores operation hash if it does not already exist.
        The process is then stopped.

        Event working together
            - OpeartionCreated
            - FeesLockedConfirmed
    """
    event_dto.name = event
    operation_hash = event_dto.data['operationHash']
    chain_id = event_dto.data['params']['chainIdFrom']
    block_step = event_dto.data['blockStep']

    app = consume_event_task
    event_bytes = to_bytes(event_dto)
    app._callback(event=event_bytes)

    expected = {
        'chain_id': chain_id,
        'block_step': block_step
    }
    assert app.operation_hash_events[operation_hash] == expected

@pytest.mark.parametrize('events', [
    ('OperationCreated', 'FeesLockedConfirmed'),
    ('FeesLockedConfirmed', 'OperationCreated'),
])
def test_callback_with_event_OpeartionCreated_and_FeesLockedConfirmed(
    consume_event_task,
    event_dto,
    events,
):
    """
        Test _callback that return success with both event
            - OperationCreated
            - FeesLockedConfirmed
        
        Not matter which event comes in with the same operation hash.
        1st event, operation hash, chain id and block_step are stored
        2nd event with the same operation hash, the process is trigger with
            - block finality validation
            - execute smart contract task
    """
    app = consume_event_task
    # 1st event
    event_dto.name = events[0]
    event_bytes = to_bytes(event_dto)
    app._callback(event=event_bytes)

    # 2nd event
    event_dto.name = events[1]
    event_bytes = to_bytes(event_dto)
    
    with patch(
        f"{PATH}.ConsumeEventTask.manage_validate_block_finality"
    ) as mock_block_validation:
        result = BlockFinalityResult()
        result.ok = "Success"
        mock_block_validation.return_value = result

        with patch(f"{PATH}.ExecuteContractTask.__call__") as mock_execute:
            result = app._callback(event=event_bytes)
            mock_execute.assert_called()
        mock_block_validation.assert_called()

@pytest.mark.parametrize('events', [
    ['OperationCreated', 'FeesLockedConfirmed'],
    ['FeesDeposited']
])
def test_callback_manage_validate_block_finality_returns_err(
    consume_event_task,
    event_dto,
    events,
):
    """
        Test _callback that returns result.err if manage_validate_block_finality
        returns error.
        manage_validate_block_finality can return error when 
        - chain id is invalid
        - calculate_block_finality returns error if chain id is invalid
        - exception BlockFinalityTimeExceededError on validate_block_finality
    """
    app = consume_event_task
    # mock define_chain_for_block_finality
    result_chain_block_finality = DefineChainBlockFinalityResult()
    result_chain_block_finality.err = "Invalid chain ID"
    app.define_chain_for_block_finality = MagicMock(
        return_value=result_chain_block_finality
    )
    # 1st event
    event_dto.name = events[0]
    event_bytes = to_bytes(event_dto)

    if len(events) > 1:
        # 2nd event
        app._callback(event=event_bytes)
        event_dto.name = events[1]
        event_bytes = to_bytes(event_dto)
    
    # Act
    result = app._callback(event=event_bytes)
    
    # Assert
    app.define_chain_for_block_finality.assert_called()
    assert "Invalid chain ID" in result.err


def test_call_consume_event_task_and_read_events(
    consume_event_task,
    register_provider,
    event_dto
):
    """
        Test __call__ that function calls.

        7 events are handled
        6 events are valid
        1 event is invalid
        2 events condition must validate block finality
            1st OperationCreated + FeesLockedConfirmed
            2nd FeesDeposited
        5 smart contract functions are executed

                                        | Block     | Pair
        Event                           | finality  | condition
        --------------------------------+-----------+----------------------
        OperationCreated                |   Yes     |   FeesLockedConfirmed
        FeesLockedConfirmed             |   Yes     |   OperationCreated
        FeesLockedAndDepositConfirmed   |   No      |   NA
        FeesDeposited                   |   Yes     |   NA
        FeesDepositConfirmed            |   No      |   NA
        OperationFinalized              |   No      |   NA
    """
    app = consume_event_task
    app.sleep = 0
    event_dto.data['blockStep'] = 5
    
    event_dtos_bytes = []
    events = [
        'OperationCreated',
        'FeesLockedConfirmed',
        'FeesLockedAndDepositConfirmed',
        'FeesDeposited',
        'FeesDepositConfirmed',
        'OperationFinalized',
        'InvalidEvent'
    ]

    for event in events:
        event_dto.name = event
        event_dto.data['blockStep'] += 5
        
        event_bytes = to_bytes(event_dto)
        event_dtos_bytes.append(event_bytes)
    
    register_provider.events = event_dtos_bytes
    
    # Mock 
    app._callback = MagicMock(side_effect=app._callback)
    app._convert_data_from_bytes = MagicMock(side_effect=app._convert_data_from_bytes)
    app.manage_validate_block_finality = MagicMock(side_effect=app.manage_validate_block_finality)
    app.store_operation_hash = MagicMock(side_effect=app.store_operation_hash)
    app.define_chain_for_block_finality = MagicMock(side_effect=app.define_chain_for_block_finality)
    app.define_block_step_for_block_finality = MagicMock(side_effect=app.define_block_step_for_block_finality)
    app.calculate_block_finality = MagicMock(side_effect=app.calculate_block_finality)
    app.validate_block_finality = MagicMock(side_effect=app.validate_block_finality)
    app.execute_smart_contract_function = MagicMock(side_effect=app.execute_smart_contract_function)

    # Act
    app()

    # handle events
    assert app._callback.call_count == 7
    assert app._convert_data_from_bytes.call_count == 7
    # Validate block finality
    assert app.manage_validate_block_finality.call_count == 2
    assert app.store_operation_hash.call_count == 2
    assert app.define_chain_for_block_finality.call_count == 2
    assert app.define_block_step_for_block_finality.call_count == 2
    assert app.calculate_block_finality.call_count == 2
    assert app.validate_block_finality.call_count == 2
    # Execute smart contract function
    assert app.execute_smart_contract_function.call_count == 5