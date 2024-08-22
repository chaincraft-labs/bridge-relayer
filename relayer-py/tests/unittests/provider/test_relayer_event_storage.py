import logging
import shutil
from hexbytes import HexBytes
import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

from web3.datastructures import AttributeDict

from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO
)
from src.relayer.provider.relayer_event_storage import (
    EventDataStoreToFile, 
    HexJsonEncoder,
)
from src.relayer.domain.exception import (
    EventDataStoreNoBlockToDelete,
    EventDataStoreRegisterFailed,
    EventDataStoreStateEmptyOrNotLoaded,
)

from tests.conftest import EVENT_TASKS


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
    chain_id = 111
    test_dir = Path("test_dir")
    test_dir.mkdir(exist_ok=True)
    test_fname = test_dir / f"{chain_id}-test_file.json"
    test_task_fname = test_dir / "task-event-test_file.json"

    with patch(f"{PATH_APP}.EventDataStoreToFile.get_file_path", return_value=test_fname), \
         patch(f"{PATH_APP}.EventDataStoreToFile.get_task_file_path", return_value=test_task_fname):
        instance = EventDataStoreToFile()
        instance.set_chain_id(chain_id=chain_id)

        yield instance

    # Clean up
    shutil.rmtree(test_dir)

@pytest.fixture(scope="function")
def event_datas():
    data = SAMPLE_EVENT_DATAS_DTO
    return data

@pytest.fixture
def event_tasks():
    event_tasks = EVENT_TASKS.copy()
    return event_tasks

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------
def test_init(setup_and_teardown):
    """
        Test instance at init that set the atrributes
    """
    instance = setup_and_teardown
    instance.set_chain_id(chain_id=111)
    
    assert instance.chain_id == '111'
    assert instance.fname == "111-events-scanner.json"
    assert instance.path.name == "data"
    assert instance.state == {}

def test_get_file_path():
    """
        Test get_file_path that returns the path + filename
    """
    instance = EventDataStoreToFile()
    instance.set_chain_id(chain_id=111)
    expected_path = instance.path / "111-events-scanner.json"

    assert instance._get_file_path() == expected_path

def test_get_task_file_path():
    """
        Test get_task_file_path that returns the path + filename
    """
    instance = EventDataStoreToFile()
    expected_path = instance.path / "events-operation.json"

    assert instance._get_task_file_path() == expected_path

def test_init_method():
    """
        Test init that create a dict to init the struct for events
    """
    instance = EventDataStoreToFile()
    instance.set_chain_id(chain_id=111)
    instance._init()

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

def test_commit_task_success(setup_and_teardown):
    """
        Test commit task that create and load the file
    """
    instance = setup_and_teardown
    instance.commit_task()
    task_fname = instance.get_task_file_path()
    with open(task_fname, "rt") as f:
        data = json.load(f)

    assert task_fname.exists()
    assert data == instance.state_task

def test_commit_dir_already_exists(setup_and_teardown):
    """
        Test commit that able to manage a file even though the dir already exist
    """
    app = setup_and_teardown
    app.state = {"111": {"last_scanned_block": 10, "blocks": {}}}
    fname = app.get_file_path()
    fname.parent.mkdir(parents=True, exist_ok=True)
    app.commit()

    with open(fname, "rt") as f:
        data = json.load(f)
    
    assert fname.exists()
    assert data == app.state

def test_commit_task_dir_already_exists(setup_and_teardown):
    """
        Test commit task that able to manage a file even though the dir already exist
    """
    app = setup_and_teardown
    app.state_task = {
        "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {
            "OperationCreated": {
                "chain_id": 1337,
                "block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0",
                "status": "completed"
            }
        }
    }
    task_fname = app.get_task_file_path()
    task_fname.parent.mkdir(parents=True, exist_ok=True)
    app.commit_task()

    with open(task_fname, "rt") as f:
        data = json.load(f)
    
    assert task_fname.exists()
    assert data == app.state_task

@patch("builtins.open", new_callable=mock_open, read_data='{"111": {"last_scanned_block": 10, "blocks": {}}}')
def test_read_events(mock_file, setup_and_teardown):
    """
        Test read_events that returns the state even
    """
    app = setup_and_teardown
    events = app.read_events()

    assert app.state == events == {
        "111": {"last_scanned_block": 10, "blocks": {}}
    }

