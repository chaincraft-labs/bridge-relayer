import logging
import shutil
from hexbytes import HexBytes
import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

from web3.datastructures import AttributeDict

from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO
)
from src.relayer.provider.relayer_event_storage import EventDataStoreToFile, HexJsonEncoder


# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
PATH_APP = 'src.relayer.provider.relayer_event_storage'
SAMPLE_EVENT_DATAS_DTO: EventDatasDTO = EventDatasDTO(
    event_datas=[
        EventDataDTO(
            block_number=14836, 
            tx_hash='0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd', 
            log_index=0, 
            event={
                'args': {
                    'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4', 
                    'params': {
                        'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'chainIdFrom': 440, 
                        'chainIdTo': 1337, 
                        'tokenName': 'allfeat', 
                        'amount': 1000000000000000, 
                        'nonce': 3, 
                        'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
                    }, 
                    'blockStep': 14836
                }, 
                'event': 'OperationCreated', 
                'logIndex': 0, 
                'transactionIndex': 0, 
                'transactionHash': 
                HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'), 
                'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
                'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'), 
                'blockNumber': 14836
            },
            block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810)
        ), 
        EventDataDTO(
            block_number=14840, 
            tx_hash='0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962', 
            log_index=0, 
            event={
                'args': {
                    'operationHash': b"\xbb1@\xd3lU\x8a\xe7\xc7\xfd2o\xd3\xc4\x94\x84\x0c\xf3~eN'`\x03x]\x8f\xbd\xad\x02\xb8\xa1", 
                    'params': {
                        'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'chainIdFrom': 440, 
                        'chainIdTo': 1337, 
                        'tokenName': 'allfeat', 
                        'amount': 1000000000000000, 
                        'nonce': 4, 
                        'signature': b'\x8b\xa2\xd0;\xc2\x89\xb9f\xfb\xf5SZ\xca\x19>`cfT\xe58kvW\xb54f\xfeU\xcd\xb8\x1dB\xed\x1f1J\x86\x16\x0e\xf6(\xf5\xdb\xd4\x07qJ\x9b:I\x10\x0b\xd0Pq\x9aQ\xc8w\xd0\x9fn\xcd\x1c'
                    }, 
                    'blockStep': 14840
                }, 
                'event': 'OperationCreated', 
                'logIndex': 0, 
                'transactionIndex': 0, 
                'transactionHash': HexBytes('0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962'), 
                'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
                'blockHash': HexBytes('0xa776cd94ee4ba4e309d85636bace1831592dbb96d61658895caae9d7d3ec8756'), 
                'blockNumber': 14840
            }, 
            block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810)
        )
    ], 
    end_block=14840,
    end_block_timestamp=datetime(2024, 8, 7, 15, 9, 14, 607810)
)

@pytest.fixture(autouse=True)
def disable_logging():
    # Disable logging during tests
    logging.disable(logging.CRITICAL)
    yield
    # Enable loggin after tests
    logging.disable(logging.NOTSET)

@pytest.fixture
def setup_and_teardown():
    test_dir = Path("test_dir")
    test_dir.mkdir(exist_ok=True)
    test_fname = test_dir / "test_file.json"

    with patch(f"{PATH_APP}.EventDataStoreToFile.get_file_path", return_value=test_fname):
        instance = EventDataStoreToFile(chain_id=1)

        yield instance

    # Clean up
    shutil.rmtree(test_dir)

@pytest.fixture(scope="function")
def event_datas():
    data = SAMPLE_EVENT_DATAS_DTO
    return data


# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------
def test_init(setup_and_teardown):
    """
        Test instance at init that set the atrributes
    """
    instance = setup_and_teardown
    
    assert instance.chain_id == '1'
    assert instance.fname == "1-events-scanner.json"
    assert instance.path.name == "data"
    assert instance.state == {}

