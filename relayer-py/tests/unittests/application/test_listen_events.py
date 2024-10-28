from datetime import datetime
import logging
import pathlib
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest

from src.relayer.domain.exception import (
    RelayerEventScanFailed, 
    RelayerRegisterEventFailed, 
    RepositoryErrorOnGet, 
    RepositoryErrorOnSave,
)
from src.relayer.domain.event_db import (
    EventDTO, 
    EventDataDTO,
    EventScanDTO,
)
from src.relayer.application.repository import Repository
from src.relayer.config.config import Config
from src.relayer.application.listen_events import ListenEvents
from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO,
    RelayerRegisterConfigDTO,
)

from src.relayer.provider.mock_relayer_blockchain_web3 import RelayerBlockchainProvider
from src.relayer.provider.mock_relayer_register_aio_pika import RelayerRegisterProvider
from src.relayer.provider.mock_relayer_repository_leveldb import RelayerRepositoryProvider
from tests.conftest import EVENT_DATA_SAMPLE as event_data
from src.utils.converter import to_bytes


PATH_APP = 'src.relayer.application.listen_events'
TEST_ROOT_PATH = pathlib.Path(__file__).parent.parent.parent
TEST_REPOSITORY_NAME = 'test.db'
DB_TEST = str(TEST_ROOT_PATH / TEST_REPOSITORY_NAME)


# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(autouse=True)
def disable_logging():
    # Disable logging during tests
    logging.disable(logging.CRITICAL)
    yield
    # Enable loggin after tests
    logging.disable(logging.NOTSET)

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
        smart_contract_deployment_block=666, 
        abi=[{}], 
        client='middleware'
    )
    return config

@pytest.fixture(scope="function")
def event_filters():
    return [
        'OperationCreated',
        'FeesDepositConfirmed',
        'FeesDeposited',
        'FeesDepositConfirmed',
        'FeesLockedAndDepositConfirmed',
        'OperationFinalized'
    ]


@pytest.fixture(scope="function")
def config(
    blockchain_config,
    register_config,
    event_filters,
):
    config = Config()
    config.get_register_config = MagicMock()
    config.get_register_config.return_value = register_config
    config.get_blockchain_config = MagicMock()
    config.get_blockchain_config.return_value = blockchain_config
    config.get_relayer_events = MagicMock()
    config.get_relayer_events.return_value = event_filters
    config.get_data_path = MagicMock()
    config.get_data_path.return_value = TEST_ROOT_PATH
    config.get_repository_name = MagicMock()
    config.get_repository_name.return_value = TEST_REPOSITORY_NAME

    return config


@pytest.fixture(scope="function")
def repository():
    repository = Repository(RelayerRepositoryProvider)
    repository.setup = AsyncMock()
    repository.get_last_scanned_block = AsyncMock()
    repository.get_last_scanned_block.return_value = 111
    repository.store_events = AsyncMock()
    repository.store_events.return_value = False
    repository.set_last_scanned_block = AsyncMock()
    repository.is_event_registered = AsyncMock()
    repository.is_event_registered.return_value = False
    repository.set_event_as_registered = AsyncMock()

    return repository

@pytest.fixture(scope="function")
def listen_events(config, repository):
    with patch(f'{PATH_APP}.Config', return_value=config):
        app = ListenEvents(
            relayer_blockchain_provider=RelayerBlockchainProvider(),
            relayer_register_provider=RelayerRegisterProvider(),
            relayer_repository_provider=RelayerRepositoryProvider(),
            chain_id=123,
            min_scan_chunk_size=10,
            max_scan_chunk_size=10000,
            chunk_size_increase=2.0,
            log_level='info',
        )
        app.repository = repository
    return app


@pytest.fixture
def example_event():
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
def example_events_scan(example_event):
    """Create an example of EventScanDTO."""
    events = []
    for i in range(10):
        example_event.block_number = i
        events.append(example_event)

    return EventScanDTO(
        events=events,
        chunks_scanned=10
    )

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

# -------------------------------------------------------
# Test init
# -------------------------------------------------------
def test_init_instance(listen_events, config, repository):
    """Test ListenEvents that is well initialized."""
    assert listen_events.log_level == 'info'
    assert listen_events.chain_id == 123
    assert listen_events.config == config
    assert listen_events.register_config == config.get_register_config()
    assert listen_events.blockchain_config == config.get_blockchain_config()
    assert listen_events.event_filters == config.get_relayer_events()
    assert listen_events.repository_name == str(TEST_ROOT_PATH / f"123.events.{TEST_REPOSITORY_NAME}")
    assert type(listen_events.blockchain_provider) is RelayerBlockchainProvider
    assert type(listen_events.register_provider) is RelayerRegisterProvider
    assert listen_events.min_scan_chunk_size == 10
    assert listen_events.max_scan_chunk_size == 10000
    assert listen_events.chunk_size_increase == 2.0
    assert listen_events.repository == repository

