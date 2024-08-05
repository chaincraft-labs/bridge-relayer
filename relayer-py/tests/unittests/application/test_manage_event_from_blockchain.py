import sys
from unittest.mock import MagicMock, patch
import pytest

from src.relayer.application.manage_event_from_blockchain import (
    ManageEventFromBlockchain
)
from src.relayer.domain.exception import BridgeRelayerListenEventFailed
from src.relayer.domain.relayer import (
    EventDTO,
    RegisterEventResult
)
from src.relayer.provider.mock_relayer_blockchain_web3 import (
    MockRelayerBlockchainProvider
)
from src.relayer.provider.mock_relayer_register_pika import (
    MockRelayerRegisterEvent,
)
from tests.conftest import DATA_TEST
from utils.converter import from_bytes


PATH = 'src.relayer.application.manage_event_from_blockchain'
PATH_MOCK_WEB3 = 'src.relayer.provider.mock_relayer_blockchain_web3'
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
def manage_event_from_blockchain(blockchain_provider, register_provider):
    return ManageEventFromBlockchain(
        relayer_blockchain_provider=blockchain_provider,
        relayer_register_provider=register_provider,
        chain_id=123,
        event_filters=EVENT_FILTERS,
        verbose=False
    )

@pytest.fixture(scope="function")
def event_dto():
    event = DATA_TEST.EVENT_SAMPLE.copy()
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args , # type: ignore
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

@pytest.mark.register_provider_data
def test_init_instance(blockchain_provider, register_provider):
    """
        Test ManageEventFromBlockchain that has access to methods
        defined in interface IRelayerEvent.
    """
    app = ManageEventFromBlockchain(
        relayer_blockchain_provider=blockchain_provider,
        relayer_register_provider=register_provider,
        chain_id=123,
        event_filters=EVENT_FILTERS,
        verbose=False
    )
    
    assert app.rb_provider == blockchain_provider
    assert app.rr_provider == register_provider
    assert app.chain_id ==  123
    assert app.event_filters == EVENT_FILTERS
    assert app.verbose is False
    assert app.register_config.host == 'localhost'
    assert app.register_config.port == 5672
    assert app.register_config.user == 'guest'
    assert app.register_config.password == 'guest'
    assert app.register_config.queue_name == 'bridge.relayer.dev'

@pytest.mark.register_provider_data
def test_call_success(manage_event_from_blockchain):
    """Test __call__ that has been called once."""
    app = manage_event_from_blockchain

    with patch(f"{PATH}.ManageEventFromBlockchain.__call__") as mock_call:
        app()
        mock_call.assert_called_once()

@pytest.mark.register_provider_data
def test_listen_events_call_success(manage_event_from_blockchain):
    """Test listen_events that has been called once."""
    with patch(f"{PATH}.ManageEventFromBlockchain.listen_events") as mock_listen_events:
        app = manage_event_from_blockchain
        app.listen_events()
        mock_listen_events.assert_called_once()

@pytest.mark.register_provider_data
def test_listen_events_has_been_called(manage_event_from_blockchain):
    """Test listen_events that has been called."""
    with patch(f"{PATH_MOCK_WEB3}.MockRelayerBlockchainProvider.listen_events") as mock_call:
        app = manage_event_from_blockchain
        app.listen_events()
        mock_call.assert_called()

@pytest.mark.relayer_provider_data(exception=Exception("fake exception"))
def test_listen_events_raise_exception(manage_event_from_blockchain):
    """Test listen_events that has been called."""
    with pytest.raises(BridgeRelayerListenEventFailed):
        app = manage_event_from_blockchain
        app.listen_events()

@pytest.mark.register_provider_data
def test_listen_events_has_been_called_from_call(manage_event_from_blockchain):
    """Test listen_events that has been called once."""
    with patch(f"{PATH_MOCK_WEB3}.MockRelayerBlockchainProvider.listen_events") as mock_call:
        app = manage_event_from_blockchain
        app()
        mock_call.assert_called()

@pytest.mark.register_provider_data
def test__convert_data_to_bytes_that_return_data_as_bytes(
    manage_event_from_blockchain,
    event_dto
):
    """
        Test _convert_data_to_bytes that convert event_dto object as 
        bytes format.
    """
    app = manage_event_from_blockchain
    event_dto_to_bytes = app._convert_data_to_bytes(event_dto)
    event_dto_from_bytes = from_bytes(event_dto_to_bytes)

    assert isinstance(event_dto_to_bytes, bytes)
    assert event_dto.name == event_dto_from_bytes.get("name")
    assert event_dto.data == event_dto_from_bytes.get("data")

@pytest.mark.register_provider_data
def test__handle_event_call_with_event_dto(
    manage_event_from_blockchain,
    event_dto
):
    """Test _handle_event that has been called with params."""
    with patch(f"{PATH}.ManageEventFromBlockchain._handle_event") as mock__handle_events:
        app = manage_event_from_blockchain
        app._handle_event(event_dto)
        mock__handle_events.assert_called_with(event_dto)
        
@pytest.mark.register_provider_data
def test__handle_event_register_event_with_event_dto_is_success(
    manage_event_from_blockchain,
    event_dto
):
    """Test _handle_event that has been called with params."""
    app = manage_event_from_blockchain
    result = app._handle_event(event_dto)
    assert isinstance(result, RegisterEventResult)
    assert result.ok is True
    
@pytest.mark.register_provider_data(exception=Exception("fake exception"))
def test__handle_event_register_event_with_event_dto_is_failed(
    manage_event_from_blockchain,
    event_dto
):
    """Test _handle_event that has been called with params."""
    app = manage_event_from_blockchain
    result = app._handle_event(event_dto)
    assert isinstance(result, RegisterEventResult)
    assert result.err == "fake exception"

def test_call_that_exit_on_KeyboardInterrupt(manage_event_from_blockchain):
    """
        Test __call__ that exit while receiving KeyboardInterrupt exception
    """
    app = manage_event_from_blockchain
    app.listen_events = MagicMock(side_effect=KeyboardInterrupt)
    sys.exit = MagicMock()
    app.print_log = MagicMock(side_effect=app.print_log)

    app()
    app.print_log.assert_called_with("emark", "Keyboard Interrupt")
    sys.exit.assert_called_once()

    