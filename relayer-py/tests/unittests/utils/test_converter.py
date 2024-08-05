import pytest
from io import BytesIO

from src.relayer.domain.relayer import EventDTO
from src.utils.converter import (
    to_bytes, 
    from_bytes,
    _serialize_data
)
from tests.conftest import DATA_TEST


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

def test_serialize_data_returns_bytesio(event_dto):
    """
        Test _serialize_data that returns a BytesIO object regardless
        if input data is an EventDTO or a dict
    """
    event_dto_to_bytes = _serialize_data(event_dto)
    event_dto_as_dict_to_bytes = _serialize_data(event_dto.as_dict())
    assert isinstance(event_dto_to_bytes, BytesIO)
    assert isinstance(event_dto_as_dict_to_bytes, BytesIO)

def test_to_bytes(event_dto):
    """
        Test to_bytes that convert an EventDTO or a dict to a bytes object
    """
    event_dto_bytes = to_bytes(event_dto)
    event_dto_as_dict_bytes = to_bytes(event_dto.as_dict())
    assert isinstance(event_dto_bytes, bytes)
    assert isinstance(event_dto_as_dict_bytes, bytes)

def test_from_bytes(event_dto):
    """
        Test from_bytes that convert a bytes object to a dict
    """
    event_dto_bytes = to_bytes(event_dto)
    event_dto_as_dict_bytes = to_bytes(event_dto.as_dict())

    event_dto_result = from_bytes(event_dto_bytes)
    event_dto_as_dict_result = from_bytes(event_dto_as_dict_bytes)

    assert isinstance(event_dto_result, dict)
    assert isinstance(event_dto_as_dict_result, dict)
