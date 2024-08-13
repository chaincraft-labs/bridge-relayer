import pytest

from src.relayer.application.register_event import RegisterEvent
from src.relayer.domain.relayer import (
    EventDTO,
    RegisterEventResult
)
from src.relayer.provider.mock_relayer_register_pika import (
    MockRelayerRegisterEvent,
)
from tests.conftest import DATA_TEST
from src.utils.converter import to_bytes


# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------

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
    block_key = f"{event.blockNumber}-{event.transactionHash.hex()}-{event.logIndex}"
    return EventDTO(
        name=event.event, # type: ignore
        data=event.args, # type: ignore
        block_key=block_key
    )


@pytest.fixture(scope="function")
def register_event(register_provider):
    return RegisterEvent(
        relayer_register_provider=register_provider,
        verbose=False
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

    
def test_register_event_instantiate(register_event, register_provider):
    """Test RegisterEvent that is instantiate successfully with provider."""
    app = register_event
    assert app.rr_provider == register_provider
    
def test_register_event_call_with_event_as_bytes_success(
    register_event, 
    event_dto
):
    """Test RegisterEvent.__call__ with event as argument is success."""
    event: bytes = to_bytes(event_dto)
    app = register_event
    result = app(event=event)
    assert isinstance(result, RegisterEventResult)
    assert result.ok is True

@pytest.mark.register_provider_data(exception=Exception("fake exception"))
def test_register_event_call_with_event_as_bytes_failed(
    register_event,
    event_dto
):
    """Test RegisterEvent.__call__ with event as argument is success."""
    event: bytes = to_bytes(event_dto)
    app = register_event
    result = app(event=event)
    assert isinstance(result, RegisterEventResult)
    assert result.err == "fake exception"