# -------------------------------------------------------
# Test register_event
# -------------------------------------------------------
@pytest.mark.parametrize('is_event_registered', [True, False])
@pytest.mark.asyncio
async def test_register_event(listen_events, example_event, repository, is_event_registered):
    """Test register event."""
    repository.is_event_registered.return_value = is_event_registered

    with patch.object(listen_events.register_provider, 'register_event') as mock_register_event:
        with patch.object(listen_events.repository, 'set_event_as_registered') as mock_set_event_as_registered:
            await listen_events.register_event(example_event)
            if is_event_registered is False:
                mock_register_event.assert_called_once_with(to_bytes(example_event))
                mock_set_event_as_registered.assert_called_once_with(example_event)
            else:
                mock_register_event.assert_not_called()
                mock_set_event_as_registered.assert_not_called()

@pytest.mark.asyncio
async def test_register_event_raise_exception_1(listen_events, example_event):
    """Test register event."""
    with patch.object(listen_events.register_provider, 'register_event') as mock_register_event:
        with patch.object(listen_events.repository, 'set_event_as_registered'):
            mock_register_event.side_effect = RelayerRegisterEventFailed('fake error')
            with patch.object(listen_events.logger, 'info') as mock_logger:
                await listen_events.register_event(example_event)

                mock_logger.assert_called_once_with(
                    f"{listen_events.Emoji.warn.value}chain_id={listen_events.chain_id} fake error"
                )

@pytest.mark.asyncio
async def test_register_event_raise_exception_2(listen_events, example_event):
    """Test register event."""
    with patch.object(listen_events.register_provider, 'register_event'):
        with patch.object(listen_events.repository, 'set_event_as_registered') as mock_set_event_as_registered:
            mock_set_event_as_registered.side_effect = RepositoryErrorOnSave('fake error')
            with patch.object(listen_events.logger, 'info') as mock_logger:
                await listen_events.register_event(example_event)

                mock_logger.assert_called_once_with(
                    f"{listen_events.Emoji.warn.value}chain_id={listen_events.chain_id} fake error"
                )

# -------------------------------------------------------
# Test show_cli_title
# -------------------------------------------------------
def test_show_cli_title(listen_events):
    """Test show_cli_title."""
    listen_events.blockchain_provider.client_version = MagicMock()
    listen_events.blockchain_provider.client_version.return_value = '1.0.0'
    listen_events.blockchain_provider.get_account_address = MagicMock()
    listen_events.blockchain_provider.get_account_address.return_value = '0x0000000000000000000000000000000000000000'

    start_block = 1
    end_block = 10
    blocks_to_scan = end_block - start_block

    with patch.object(listen_events, 'print_log') as mock_print_log:
        listen_events.show_cli_title(start_block, end_block)

        expected_title_length = 20
        expected_calls = [
            call(
                "none",
                f"{'rpc_url':<{expected_title_length}} : {listen_events.blockchain_config.rpc_url}\n"
                f"{'client version':<{expected_title_length}} : {listen_events.blockchain_provider.client_version()}\n"
                f"{'chain_id':<{expected_title_length}} : {listen_events.chain_id}\n"
                f"{'Account address':<{expected_title_length}} : {listen_events.blockchain_provider.get_account_address()}\n"
                f"{'Contract address':<{expected_title_length}} : {listen_events.blockchain_config.smart_contract_address}\n"
                f"{'Deployment block':<{expected_title_length}} : {listen_events.blockchain_config.smart_contract_deployment_block}\n"
                f"{'start_block':<{expected_title_length}} : {start_block}\n"
                f"{'end_block':<{expected_title_length}} : {end_block}\n"
                f"{'blocks_to_scan':<{expected_title_length}} : {blocks_to_scan}\n"
            ),
            call('main', "Waiting for events. To exit press CTRL+C")
        ]

        mock_print_log.assert_has_calls(expected_calls)



# -------------------------------------------------------
# Test get_suggested_scan_end_block
# -------------------------------------------------------
@pytest.mark.parametrize('current_block, expected', [
    (789, 788),
    (0, 0),
    (-1, 0)
])
def test_get_suggested_scan_end_block(listen_events, current_block, expected):
    """Test get_suggested_scan_end_block."""
    listen_events.blockchain_provider.get_current_block_number = MagicMock()
    listen_events.blockchain_provider.get_current_block_number.return_value = current_block
    assert listen_events.get_suggested_scan_end_block() == expected