@patch(
    "builtins.open", 
    new_callable=mock_open, 
    read_data='{"9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {"OperationCreated": {"chain_id": 1337,"block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0","status": "completed"}}}'
)
def test_read_event_tasks(mock_file, setup_and_teardown):
    """
        Test read_event_tasks that returns the state task
    """
    app = setup_and_teardown
    event_tasks = app.read_event_tasks()

    assert (
        app.state_task
        == event_tasks
        == {
            "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {
                "OperationCreated": {
                    "chain_id": 1337,
                    "block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0",
                    "status": "completed",
                }
            }
        }
    )

@patch("builtins.open", new_callable=mock_open, read_data='')
def test_read_events_from_file_is_empty(mock_file, setup_and_teardown):
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

@patch("builtins.open", new_callable=mock_open, read_data='')
def test_read_event_tasks_from_file_is_empty(mock_file, setup_and_teardown):
    """
        Test read_event_tasks that returns the state even though the state is empty
    """
    app = setup_and_teardown
    event_tasks = app.read_event_tasks()

    assert app.state_task == event_tasks == {}

@patch("builtins.open", new_callable=mock_open, read_data='invalid json')
def test_read_event_from_file_with_invalid_json(mock_file, setup_and_teardown):
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

@patch("builtins.open", new_callable=mock_open, read_data='invalid json')
def test_read_event_task_from_file_invalid_json(mock_file, setup_and_teardown):
    """
        Test read_event_tasks that returns the state even though the state is invalid
    """
    app = setup_and_teardown
    events = app.read_event_tasks()
    
    assert app.state_task == events == {}

