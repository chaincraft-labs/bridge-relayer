from datetime import datetime
import logging
from unittest.mock import MagicMock, patch
from hexbytes import HexBytes
import pytest

from src.relayer.provider.mock_relayer_blockchain_web3_v2 import (
    MockRelayerBlockchainProvider
)
from src.relayer.provider.mock_relayer_register_pika import (
    MockRelayerRegisterEvent
)
from src.relayer.provider.mock_event_datastore_to_file import (
    MockEventDataStore
)
from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO,
    RelayerRegisterConfigDTO,
)
from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO,
    EventDatasScanDTO,
    EventDatasScanResult
)
from src.relayer.domain.relayer import (
    EventDTO
)
from src.relayer.application.manage_event_from_blockchain_v2 import (
    ManageEventFromBlockchain,
)

# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
PATH_APP = 'src.relayer.application.manage_event_from_blockchain_v2'
EVENT_FILTERS = ['FAKE_EVENT_NAME']

@pytest.fixture(autouse=True)
def disable_logging():
    # Disable logging during tests
    logging.disable(logging.CRITICAL)
    yield
    # Enable loggin after tests
    logging.disable(logging.NOTSET)

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
def event_datastore_provider(request):
    # parameters for MockEventDataStore
    # event, name, exception
    marker = request.node.get_closest_marker("event_store_data")
    if marker:
        return MockEventDataStore(**marker.kwargs)
    return MockEventDataStore()


@pytest.fixture(scope="function")
def register_config():
    return RelayerRegisterConfigDTO(
        host="localhost",
        port=5672,
        user="guest",
        password="guest",
        queue_name="bridge.relayer.dev",
    )

@pytest.fixture(scope="function")
def blockchain_config():
    config = RelayerBlockchainConfigDTO(
        chain_id=123, 
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=0,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        genesis_block=666, 
        abi=[{}], 
        client='middleware'
    )
    return config

@pytest.fixture(scope="function")
def manage_event_from_blockchain(
    blockchain_provider, 
    register_provider,
    event_datastore_provider,
    blockchain_config,
    register_config
):
    with patch(f'{PATH_APP}.get_blockchain_config'), \
         patch(f'{PATH_APP}.get_register_config'):
        app = ManageEventFromBlockchain(
            relayer_blockchain_provider=blockchain_provider,
            relayer_register_provider=register_provider,
            event_datastore_provider=event_datastore_provider,
            chain_id=123,
            event_filters=EVENT_FILTERS,
            min_scan_chunk_size=10,
            max_scan_chunk_size=10000,
            chunk_size_increase=2.0,
            log_level='info',
        )
    
        app.register_config = register_config
        app.blockchain_config = blockchain_config

    return app

@pytest.fixture(scope="function")
def event_datas():
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
    return SAMPLE_EVENT_DATAS_DTO

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

@pytest.mark.register_provider_data
def test_init_instance(
    blockchain_provider, 
    register_provider,
    event_datastore_provider,
    register_config
):
    """
        Test ManageEventFromBlockchain that has access to methods
        defined in interface IRelayerEvent.
    """
    with patch(f'{PATH_APP}.get_blockchain_config'), \
         patch(f'{PATH_APP}.get_register_config'):
        app = ManageEventFromBlockchain(
            relayer_blockchain_provider=blockchain_provider,
            relayer_register_provider=register_provider,
            event_datastore_provider=event_datastore_provider,
            chain_id=123,
            event_filters=EVENT_FILTERS,
            log_level='info',
        )

        app.register_config = register_config

    assert app.rb_provider == blockchain_provider
    assert app.rr_provider == register_provider
    assert app.evt_store == event_datastore_provider
    assert app.chain_id ==  123
    assert app.event_filters == EVENT_FILTERS
    assert app.log_level == 'info'
    assert app.register_config.host == 'localhost'
    assert app.register_config.port == 5672
    assert app.register_config.user == 'guest'
    assert app.register_config.password == 'guest'
    assert app.register_config.queue_name == 'bridge.relayer.dev'


@pytest.mark.parametrize('data, expected', [
    ({'event_found_count': 0, 'current_chuck_size': 20}, 40),
    ({'event_found_count': 0, 'current_chuck_size': 40}, 80),
    ({'event_found_count': 1, 'current_chuck_size': 20}, 10),
    ({'event_found_count': 10, 'current_chuck_size': 40}, 10),
])
def test_estimate_next_chunk_size_(manage_event_from_blockchain, data, expected):
    """
        Test estimate_next_chunk_size that returns the chunk size according to
        the number of event scanned.
        For each iteration, if no events have been retrieved, chunk size increase by chunk_size_increase
        For each iteration, if events have been retrieved, chunk size = min_scan_chunk_size

        with:
          chunk_size_increase = 2.0
          min_scan_chunk_size = 10
    """
    app = manage_event_from_blockchain
    chuck_size = app.estimate_next_chunk_size(
        current_chuck_size=data['current_chuck_size'],
        event_found_count=data['event_found_count'],
    )
    assert chuck_size == expected


