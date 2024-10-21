import pytest
from datetime import datetime, timezone
from src.relayer.domain.event_db import (
    EventTxDataDTO,
    EventTxDTO,
    EventDataDTO,
    EventDTO,
    EventsDTO,
    EventScanDTO,
    BridgeTaskDTO,
    BridgeTaskActionDTO,
    BridgeTaskTxResult
)


from tests.conftest import EVENT_DATA_SAMPLE as event_data


@pytest.fixture
def event_dto():
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


@pytest.fixture
def event_tx_data_dto():
    return EventTxDataDTO(
        event_name="Transfer",
        from_="0x0000000000000000000000000000000000000000",
        to="0x0000000000000000000000000000000000000000",
        chain_id_from=1337,
        chain_id_to=440,
        token_name="ethereum",
        amount=1000000000000000,
        nonce=20,
        signature_str="0x0000000000000000000000000000000000000000",
        signature_bytes=b'\x00' * 20,
        operation_hash_str="0x0000000000000000000000000000000000000000",
        operation_hash_bytes=b'\x00' * 20,
        block_step=14836,
        block_datetime=datetime.now(timezone.utc)
    )

@pytest.fixture
def event_tx_dto(event_tx_data_dto):
    return EventTxDTO(
        chain_id=1,
        block_number=100,
        tx_hash="0xabc123",
        log_index=0,
        data=event_tx_data_dto
    )


@pytest.fixture
def bridge_task_dto():
    return BridgeTaskDTO(
        chain_id=1,
        block_number=100,
        tx_hash="0xabc123",
        log_index=0,
        operation_hash="0xdef456",
        event_name="Transfer",
        status="Pending",
        datetime=datetime.now(timezone.utc)
    )

@pytest.fixture
def bridge_task_action_dto():
    return BridgeTaskActionDTO(
        operation_hash="0xdef456",
        func_name="transfer",
        params={"from": "0x0000000000000000000000000000000000000000"}
    )

@pytest.fixture
def bridge_task_tx_result():
    return BridgeTaskTxResult(
        tx_hash="0xabc123",
        block_hash="0xdef456",
        block_number=100,
        gas_used=21000,
        status=1
    )

# ------------------ EventTxDataDTO ---------------------------------------
def test_event_tx_data_dto_as_key(event_tx_data_dto):
    expected_key = (
        f"{event_tx_data_dto.operation_hash_str}-{event_tx_data_dto.event_name}"
    )
    assert event_tx_data_dto.as_key() == expected_key


def test_event_tx_data_dto_raw_params(event_tx_data_dto):
    expected_raw_params = {
        "from": event_tx_data_dto.from_,
        "to": event_tx_data_dto.to,
        "chainIdFrom": event_tx_data_dto.chain_id_from,
        "chainIdTo": event_tx_data_dto.chain_id_to,
        "tokenName": event_tx_data_dto.token_name,
        "amount": event_tx_data_dto.amount,
        "nonce": event_tx_data_dto.nonce,
        "signature": event_tx_data_dto.signature_bytes,
    }
    assert event_tx_data_dto.raw_params() == expected_raw_params


def test_event_tx_data_dto_params(event_tx_data_dto):
    expected_params = {
        "from": event_tx_data_dto.from_,
        "to": event_tx_data_dto.to,
        "chainIdFrom": event_tx_data_dto.chain_id_from,
        "chainIdTo": event_tx_data_dto.chain_id_to,
        "tokenName": event_tx_data_dto.token_name,
        "amount": event_tx_data_dto.amount,
        "nonce": event_tx_data_dto.nonce,
        "signature": event_tx_data_dto.signature_str,
    }
    assert event_tx_data_dto.params() == expected_params

# ------------------ EventTxDTO ---------------------------------------
def test_event_tx_dto_as_key(event_tx_dto):
    expected_key = (
        f"{event_tx_dto.chain_id}-{event_tx_dto.block_number}-"
        f"{event_tx_dto.tx_hash}-{event_tx_dto.log_index}"
    )
    assert event_tx_dto.as_key() == expected_key