def test_save_event_success(setup_and_teardown, event_datas):
    """
        Test save_event that save an event data to the state
    """
    app = setup_and_teardown
    events = app.read_events()
    event = event_datas.event_datas[0]
    
    # before saving event
    assert app.state == events == {
        "111": {
            "last_scanned_block": 0,
            "blocks": {}
        }
    }
    app.save_event(event)
    # after saving event
    assert app.state == {
        "111": {
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
        "111": {
            "last_scanned_block": 0,
            "blocks": {}
        }
    }
    app.save_events(events=events)
    # after saving events
    assert app.state == {
        "111": {
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

def test_save_event_task_success_new_event(setup_and_teardown):
    """
        Test save_event_task that save an event task to the state
    """
    app = setup_and_teardown
    app.commit_task = MagicMock()
    event_tasks = app.read_event_tasks()
    
    # before saving event
    assert app.state_task == event_tasks == {}

    operation_hash = "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd"
    event_name = "OperationCreated"
    chain_id = 111
    block_key = "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0"
    status = 'processing'
    app.save_event_task(
        chain_id=chain_id,
        block_key=block_key,
        operation_hash=operation_hash,
        event_name=event_name,
        status=status,
        auto_commit=True
    )
    # after saving event
    assert app.state_task == {
        "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {
            "OperationCreated": {
                "chain_id": 111,
                "block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0",
                "status": "processing"
            }
        }
    }
    app.commit_task.assert_called()

def test_save_event_task_success_update_event(setup_and_teardown):
    """
        Test save_event_task that save an event task to the state and update the status
    """
    app = setup_and_teardown
    app.commit_task = MagicMock()
    event_tasks = app.read_event_tasks()
    
    # before saving event
    assert app.state_task == event_tasks == {}

    operation_hash = "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd"
    event_name = "OperationCreated"
    chain_id = 111
    block_key = "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0"
    status = 'processing'
    app.save_event_task(
        chain_id=chain_id,
        block_key=block_key,
        operation_hash=operation_hash,
        event_name=event_name,
        status=status,
        auto_commit=True
    )

    status = 'completed'
    app.save_event_task(
        chain_id=chain_id,
        block_key=block_key,
        operation_hash=operation_hash,
        event_name=event_name,
        status=status,
        auto_commit=True
    )

    assert app.state_task == {
        "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {
            "OperationCreated": {
                "chain_id": 111,
                "block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0",
                "status": "completed"
            }
        }
    }
    app.commit_task.assert_called()

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

def test_delete_event_raise_exception_if_no_blocks_or_empty_state(
    setup_and_teardown
):
    """
        Test delete_event that returns 0 if no blocks.
    """
    app = setup_and_teardown
    # KeyError is raised because state = {}
    with pytest.raises(
        EventDataStoreNoBlockToDelete,
        match="No block to delete, state empty"
    ):
        app.delete_event(
            current_block=100,
            block_to_delete=10,
            auto_commit=True
        )
    # load state
    app.read_events()
    # StopIteration is raised because state does not have any blocks
    with pytest.raises(
        EventDataStoreNoBlockToDelete,
        match="No block to delete, state empty"
    ):
        app.delete_event(
            current_block=100,
            block_to_delete=10,
            auto_commit=True
        )

def test_delete_event_raise_exception_if_block_limit_greater_than_last_block_in_state(
    setup_and_teardown
):
    """
        Test delete_event that raises EventDataStoreNoBlockToDelete 
        if block_limit is greater than the last block in the state
        
        5 blocks in the state
        since_block = 6
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
    with pytest.raises(EventDataStoreNoBlockToDelete):
        app.delete_event(
            current_block=100,
            block_to_delete=10,
            auto_commit=True
        )

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

    app.commit = MagicMock()
    app.save_events(events=events.event_datas)
    block_number = app.get_last_scanned_block()
    app.delete_event(
        current_block=100,
        block_to_delete=10,
        auto_commit=True
    )
    new_block_number = app.get_last_scanned_block()

    assert block_number == 99
    assert new_block_number == 87
    assert app.state[app.chain_id]['blocks'].get("99", None) is None

def test_get_last_scanned_block_failed(setup_and_teardown):
    """
        Test get_last_scanned_block that raise an error if the state is empty
    """
    app = setup_and_teardown
    with pytest.raises(
        EventDataStoreStateEmptyOrNotLoaded,
        match="State empty or not loaded!"
    ):
        app.get_last_scanned_block()

def test_get_last_scanned_block_success(setup_and_teardown):
    """
        Test get_last_scanned_block that get the last scanned block
    """
    app = setup_and_teardown
    app.read_events()
    assert app.get_last_scanned_block() == 0

def test_set_last_scanned_block_failed(setup_and_teardown):
    """
        Test set_last_scanned_block that raise an error if the state is empty
    """
    app = setup_and_teardown
    with pytest.raises(
        EventDataStoreStateEmptyOrNotLoaded,
        match="State empty or not loaded!"
    ):
        app.set_last_scanned_block(block_numer=100)

def test_set_last_scanned_block_success(setup_and_teardown):
    """
        Test set_last_scanned_block that set the last scanned block
    """
    app = setup_and_teardown
    app.read_events()
    app.set_last_scanned_block(block_numer=100)
    assert app.get_last_scanned_block() == 100

def test_is_event_stored_return_false_if_event_not_in_state(
    setup_and_teardown, 
    event_datas
):
    """
        Test is_event_stored that returns false if event is not in the state
        same event
    """
    app = setup_and_teardown
    events = event_datas.event_datas
    app.read_events()
    app.save_events(events=events)
    assert app.is_event_stored(event_key="block_number-tx_hash-log_index") is False

def test_is_event_stored_return_true_if_event_in_state(
    setup_and_teardown, 
    event_datas
):
    """
        Test is_event_stored that returns True if event is in the state
        same event
    """
    app = setup_and_teardown
    events = event_datas.event_datas
    app.read_events()
    app.save_events(events=events)
    event_key = '14836-0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd-0'
    assert app.is_event_stored(event_key=event_key) is True

def test_set_event_as_registered_failed_if_state_empty_or_not_loaded(
    setup_and_teardown, 
):
    """
        Test set_event_as_registered that raise an error if state is empty or not loaded
    """
    app = setup_and_teardown
    event_key = '14836-0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd-0'

    with pytest.raises(EventDataStoreRegisterFailed):
        app.set_event_as_registered(event_key=event_key)

def test_set_event_as_registered_success(
    setup_and_teardown, 
    event_datas):
    """
        Test set_event_as_registered that raise an error if 
    """
    app = setup_and_teardown
    events = event_datas.event_datas
    app.commit = MagicMock()
    event_key = '14836-0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd-0'
    app.read_events()
    app.save_events(events=events)
    app.set_event_as_registered(event_key=event_key, auto_commit=True)

    app.commit.assert_called()
    assert app.state["111"]['blocks']['14836']['0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd']['0']['handled'] == 'registered'

def test_is_event_registered_return_false_if_event_not_registered(
    setup_and_teardown, 
):
    """
        Test is_event_registered that returns false if event is not in the state
    """
    app = setup_and_teardown
    app.read_events()
    assert app.is_event_registered(event_key="block_number-tx_hash-log_index") is False

def test_is_event_registered_return_true_if_event_is_registered(
    setup_and_teardown, 
    event_datas
):
    """
        Test is_event_registered that returns true if event is registered in the state
    """
    app = setup_and_teardown
    events = event_datas.event_datas
    event_key = '14836-0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd-0'
    app.read_events()
    app.save_events(events=events)
    app.set_event_as_registered(event_key=event_key)
    assert app.is_event_registered(event_key=event_key) is True

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