def test_scan_success(
    blockchain_provider,
    manage_event_from_blockchain,
    event_datas,
):
    """
        Test scan that
    """
    app = manage_event_from_blockchain

    start_block = 14830
    end_block = 14840
    start_chunk_size = 20
    progress_callback = None
    with patch.object(blockchain_provider, 'scan', return_value=event_datas):
        # act
        event_datas_scan_result = app.scan(
            start_block=start_block,
            end_block=end_block,
            start_chunk_size=start_chunk_size,
            progress_callback=progress_callback,
        )
        all_event_datas = event_datas_scan_result.ok.event_datas
        total_chunks_scanned = event_datas_scan_result.ok.chunks_scanned

        # assert
        assert isinstance(event_datas_scan_result, EventDatasScanResult)
        assert isinstance(event_datas_scan_result.ok, EventDatasScanDTO)
        assert isinstance(all_event_datas[0], EventDataDTO)
        assert len(all_event_datas) == 2
        assert all_event_datas[0].block_datetime == event_datas.event_datas[0].block_datetime
        assert total_chunks_scanned == 1


def test_run_scan_with_progress_bar_render(
    blockchain_provider,
    manage_event_from_blockchain,
    event_datas,
):
    """
        Test run_scan_with_progress_bar_render that call scan and show 
        a progress bar until events have been scanned
    """
    app = manage_event_from_blockchain

    start_block = 14830
    end_block = 14840
    start_chunk_size = 20
    with patch.object(blockchain_provider, 'scan', return_value=event_datas):
        # act
        event_datas_scan_result = app.run_scan_with_progress_bar_render(
            start_block=start_block,
            end_block=end_block,
            start_chunk_size=start_chunk_size,
        )
        # assert
        all_event_datas = event_datas_scan_result.ok.event_datas
        total_chunks_scanned = event_datas_scan_result.ok.chunks_scanned

        assert isinstance(event_datas_scan_result, EventDatasScanResult)
        assert isinstance(event_datas_scan_result.ok, EventDatasScanDTO)
        assert isinstance(all_event_datas[0], EventDataDTO)
        assert len(all_event_datas) == 2
        assert all_event_datas[0].block_datetime == event_datas.event_datas[0].block_datetime
        assert total_chunks_scanned == 1


def test_create_event_dto(manage_event_from_blockchain, event_datas):
    """
        Test create_event_dto that returns an event_dto
    """
    app = manage_event_from_blockchain
    event_dto = app.create_event_dto(event_data=event_datas.event_datas[0])
    assert isinstance(event_dto, EventDTO)


def test_call_success(
    manage_event_from_blockchain, 
    event_datas,
    event_datastore_provider,
    register_provider
):
    """
        Test __call__
    """
    app = manage_event_from_blockchain
    
    all_event_datas = event_datas.event_datas
    total_chunks_scanned = 456
    event_datas_scan_result = EventDatasScanResult()
    end_block_timestamp=datetime(2024, 8, 7, 15, 9, 14, 607810)

    event_datas_scan_result.ok = EventDatasScanDTO(
        event_datas=all_event_datas,
        end_block_timestamp=end_block_timestamp,
        chunks_scanned=total_chunks_scanned
    )
    
    event_datastore_provider.save_event = MagicMock(
        side_effect=event_datastore_provider.save_event)
    
    register_provider.register_event = MagicMock(
        side_effect=register_provider.register_event)
    
    with patch.object(app, 'scan', return_value=event_datas_scan_result) as mock_scan:
        app(
            start_chunk_size=20,
            block_to_delete=10,
            progress_bar=False,
            auto_commit=True,
        )
        mock_scan.assert_called_with(
            start_block=14830,
            end_block=15123,
            start_chunk_size=20,
        )

        event_datastore_provider.save_event.assert_called()
        register_provider.register_event.assert_called()


def test_call_with_error(
    manage_event_from_blockchain, 
    event_datastore_provider,
    register_provider
):
    """
        Test __call__
    """
    app = manage_event_from_blockchain
    event_datas_scan_result = EventDatasScanResult()
    event_datas_scan_result.err = "some fake error"
    event_datastore_provider.save_events = MagicMock(
        side_effect=event_datastore_provider.save_events)
    register_provider.register_event = MagicMock(
        side_effect=register_provider.register_event)

    with patch.object(app, 'scan', return_value=event_datas_scan_result) as mock_scan:
        app(
            start_chunk_size=20,
            block_to_delete=10,
            progress_bar=False,
            auto_commit=True,
        )
        mock_scan.assert_called_with(
            start_block=14830,
            end_block=15123,
            start_chunk_size=20,
        )
        event_datastore_provider.save_events.assert_not_called()
        register_provider.register_event.assert_not_called()