# ------------------ EventDTO ---------------------------------------
def test_events_dto(event_dto):
    expected_key = (
        f"{event_dto.block_number}-{event_dto.tx_hash}-{event_dto.log_index}"
    )
    events_dto_instance = EventsDTO(
        event_datas=[event_dto], 
        end_block=100
    )
    assert events_dto_instance.end_block == 100
    assert len(events_dto_instance.event_datas) == 1
    assert events_dto_instance.event_datas[0].tx_hash == event_dto.tx_hash
    assert events_dto_instance.event_datas[0].as_key() == expected_key

# ------------------ BridgeTaskDTO ---------------------------------------
def test_bridge_task_dto_as_key(bridge_task_dto):
    expected_key = (
        f"{bridge_task_dto.operation_hash}-{bridge_task_dto.event_name}"
    )
    assert bridge_task_dto.as_key() == expected_key


def test_bridge_task_dto_as_id(bridge_task_dto):
    expected_id = (
        f"{bridge_task_dto.block_number}-{bridge_task_dto.tx_hash}-"
        f"{bridge_task_dto.log_index}"
    )
    assert bridge_task_dto.as_id() == expected_id


#  ------------------ BridgeTaskActionDTO ---------------------------------------
def test_bridge_task_action_dto(bridge_task_action_dto):
    assert bridge_task_action_dto.operation_hash == "0xdef456"
    assert bridge_task_action_dto.func_name == "transfer"
    assert bridge_task_action_dto.params == {
        "from": "0x0000000000000000000000000000000000000000"
    }


# ------------------ BridgeTaskTxResult ---------------------------------------
def test_bridge_task_tx_result(bridge_task_tx_result):
    assert bridge_task_tx_result.tx_hash == "0xabc123"
    assert bridge_task_tx_result.block_hash == "0xdef456"
    assert bridge_task_tx_result.block_number == 100
    assert bridge_task_tx_result.gas_used == 21000
    assert bridge_task_tx_result.status == 1


# ------------- EventScanDTO -----------------------------------------
def test_event_scan_dto(event_dto):
    events = []
    for i in range(10):
        event_dto.block_number = i
        events.append(event_dto)

    event_scan_dto = EventScanDTO(events=events, chunks_scanned=10)
    event_scan_dto.events = events
    event_scan_dto.chunks_scanned = 10

def test_event_data_dto():
    event_data_dto = EventDataDTO(
        from_="0x0000000000000000000000000000000000000000",
        to="0x0000000000000000000000000000000000000000",
        chain_id_from=1337,
        chain_id_to=440,
        token_name="ethereum",
        amount=1000000000000000,
        nonce=20,
        signature_str="0x0000000000000000000000000000000000000000",
        signature_bytes=b'\x00' * 20,
        operation_hash_str="0x0000000000000000000000000000000000000000",
        operation_hash_bytes=b'\x00' * 20,
        block_step=14836
    )
    assert event_data_dto.raw_params() == {
        "from": event_data_dto.from_,
        "to": event_data_dto.to,
        "chainIdFrom": event_data_dto.chain_id_from,
        "chainIdTo": event_data_dto.chain_id_to,
        "tokenName": event_data_dto.token_name,
        "amount": event_data_dto.amount,
        "nonce": event_data_dto.nonce,
        "signature": event_data_dto.signature_bytes,
    }

    assert event_data_dto.params() == {
        "from": event_data_dto.from_,
        "to": event_data_dto.to,
        "chainIdFrom": event_data_dto.chain_id_from,
        "chainIdTo": event_data_dto.chain_id_to,
        "tokenName": event_data_dto.token_name,
        "amount": event_data_dto.amount,
        "nonce": event_data_dto.nonce,
        "signature": event_data_dto.signature_str,
    }