def test_get_file_path():
    """
        Test get_file_path that returns the path + filename
    """
    instance = EventDataStoreToFile(chain_id=1)
    expected_path = instance.path / instance.fname

    assert instance.get_file_path() == expected_path

def test_init_method():
    """
        Test init that create a dict to init the struct for events
    """
    instance = EventDataStoreToFile(chain_id=1)
    instance.init()

    assert instance.state[instance.chain_id] == {
        "last_scanned_block": 0,
        "blocks": {},
    }

def test_commit_success(setup_and_teardown):
    """
        Test commit that create and load the file
    """
    instance = setup_and_teardown
    instance.commit()
    fname = instance.get_file_path()
    with open(fname, "rt") as f:
        data = json.load(f)

    assert fname.exists()
    assert data == instance.state

def test_commit_dir_already_exists(setup_and_teardown):
    """
        Test commit that able to manage a file even though the dir already exist
    """
    app = setup_and_teardown
    app.state = {"1": {"last_scanned_block": 10, "blocks": {}}}
    fname = app.get_file_path()
    fname.parent.mkdir(parents=True, exist_ok=True)
    app.commit()

    with open(fname, "rt") as f:
        data = json.load(f)
    
    assert fname.exists()
    assert data == app.state

@patch("builtins.open", new_callable=mock_open, read_data='{"1": {"last_scanned_block": 10, "blocks": {}}}')
def test_read_events(mock_file, setup_and_teardown):
    """
        Test read_events that returns the state even though the state is new
    """
    app = setup_and_teardown
    events = app.read_events()

    assert app.state == events == {
        "1": {"last_scanned_block": 10, "blocks": {}}
    }

@patch("builtins.open", new_callable=mock_open, read_data='')
def test_read_events_from_file_empty(mock_file, setup_and_teardown):
    """
        Test read_events that returns the state even though the state is empty
    """
    app = setup_and_teardown
    events = app.read_events()

    assert app.state == events == {
        app.chain_id: {
            "last_scanned_block": 0,
            "blocks": {},
        }
    }

@patch("builtins.open", new_callable=mock_open, read_data='invalid json')
def test_load_event_from_file_invalid_json(mock_file, setup_and_teardown):
    """
        Test read_events that returns the state even though the state is invalid
    """
    app = setup_and_teardown
    events = app.read_events()
    
    assert app.state == events == {
        app.chain_id: {
            "last_scanned_block": 0,
            "blocks": {},
        }
    }

def test_save_event_success(setup_and_teardown, event_datas):
    """
        Test save_event that save an event data to the state
    """
    app = setup_and_teardown
    events = app.read_events()
    event = event_datas.event_datas[0]
    
    # before saving event
    assert app.state == events == {
        "1": {
            "last_scanned_block": 0,
            "blocks": {}
        }
    }
    app.save_event(event)
    # after saving event
    assert app.state == {
        "1": {
            "last_scanned_block": 14836,
            "blocks": {
                "14836": {
                    "0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd": {
                        "0": {
                            "event": "OperationCreated",
                            "data": {
                                "operationHash": b"~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4",
                                "params": {
                                    "from": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "chainIdFrom": 440,
                                    "chainIdTo": 1337,
                                    "tokenName": "allfeat",
                                    "amount": 1000000000000000,
                                    "nonce": 3,
                                    "signature": b"\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c",
                                },
                                "blockStep": 14836,
                            },
                            "timestamp": "2024-08-07T15:09:14.607810",
                        }
                    }
                }
            },
        }
    }

