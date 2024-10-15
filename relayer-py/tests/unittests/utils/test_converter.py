from datetime import datetime
import pytest
from io import BytesIO

from src.relayer.domain.event_db import EventDTO, EventDataDTO
from src.utils.converter import (
    bytes_to_hex,
    hex_to_bytes,
    to_bytes, 
    from_bytes,
    _serialize_data
)

from tests.conftest import EVENT_DATA_SAMPLE as event_data


@pytest.fixture
def example_event_dto():
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

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_serialize_data_returns_bytesio(example_event_dto):
    """
        Test _serialize_data that returns a BytesIO object regardless
        if input data is an EventDTO or a dict
    """
    event_data_dto_to_bytes = _serialize_data(example_event_dto)
    event_data_dict_to_bytes = _serialize_data(example_event_dto)
    assert isinstance(event_data_dto_to_bytes, BytesIO)
    assert isinstance(event_data_dict_to_bytes, BytesIO)

def test_to_bytes(example_event_dto):
    """
        Test to_bytes that convert an EventDTO or a dict to a bytes object
    """
    event_data_dto_bytes = to_bytes(example_event_dto)
    event_data_dict_bytes = to_bytes(example_event_dto)
    assert isinstance(event_data_dto_bytes, bytes)
    assert isinstance(event_data_dict_bytes, bytes)

def test_from_bytes(example_event_dto):
    """
        Test from_bytes that convert a bytes object to a dict
    """
    event_data_bytes = to_bytes(example_event_dto)
    event_data_dict_bytes = to_bytes(example_event_dto)

    event_data_result = from_bytes(event_data_bytes)
    event_data_dict_result = from_bytes(event_data_dict_bytes)

    assert event_data_result == example_event_dto
    assert event_data_dict_result == example_event_dto


def test_hex_to_bytes_success():
    """
        Test hex_to_bytes that convert a hex string to a bytes object
    """
    hex_str = '0x01020304'
    assert hex_to_bytes(hex_str) == b'\x01\x02\x03\x04'

def test_bytes_to_hex_success():
    """
        Test bytes_to_hex that convert a bytes object to a hex string
    """
    bytes_hex = b'\x01\x02\x03\x04'
    assert bytes_to_hex(bytes_hex) == '0x01020304'
