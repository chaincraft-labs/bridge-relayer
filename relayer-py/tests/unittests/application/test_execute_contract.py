import logging
from unittest.mock import MagicMock
import pytest

from src.relayer.application.execute_contract import ExecuteContractTask
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    BridgeTaskTxResult,
    EventDTO,
)
from src.relayer.provider.mock_relayer_blockchain_web3_v2 import (
    MockRelayerBlockchainProvider
)
from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.domain.exception import (
    RelayerBlockchainFailedExecuteSmartContract,
)
from tests.conftest import DATA_TEST

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
def blockchain_provider(request):
    # parameters for MockChainProvider
    # event, name, exception
    marker = request.node.get_closest_marker("relayer_provider_data")
    if marker:
        return MockRelayerBlockchainProvider(**marker.kwargs)
    return MockRelayerBlockchainProvider()

@pytest.fixture(scope="function")
def event_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args , # type: ignore
        block_key=f'{event.blockNumber}-{event.transactionIndex}'
    )

@pytest.fixture(scope="function")
def bridge_task_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    return BridgeTaskDTO(
        func_name='func_name', 
        params=event.args['params']
    )

@pytest.fixture(scope="function")
def execute_contract_task(blockchain_provider):
    return ExecuteContractTask(
        relayer_blockchain_provider=blockchain_provider)
@pytest.fixture
def get_blockchain_config():
    config = RelayerBlockchainConfigDTO(
        chain_id=123, 
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=0,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        genesis_block=123456789, 
        abi=[{}], 
        client='middleware'
    )
    return config
# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_execute_contract_task_init(blockchain_provider):
    """Test ExecuteContractTask init."""
    app = ExecuteContractTask(
        relayer_blockchain_provider=blockchain_provider)
    assert app.rb_provider == blockchain_provider

def test_call_contract_func_print_err_with_failed_tx(
        execute_contract_task,
        blockchain_provider,
        bridge_task_dto
):
    """
        Test call_contract_func that print an err with invalid transaction
        while executing smart contract task.
    """
    app = execute_contract_task
    blockchain_provider.exception = Exception("fake Tx exception")
    with pytest.raises(
        RelayerBlockchainFailedExecuteSmartContract,
        match="fake Tx exception"
    ):
        app.call_contract_func(chain_id=80002, bridge_task_dto=bridge_task_dto)


def test_call_contract_func_print_success_with_valid_tx(
        execute_contract_task,
        blockchain_provider,
        bridge_task_dto
):
    """
        Test call_contract_func that print success with valid transaction
        while executing smart contract task.
    """
    app = execute_contract_task
    blockchain_provider.tx_hash = "0x7d90ac3daf3ced0d01adbde94f2f4fe0eb2d79ce55b7bab9e08d6cac4b3ea01c"
    tx = app.call_contract_func(chain_id=80002, bridge_task_dto=bridge_task_dto)
    assert tx.tx_hash == "0x7d90ac3daf3ced0d01adbde94f2f4fe0eb2d79ce55b7bab9e08d6cac4b3ea01c"
    assert isinstance(tx, BridgeTaskTxResult)

def test_call_that_call_contract_func(
    execute_contract_task,
    blockchain_provider,
    bridge_task_dto
):
    """
        Test __call__ that execute call_contract_func function
    """
    app = execute_contract_task
    blockchain_provider.set_chain_id = MagicMock(
        side_effect=blockchain_provider.set_chain_id)
    app.call_contract_func = MagicMock(side_effect=app.call_contract_func)

    app(chain_id=80002, bridge_task_dto=bridge_task_dto)
    blockchain_provider.set_chain_id.assert_called_with(chain_id=80002)
    app.call_contract_func.assert_called_with(
        chain_id=80002,
        bridge_task_dto=bridge_task_dto
    )