def test_save_events(setup_and_teardown, event_datas):
    """
        Test save_events that save a list of event data dto to the state
    """
    app = setup_and_teardown
    state_events = app.read_events()
    events = event_datas.event_datas

    # before saving events
    assert app.state == state_events == {
        "1": {
            "last_scanned_block": 0,
            "blocks": {}
        }
    }
    app.save_events(events=events)
    # after saving events
    assert app.state == {
        "1": {
            "last_scanned_block": 14840,
            "blocks": {
                "14836": {
                    "0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd": {
                        "0": {
                            "event": "OperationCreated",
                            "data": {
                                "operationHash": b"~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4",
                                "params": {
                                    "from": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "chainIdFrom": 440,
                                    "chainIdTo": 1337,
                                    "tokenName": "allfeat",
                                    "amount": 1000000000000000,
                                    "nonce": 3,
                                    "signature": b"\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c",
                                },
                                "blockStep": 14836,
                            },
                            "timestamp": "2024-08-07T15:09:14.607810",
                        }
                    }
                },
                "14840": {
                    "0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962": {
                        "0": {
                            "event": "OperationCreated",
                            "data": {
                                "operationHash": b"\xbb1@\xd3lU\x8a\xe7\xc7\xfd2o\xd3\xc4\x94\x84\x0c\xf3~eN'`\x03x]\x8f\xbd\xad\x02\xb8\xa1",
                                "params": {
                                    "from": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                    "chainIdFrom": 440,
                                    "chainIdTo": 1337,
                                    "tokenName": "allfeat",
                                    "amount": 1000000000000000,
                                    "nonce": 4,
                                    "signature": b"\x8b\xa2\xd0;\xc2\x89\xb9f\xfb\xf5SZ\xca\x19>`cfT\xe58kvW\xb54f\xfeU\xcd\xb8\x1dB\xed\x1f1J\x86\x16\x0e\xf6(\xf5\xdb\xd4\x07qJ\x9b:I\x10\x0b\xd0Pq\x9aQ\xc8w\xd0\x9fn\xcd\x1c",
                                },
                                "blockStep": 14840,
                            },
                            "timestamp": "2024-08-07T15:09:14.607810",
                        }
                    }
                },
            },
        }
    }

def test_get_last_scanned_block_no_events(setup_and_teardown):
    """
        Test get_last_scanned_block that returns the last block scanned.
        As in this test there are no event, last scanned block = 0 
    """
    app = setup_and_teardown
    app.read_events()
    block_number = app.get_last_scanned_block()

    assert block_number == 0

def test_get_last_scanned_block_with_events(setup_and_teardown, event_datas):
    """
        Test get_last_scanned_block that returns the last block scanned.
        As in this test there are events, last scanned block = 14840
    """
    app = setup_and_teardown
    app.read_events()
    events = event_datas.event_datas
    app.save_events(events=events)
    block_number = app.get_last_scanned_block()

    assert block_number == 14840

def test_delete_event(setup_and_teardown):
    """
        Test delete_event that delete the last 'n' blocks in the state.
        In this test, we generate 100 / 3 events with:
          first event block = 0
          second event block = 3
          last event block = 99
          With since_block = 10, we delete 99, 96, 93, 90 blocks
          last block number become 87
    """
    app = setup_and_teardown
    app.read_events()
    events = EventDatasDTO(
        event_datas=[],
        end_block=0,
        end_block_timestamp=datetime(2024, 8, 7, 15, 9, 14, 607810)
    )
    for block_number in range(0, 100, 3):
        events.event_datas.append(EventDataDTO(
            block_number=block_number, 
            tx_hash='0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd', 
            log_index=0, 
            event={
                'args': {
                    'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4', 
                    'params': {
                        'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'chainIdFrom': 440, 
                        'chainIdTo': 1337, 
                        'tokenName': 'allfeat', 
                        'amount': 1000000000000000, 
                        'nonce': 3, 
                        'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
                    }, 
                    'blockStep': 14836
                }, 
                'event': 'OperationCreated', 
                'logIndex': 0, 
                'transactionIndex': 0, 
                'transactionHash': 
                HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'), 
                'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
                'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'), 
                'blockNumber': block_number
            },
            block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810)
        ))

    app.save_events(events=events.event_datas)
    block_number = app.get_last_scanned_block()

    since_block = 10 # delete the last 6 blocks 
    app.delete_event(since_block=since_block)
    new_block_number = app.get_last_scanned_block()

    assert block_number == 99
    assert new_block_number == 87
    assert app.state[app.chain_id]['blocks'].get("99", None) is None

