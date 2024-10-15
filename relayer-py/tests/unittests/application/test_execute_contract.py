import logging
from unittest.mock import MagicMock
import pytest

from src.relayer.domain.event_db import BridgeTaskActionDTO, BridgeTaskTxResult
from src.relayer.application.execute_contracts import ExecuteContracts
from src.relayer.provider.mock_relayer_blockchain_web3 import (
    RelayerBlockchainProvider
)
from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.domain.exception import (
    RelayerBlockchainFailedExecuteSmartContract,
)
from tests.conftest import EVENT_DATA_SAMPLE as event_data

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
def blockchain_provider():
    return RelayerBlockchainProvider


@pytest.fixture
def example_bridge_task_action():
    """Create an example bridge task."""
    return BridgeTaskActionDTO(
        operation_hash="0x123456789",
        params=event_data.args['params'],
        func_name="func_name",
    )

@pytest.fixture(scope="function")
def execute_contract_task(blockchain_provider):
    return ExecuteContracts(blockchain_provider)

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


# -------------------------------------------------------
# init
# -------------------------------------------------------
def test_execute_contract_task_init(blockchain_provider):
    """Test ExecuteContracts init."""
    app = ExecuteContracts(
        relayer_blockchain_provider=blockchain_provider
    )
    assert app.blockchain_provider == blockchain_provider

# -------------------------------------------------------
# chain_connector
# -------------------------------------------------------
def test_chain_connector(execute_contract_task, blockchain_provider):
    """Test chain_connector."""
    blockchain_provider.connect_client = MagicMock()
    providers = set()
    for _ in range(5):
        providers.add(execute_contract_task.chain_connector(chain_id=123))

    blockchain_provider.connect_client.assert_called_with(chain_id=123)
    assert len(providers) == 1
    assert isinstance(list(providers)[0], RelayerBlockchainProvider)

# -------------------------------------------------------
# call_contract_func
# -------------------------------------------------------
def test_call_contract_func_print_err_with_failed_tx(
        execute_contract_task,
        blockchain_provider,
        example_bridge_task_action
):
    """
        Test call_contract_func that print an err with invalid transaction
        while executing smart contract task.
    """
    blockchain_provider.connect_client = MagicMock()
    blockchain_provider.call_contract_func = MagicMock()
    blockchain_provider.call_contract_func.side_effect = RelayerBlockchainFailedExecuteSmartContract("fake Tx exception")
    
    with pytest.raises(
        RelayerBlockchainFailedExecuteSmartContract,
        match="fake Tx exception"
    ):
        execute_contract_task.call_contract_func(
            chain_id=80002, 
            bridge_task_action_dto=example_bridge_task_action
        )


def test_call_contract_func_print_success_with_valid_tx(
        execute_contract_task,
        blockchain_provider,
        example_bridge_task_action
):
    """
        Test call_contract_func that print success with valid transaction
        while executing smart contract task.
    """
    blockchain_provider.connect_client = MagicMock()
    blockchain_provider.call_contract_func = MagicMock()
    blockchain_provider.call_contract_func.return_value = BridgeTaskTxResult(
        tx_hash="0x5555555555555555555555555555555555555555555555555555555555555555",
        block_hash="0x666666666666666666666666666666666666666666666666666666666666666",
        block_number=1,
        gas_used=1,
        status=1,
    )

    tx = execute_contract_task.call_contract_func(
        chain_id=80002, 
        bridge_task_action_dto=example_bridge_task_action
    )
    assert tx.tx_hash == "0x5555555555555555555555555555555555555555555555555555555555555555"
    assert isinstance(tx, BridgeTaskTxResult)

# -------------------------------------------------------
# __call__
# -------------------------------------------------------   
def test_call_that_call_contract_func(
    execute_contract_task,
    example_bridge_task_action
):
    """
        Test __call__ that execute call_contract_func function
    """
    execute_contract_task.call_contract_func = MagicMock()

    execute_contract_task(
        chain_id=80002, 
        bridge_task_action_dto=example_bridge_task_action
    )
    
    execute_contract_task.call_contract_func.assert_called_with(
        chain_id=80002,
        bridge_task_action_dto=example_bridge_task_action
    )
