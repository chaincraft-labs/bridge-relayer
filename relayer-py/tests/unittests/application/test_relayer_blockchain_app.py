from unittest.mock import patch
import pytest

from web3.datastructures import AttributeDict

from src.relayer.domain.relayer import (
    EventDTO
)
from src.relayer.application.relayer_blockchain import (
    ManageEventFromBlockchain,
    RegisterEvent,
)
from src.relayer.provider.mock_relayer_blockchain_web3 import (
    MockRelayerBlockchainProvider
)
from src.relayer.provider.mock_relayer_register_pika import (
    MockRelayerRegisterEvent,
)
from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO,
)
from tests.conftest import DATA_TEST


PATH = 'src.relayer.application.relayer_blockchain.ManageEventFromBlockchain'


# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture
def blockchain_provider(
    request
):
    # parameters for MockChainProvider
    # event, name, exception 
    marker = request.node.get_closest_marker("relayer_provider_data")                
    return MockRelayerBlockchainProvider(**marker.kwargs)


@pytest.fixture
def register_provider(
    request
):
    # parameters for MockChainProvider
    # event, name, exception 
    marker = request.node.get_closest_marker("relayer_provider_data")                
    return MockRelayerRegisterProvider(**marker.kwargs)

    
@pytest.fixture
def manage_event_from_blockchain(
    blockchain_provider,
    register_provider
):
    return ManageEventFromBlockchain(
        relayer_blockchain_provider=blockchain_provider,
        relayer_register_provider=register_provider,
        chain_id=123,
        verbose=False
    )
    
@pytest.fixture
def event_dto():
    return EventDTO(
        name=DATA_TEST.EVENT_SAMPLE.event, # type: ignore
        data=DATA_TEST.EVENT_SAMPLE.args , # type: ignore
    )

@pytest.fixture
def relayer_register_config_dto():
    """A RelayerRegisterEventConfigDTO instance."""
    return RelayerRegisterEventConfigDTO(
        host=DATA_TEST.REGISTER_CONFIG['host'], # type: ignore
        port=DATA_TEST.REGISTER_CONFIG['port'], # type: ignore
        user=DATA_TEST.REGISTER_CONFIG['user'], # type: ignore
    )

@pytest.fixture
def relayer_register_event_provider(
    relayer_register_config_dto
):
    return MockRelayerRegisterProvider(
        register_config_dto=relayer_register_config_dto
    )

@pytest.fixture
def register_event_app(
    relayer_register_event_provider
):
    return RegisterEvent(
        relayer_register_provider=relayer_register_event_provider
    )


class TestManageEventFromBlockchain:
    """Test ManageEventFromBlockchain."""

    # -------------------------------------------------------
    # T E S T S
    # -------------------------------------------------------
    @pytest.mark.relayer_provider_data
    def test_watch_event_from_blockchain_init_instance(
        self, 
        manage_event_from_blockchain,
        blockchain_provider,
        relayer_blockchain_config_dto
    ):
        """
            Test WatchEventFromChain that has access to methods defined in \
            interface IRelayerEvent.
        """
        app = manage_event_from_blockchain
        
        assert app.rb_provider == blockchain_provider
        assert app.rbc_dto == relayer_blockchain_config_dto
    
    @pytest.mark.relayer_provider_data
    def test_manage_event_from_blockchain_call_success(
        self,
        manage_event_from_blockchain
    ):
        """Test __call__ that has been called once."""
        app = manage_event_from_blockchain
        with patch(f"{PATH}.__call__") as mock_call:
            app()
            mock_call.assert_called_once()  
        
    @pytest.mark.relayer_provider_data
    def test_manage_event_from_blockchain_listen_events_call_success(
        self, 
        manage_event_from_blockchain
    ):
        """Test listen_events that has been called once."""
        with patch(f"{PATH}.listen_events") as mock_listen_events:
            app = manage_event_from_blockchain
            app.listen_events()
            mock_listen_events.assert_called_once()
    
    @pytest.mark.relayer_provider_data
    def test__convert_data_to_bytes_that_return_data_as_bytes(
        self,
        manage_event_from_blockchain,
        event_dto
    ):
        """Test _convert_data_to_bytes that convert data as bytes format."""
        app = manage_event_from_blockchain
        new_event_dto = app._convert_data_to_bytes(event_dto)
        assert isinstance(new_event_dto.data, bytes)        

    @pytest.mark.relayer_provider_data
    def test__handle_event_receive_event(
        self,
        manage_event_from_blockchain,
        event_dto
    ):
        """Test _handle_event that has been called with params."""
        with patch(f"{PATH}._handle_event") as mock__handle_events:
            app = manage_event_from_blockchain
            app._handle_event(event_dto)
            mock__handle_events.assert_called_with(event_dto)
            
    @pytest.mark.relayer_provider_data
    def test__handle_event_returns_event_dto_with_data_updated(
        self,
        manage_event_from_blockchain,
        event_dto
    ):
        """Test _handle_event that has been called with params."""
        app = manage_event_from_blockchain
        new_event_dto = app._handle_event(event_dto)
        assert isinstance(new_event_dto.data, bytes)
        
        
class TestRegisterEvent:
    """"""
    
    def test_register_event_instantiate(
        self,
        register_event_app,
        relayer_register_event_provider
    ):
        """Test RegisterEvent that is instantiate successfully with provider."""
        app = register_event_app
        assert app.rre_provider == relayer_register_event_provider
        
    def test__create_queue_name_from_event(
        self,
        register_event_app,
        event_dto
    ):
        """"""
        chain_id_source = 777
        chain_id_target = 222
        queue_name_expected = f"{event_dto.name}.{chain_id_source}.{chain_id_target}"
        app = register_event_app
        queue_name = app._create_queue_name_from_event(
            event_dto, chain_id_source, chain_id_target)
        assert queue_name == queue_name_expected
        