def test_delete_event_with_only_one_block(setup_and_teardown):
    """
        Test delete_event that delete the last 'n' blocks in the state.
        In this test, we generate 100 / 3 events with:
          first event block = 0
          second event block = 3
          last event block = 99
          With since_block = 10, we delete 99, 96, 93, 90 blocks
          last block number become 87
    """
    app = setup_and_teardown
    app.read_events()
    events = EventDatasDTO(
        event_datas=[],
        end_block=0,
        end_block_timestamp=datetime(2024, 8, 7, 15, 9, 14, 607810)
    )
    for block_number in range(5):
        events.event_datas.append(EventDataDTO(
            block_number=block_number, 
            tx_hash='0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd', 
            log_index=0, 
            event={
                'args': {
                    'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4', 
                    'params': {
                        'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 
                        'chainIdFrom': 440, 
                        'chainIdTo': 1337, 
                        'tokenName': 'allfeat', 
                        'amount': 1000000000000000, 
                        'nonce': 3, 
                        'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
                    }, 
                    'blockStep': 14836
                }, 
                'event': 'OperationCreated', 
                'logIndex': 0, 
                'transactionIndex': 0, 
                'transactionHash': 
                HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'), 
                'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
                'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'), 
                'blockNumber': block_number
            },
            block_datetime=datetime(2024, 8, 7, 15, 9, 14, 607810)
        ))

    app.save_events(events=events.event_datas)
    block_number = app.get_last_scanned_block()

    since_block = 10 # delete the last 6 blocks 
    app.delete_event(since_block=since_block)
    new_block_number = app.get_last_scanned_block()

    assert block_number == 4
    assert new_block_number == 4
    assert app.state[app.chain_id]['blocks'].get("4", None) is None
    assert app.state[app.chain_id]['blocks'] == {}


def test_hex_json_encoder_hex_bytes():
    """
        Test HexJsonEncoder that encode hex_bytes type
    """
    encoder = HexJsonEncoder()
    hex_bytes = HexBytes(b'\x01\x02\x03\x04')
    result = encoder.default(hex_bytes)
    assert result == '0x01020304'

def test_hex_json_encoder_bytes():
    """
        Test HexJsonEncoder that encode byte_data type
    """
    encoder = HexJsonEncoder()
    byte_data = b'\x01\x02\x03\x04'
    result = encoder.default(byte_data)
    assert result == '01020304'

def test_hex_json_encoder_attribute_dict():
    """
        Test HexJsonEncoder that encode attr_dict type
    """
    encoder = HexJsonEncoder()
    attr_dict = AttributeDict({'key': 'value'})
    result = encoder.default(attr_dict)
    assert result == {'key': 'value'}

def test_hex_json_encoder_other_types():
    """
        Test HexJsonEncoder that encode dict type
    """
    encoder = HexJsonEncoder()
    dict_obj = {'key': 'value'}
    result = encoder.default(dict_obj)
    assert result == dict_obj

def test_hex_json_encoder_serialization():
    """
        Test HexJsonEncoder that serialize a data object
    """
    data = {
        'hex_bytes': HexBytes(b'\x01\x02\x03\x04'),
        'bytes': b'\x01\x02\x03\x04',
        'attr_dict': AttributeDict({'key': 'value'}),
        'other': {'key': 'value'}
    }
    json_str = json.dumps(data, cls=HexJsonEncoder)
    expected_json_str = json.dumps({
        'hex_bytes': '0x01020304',
        'bytes': '01020304',
        'attr_dict': {'key': 'value'},
        'other': {'key': 'value'}
    })
    assert json_str == expected_json_str
