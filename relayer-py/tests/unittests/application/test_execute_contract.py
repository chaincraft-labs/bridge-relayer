from unittest.mock import MagicMock
import pytest

from src.relayer.application.execute_contract import ExecuteContractTask

from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    EventDTO,
)
from src.relayer.provider.mock_relayer_blockchain_web3 import (
    MockRelayerBlockchainProvider
)

from tests.conftest import DATA_TEST

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
def event_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args , # type: ignore
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
        relayer_blockchain_provider=blockchain_provider,
        verbose=False
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_execute_contract_task_init(blockchain_provider):
    """Test ExecuteContractTask init."""
    app = ExecuteContractTask(
        relayer_blockchain_provider=blockchain_provider,
        verbose=False
    )
    assert app.rb_provider == blockchain_provider
    assert app.verbose is False

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
    app.print_log = MagicMock(side_effect=app.print_log)

    app.call_contract_func(
        chain_id=80002,
        bridge_task_dto=bridge_task_dto
    )

    app.print_log.assert_called_with("fail", (
        f"Transaction failed func_name={bridge_task_dto.func_name}' "
        f"error=fake Tx exception"
    ))

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
    app.print_log = MagicMock(side_effect=app.print_log)

    app.call_contract_func(
        chain_id=80002,
        bridge_task_dto=bridge_task_dto
    )

    app.print_log.assert_called_with("success", (
        f"Transaction success func_name={bridge_task_dto.func_name} "
        f"Transaction_hash={blockchain_provider.tx_hash}"
    ))

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