# -------------------------------------------------------
# Test estimate_next_chunk_size
# -------------------------------------------------------
@pytest.mark.parametrize('current_chuck_size, event_found_count, expected', [
    (0, 10, 10), # min_scan_chunk_size with event_found_count > 0
    (0, 0, 10),
    (10, 0, 20),
    (15000, 0, 10000), # max_scan_chunk_size
])
def test_estimate_next_chunk_size(
    listen_events,
    current_chuck_size, 
    event_found_count, 
    expected
):
    """Test estimate_next_chunk_size.
    
    Based on default value: 
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000,
        chunk_size_increase: float = 2.0,
    """
    assert listen_events.estimate_next_chunk_size(
        current_chuck_size, 
        event_found_count
    ) == expected


# -------------------------------------------------------
# Test scan
# -------------------------------------------------------
def test_scan_raise_exception(listen_events):
    """Test scan that raise RelayerEventScanFailed 
        when start_block > end_block.
    """
    start_block = 10
    end_block = 9
    with pytest.raises(RelayerEventScanFailed):
        listen_events.scan(start_block, end_block)

def test_scan(listen_events, example_event):
    """Test scan."""
    events = []
    for i in range(30):
        example_event.block_number = i
        events.append(example_event)
    _end_block = 200

    listen_events.blockchain_provider.scan = MagicMock()
    listen_events.blockchain_provider.scan.return_value = (events, _end_block)
    listen_events.blockchain_provider.get_block_timestamp = MagicMock()
    listen_events.blockchain_provider.get_block_timestamp.return_value = "2023-11-14 05:33:20"
    listen_events.estimate_next_chunk_size = MagicMock()
    listen_events.estimate_next_chunk_size.return_value = 10
    mock_progress_callback = MagicMock()

    start_block = 1
    end_block = 1000
    start_chunk_size = 10
    event_scanned = listen_events.scan(
        start_block, 
        end_block, 
        start_chunk_size, 
        mock_progress_callback
    )
    assert event_scanned.events == events
    assert event_scanned.chunks_scanned == 1
    mock_progress_callback.assert_called()

# -------------------------------------------------------
# Test run_scan_with_progress_bar_render
# -------------------------------------------------------
def test_run_scan_with_progress_bar_render(
    listen_events, 
    example_events_scan
):
    """Test run_scan_with_progress_bar_render."""
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan

    start_block = 1
    end_block = 10 

    with patch(f"{PATH_APP}.tqdm") as mock_tqdm:
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = mock_progress_bar

        result = listen_events.run_scan_with_progress_bar_render(
            start_block=start_block, 
            end_block=end_block, 
            start_chunk_size=10
        )

        assert result == example_events_scan
        mock_tqdm.assert_called_once_with(total=end_block - start_block)


# -------------------------------------------------------
# Test __call__
# -------------------------------------------------------
@pytest.mark.asyncio
async def test__call___with_resume_events(
    listen_events, 
    example_events_scan,
):
    """
        Test __call__.

        resume_events: True
        progress_bar: False
        scan_as_service: False
    """
    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan
    listen_events.repository.is_event_registered = AsyncMock(return_value=False)
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.print_log = MagicMock()

    # act
    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    # assert
    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20

    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.scan.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )
    listen_events.repository.store_event.call_count == 30
    listen_events.register_event.call_count == 30
    listen_events.print_log.assert_called_once()
    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )

@pytest.mark.asyncio
async def test__call___with_with_progress_bar(
    listen_events, 
    example_events_scan,
):
    """Test __call__.

        resume_events: True
        progress_bar: True
        scan_as_service: False
    """
    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.run_scan_with_progress_bar_render = MagicMock()
    listen_events.run_scan_with_progress_bar_render.return_value = example_events_scan
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.print_log = MagicMock()

    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=True,
        as_service=False,
        log_level='info',
    )

    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20
    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.run_scan_with_progress_bar_render.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )
    listen_events.repository.store_event.call_count == 30
    listen_events.register_event.call_count == 30
    listen_events.print_log.assert_called_once()
    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )

@pytest.mark.asyncio
async def test__call___with_raise_exception_1(
    listen_events, 
    example_events_scan,
):
    """Test __call__.

        get_last_scanned_block raise RepositoryErrorOnGet => last_scanned_block = 0
    """

    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.side_effect = RepositoryErrorOnGet('fake error')
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.print_log = MagicMock()

    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20
    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.scan.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )
    listen_events.repository.store_event.call_count == 30
    listen_events.register_event.call_count == 30
    listen_events.print_log.assert_called_once()
    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )


@pytest.mark.asyncio
async def test__call___with_raise_exception_2(
    listen_events, 
):
    """Test __call__.

    listen_events.scan raise RelayerEventScanFailed => nothing to register
    """

    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.side_effect = RelayerEventScanFailed('fake error')
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.print_log = MagicMock()

    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20
    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.scan.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )

@pytest.mark.asyncio
async def test__call___with_with_no_event_scanned(
    listen_events, 
    example_events_scan,
):
    """Test __call__.

    event_scanned = []
        nothing to store
        nothing to register
    """
    example_events_scan.events = [None]

    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.print_log = MagicMock()

    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20
    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.scan.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )

    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )

@pytest.mark.asyncio
async def test__call___set_last_scanned_block_raise_Exception(
    listen_events, 
    example_events_scan,
):
    """
        Test __call__.

        set_last_scanned_block raise RepositoryErrorOnSave
        Log error
    """
    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan
    listen_events.repository.store_event = AsyncMock()
    listen_events.repository.store_event.return_value = True
    listen_events.register_event = AsyncMock()
    # Raise RepositoryErrorOnSave
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.repository.set_last_scanned_block.side_effect = RepositoryErrorOnSave('fake error')
    listen_events.print_log = MagicMock()
    listen_events.logger = MagicMock()

    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    # assert
    listen_events.repository.setup.assert_called_once_with(repository_name=listen_events.repository_name)
    listen_events.blockchain_provider.connect_client.assert_called_once_with(chain_id=listen_events.chain_id)
    listen_events.blockchain_provider.set_event_filter.assert_called_once_with(
        events=listen_events.event_filters
    )
    listen_events.get_suggested_scan_end_block.call_count == 2
    listen_events.repository.get_last_scanned_block.assert_called_once_with(listen_events.chain_id)
    # start_block = get_last_scanned_block - block_to_delete = 0 OR smart_contract_deployment_block = 321
    # start_block Max => 321
    # end_block = 100
    start_block = 321
    end_block = 100
    start_chunk_size = 20
    listen_events.show_cli_title.assert_called_once_with(start_block, end_block)
    listen_events.scan.assert_called_once_with(
        start_block=start_block, 
        end_block=end_block, 
        start_chunk_size=start_chunk_size
    )
    listen_events.repository.store_event.call_count == 30
    listen_events.register_event.call_count == 30
    listen_events.print_log.assert_called_once()
    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )

    msg = (
        f"chain_id={listen_events.chain_id} "
        "Unable to save last scanned block with bloc number="
        f"{end_block}"
    )
    listen_events.logger.error.assert_called_once_with(
        f"{listen_events.Emoji.fail.value}{msg}"
    )

@pytest.mark.asyncio
async def test__call___set_last_scanned_block_event_alreadt_registered(
    listen_events, 
    example_events_scan,
):
    """
        Test __call__.

        set_last_scanned_block raise RepositoryErrorOnSave
        Log error
    """
    listen_events.repository.setup = AsyncMock()
    listen_events.blockchain_provider.connect_client = MagicMock()
    listen_events.blockchain_provider.set_event_filter = MagicMock()
    listen_events.get_suggested_scan_end_block = MagicMock()
    listen_events.get_suggested_scan_end_block.return_value = 100
    listen_events.repository.get_last_scanned_block = AsyncMock()
    listen_events.repository.get_last_scanned_block.return_value = 10
    listen_events.blockchain_config.smart_contract_deployment_block = 321
    listen_events.show_cli_title = MagicMock()
    listen_events.scan = MagicMock()
    listen_events.scan.return_value = example_events_scan
    
    listen_events.repository.is_event_registered = AsyncMock()
    listen_events.repository.is_event_registered.return_value = True

    listen_events.print_log = MagicMock()
    listen_events.repository.set_last_scanned_block = AsyncMock()
    listen_events.logger = MagicMock()

    end_block = 100
    await listen_events(
        resume_events=True,
        start_chunk_size=20,
        block_to_delete=10,
        progress_bar=False,
        as_service=False,
        log_level='info',
    )

    calls = [call(event) for event in example_events_scan.events]
    listen_events.repository.is_event_registered.assert_has_awaits(calls)
    listen_events.print_log.assert_not_called()
    listen_events.repository.set_last_scanned_block.assert_called_once_with(
        chain_id=listen_events.chain_id, 
        block_numer=end_block
    )