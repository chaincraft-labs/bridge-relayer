import logging
from typing import Coroutine
from unittest.mock import AsyncMock, MagicMock, patch
from hexbytes import HexBytes
import pytest

from attributedict.collections import AttributeDict
from eth_account.signers.local import LocalAccount
from eth_account.datastructures import SignedTransaction
from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract
from web3.types import (
    BlockData,
    TxReceipt,
    Nonce,
)

from src.relayer.domain.relayer import (
    BridgeTaskDTO, 
    BridgeTaskResult, 
    EventDTO,
)
from src.relayer.domain.exception import (
    BridgeRelayerBlockchainNotConnected, 
    BridgeRelayerEventsFilterTypeError,
    BridgeRelayerListenEventFailed,
)
from src.relayer.provider.relayer_blockchain_web3 import (
    RelayerBlockchainProvider
)
from tests.conftest import EVENT_SAMPLE

pytest_plugins = ('pytest_asyncio',)




# -----------------------------------------------------------------
# F I X T U R E S
# -----------------------------------------------------------------

ROOT_PATH = "src.relayer.provider.relayer_blockchain_web3"
CHAIN_ID = 80002
TX_RECEIPT = AttributeDict(
    {
        "blockHash": HexBytes(
            "0x21cf5a29ed75c26a669383c58a686fd8bdda55c2620e82ddca9e7ce490dd0547"
        ),
        "blockNumber": 7959797,
        "contractAddress": None,
        "cumulativeGasUsed": 383282,
        "effectiveGasPrice": 1000000015,
        "from": "0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11",
        "gasUsed": 288414,
        "logs": [
            AttributeDict(
                {
                    "address": "0x0000000000000000000000000000000000001010",
                    "topics": [
                        HexBytes(
                            "0x4dfe1bbbcf077ddc3e01291eea2d5c70c2b422b415d95645b9adcfd678cb1d63"
                        ),
                        HexBytes(
                            "0x0000000000000000000000000000000000000000000000000000000000001010"
                        ),
                        HexBytes(
                            "0x000000000000000000000000e4192bf486aea10422ee097bc2cf8c28597b9f11"
                        ),
                        HexBytes(
                            "0x0000000000000000000000006ab3d36c46ecfb9b9c0bd51cb1c3da5a2c81cea6"
                        ),
                    ],
                    "data": HexBytes(
                        "0x0000000000000000000000000000000000000000000000000001064f9e04ac00000000000000000000000000000000000000000000000000048d9bee3a75b1010000000000000000000000000000000000000000000001ac3ac84ce0f81bc7f8000000000000000000000000000000000000000000000000048c959e9c7105010000000000000000000000000000000000000000000001ac3ac95330962073f8"
                    ),
                    "blockNumber": 7959797,
                    "transactionHash": HexBytes(
                        "0xbe9e2d490f4026f18f2b1740e9b1c5d56268d0659ae7687546b1d256d706f2bf"
                    ),
                    "transactionIndex": 1,
                    "blockHash": HexBytes(
                        "0x21cf5a29ed75c26a669383c58a686fd8bdda55c2620e82ddca9e7ce490dd0547"
                    ),
                    "logIndex": 2,
                    "removed": False,
                }
            )
        ],
        "logsBloom": HexBytes(
            "0x00000000080000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000080000000008000000000000800000000000000000000100000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000000400000000000200000000000000000000000000000000000000000000000000000000000004000000000000000000001020000000000000000010000000000100000000000000000000000000000000000000000000000000000000000000000000000100000"
        ),
        "status": 1,
        "to": "0xc8f81a3F84a3E96c1676c7F303e191b3E688E8e5",
        "transactionHash": HexBytes(
            "0xbe9e2d490f4026f18f2b1740e9b1c5d56268d0659ae7687546b1d256d706f2bf"
        ),
        "transactionIndex": 1,
        "type": 2,
    }
)

async def mock_client_version():
    return "7.7.7"

@pytest.fixture(autouse=True)
def disable_logging():
    # Désactiver les logs pendant les tests
    logging.disable(logging.CRITICAL)
    yield
    # Réactiver les logs après les tests
    logging.disable(logging.NOTSET)


@pytest.fixture(scope="function")
def func():
    """"""
    class TransactionBuilder:
        def __init__(self, **data):
            self.data = data

        async def build_transaction(self, **data):
            return {}

    def func(**data):
        return TransactionBuilder(**data)
    
    return func

@pytest.fixture(scope="function")
def provider():
    """Create a relayer blockchain provider."""        
    provider = RelayerBlockchainProvider()
    provider.set_chain_id(chain_id=123)
    return provider

@pytest.fixture
def mock_bridge_task_dto():
    return BridgeTaskDTO(
        func_name='OperationCreated', 
        params={
            'params': [
                '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
                '0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11', 
                80002, 
                411, 
                '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
                '0x0000000000000000000000000000000000000000', 
                100, 
                123, 
                b'\xf2\xc2\x98\xbe\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06MyName\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            ]
        }
    )


@pytest.fixture
def mock_account():
    return MagicMock(
        spec=LocalAccount, 
        address="0x1234567890abcdef1234567890abcdef12345678"
    )

@pytest.fixture
def mock_nonce():
    return MagicMock(spec=Nonce, return_value=10)

@pytest.fixture
def mock_built_tx():
    return {
        "from": "0x1234567890abcdef1234567890abcdef12345678",
        "nonce": 10,
        "gas": 2000000,
        "gasPrice": 5000000000,
        "value": 0,
        "data": b"",
        "chainId": 1
    }

@pytest.fixture
def mock_signed_tx():
    return MagicMock(
        spec=SignedTransaction, 
        rawTransaction=b"raw_transaction_data"
    )

@pytest.fixture
def mock_tx_hash():
    return MagicMock(
        spec=HexBytes, 
        hex=lambda: "0x1234567890abcdef1234567890abcdef12345678")

@pytest.fixture
def mock_tx_receipt():
    return MagicMock(
        spec=TxReceipt, 
        transactionHash="0x1234567890abcdef1234567890abcdef12345678")


# -----------------------------------------------------------------
# T E S T S
# -----------------------------------------------------------------
@patch('src.relayer.provider.relayer_blockchain_web3.get_blockchain_config')
def test_set_chain_id_with_success(mock_config, provider):
    """
        Test set_chain_id that 
         - set chain id
         - get the blockchain config data (mocked)
         - connect (mocked)
    """
    provider._connect = MagicMock()
    provider.set_chain_id(chain_id=123)
    
    assert provider.chain_id == 123
    provider._connect.assert_called()
    mock_config.assert_called_with(123)


def test_set_event_filter_raise_exception(provider):
    """
        Test set_event_filter that raises BridgeRelayerEventsFilterTypeError
        if events is not a list
    """
    with pytest.raises(BridgeRelayerEventsFilterTypeError) as e:
        provider.set_event_filter(events='AnEventInSmartContract')
    assert str(e.value.args[0]) == "'events' not a list!"

def test_set_event_filter_with_success(provider):
    """
        Test set_event_filter that set a list of events
    """
    provider.set_event_filter(events=['AnEventInSmartContract'])
    provider.event_filter = ['AnEventInSmartContract']

@pytest.mark.asyncio
async def test_get_block_number_with_success(provider):
    """
        Test get_block_number that return the current block number
    """
    class BlockData:
        def __init__(self, number):
            self.number = number
    block_data = BlockData(number=777)
    provider._get_block_data = AsyncMock(return_value=block_data)

    block_number = await provider.get_block_number()
    assert block_number == 777

def test_listen_events_exception(provider):
    """
        Test listen_events that raises BridgeRelayerListenEventFailed
    """
    def mock_callback():
        return MagicMock()
    
    with patch.object(
        provider, '_execute_event_filters', side_effect=Exception('Test Exception')
    ), \
         patch('asyncio.new_event_loop'), \
         patch('asyncio.set_event_loop'), \
         patch('asyncio.gather'):

        with pytest.raises(BridgeRelayerListenEventFailed):
            provider.listen_events(callback=mock_callback, poll_interval=2)

def test_listen_events_success(provider):
    """
        Test listen_events that execute successfully
    """
    def mock_callback():
        return MagicMock()

    with patch.object(
        provider, '_execute_event_filters', return_value=[]
    ) as mock_execute_event_filters, \
         patch.object(provider, '_log_loop'), \
         patch('asyncio.new_event_loop') as mock_new_event_loop, \
         patch('asyncio.set_event_loop') as mock_set_event_loop, \
         patch('asyncio.gather') as mock_gather:

        provider.listen_events(callback=mock_callback, poll_interval=2)

        mock_execute_event_filters.assert_called_once()
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once()
        mock_gather.assert_called_once()

def test_listen_events_loop_close(provider):
    """
        Test listen_events that close the loop
    """
    def mock_callback():
        return MagicMock()
    
    with patch.object(provider, '_execute_event_filters', return_value=[]), \
         patch.object(provider, '_log_loop', ), \
         patch('asyncio.new_event_loop') as mock_new_event_loop, \
         patch('asyncio.set_event_loop'), \
         patch('asyncio.gather'):

        loop_mock = MagicMock()
        mock_new_event_loop.return_value = loop_mock

        provider.listen_events(callback=mock_callback, poll_interval=2)

        loop_mock.close.assert_called_once()

@pytest.mark.asyncio
async def test_call_contract_func_returns_err(provider, mock_bridge_task_dto):
    """
        Test call_contract_func that raises
    """
    provider.client_version = MagicMock(
        side_effect=BridgeRelayerBlockchainNotConnected(
            "fake client connect error"
        ))

    result = await provider.call_contract_func(
        bridge_task_dto=mock_bridge_task_dto)
    assert isinstance(result, BridgeTaskResult)
    assert str(result.err) == "fake client connect error"

@pytest.mark.asyncio
async def test_call_contract_func_success(provider, mock_bridge_task_dto):
    """
        Test call_contract_func that return 
    """
    with patch.object(provider, 'client_version', new_callable=AsyncMock, return_value='1.0.0') as mock_client_version, \
         patch.object(provider, '_get_nonce', new_callable=AsyncMock, return_value=1) as mock_get_nonce, \
         patch.object(provider, '_get_function_by_name', return_value=MagicMock()) as mock_get_function_by_name, \
         patch.object(provider, '_build_tx', new_callable=AsyncMock, return_value={}) as mock_build_tx, \
         patch.object(provider, '_sign_tx', return_value=MagicMock()) as mock_sign_tx, \
         patch.object(provider, '_send_raw_tx', new_callable=AsyncMock, return_value=MagicMock()) as mock_send_raw_tx, \
         patch.object(
             provider, 
             '_wait_for_transaction_receipt', 
             new_callable=AsyncMock, 
             return_value=MagicMock(
                 transactionHash=HexBytes('1234'), 
                 blockHash=HexBytes('0x4567'), 
                 blockNumber=1, 
                 gasUsed=21000
                )
        ) as mock_wait_for_transaction_receipt:

        result = await provider.call_contract_func(mock_bridge_task_dto)

        mock_client_version.assert_called_once()
        mock_get_nonce.assert_called_once()
        mock_get_function_by_name.assert_called_once_with(
            bridge_task_dto=mock_bridge_task_dto)
        mock_build_tx.assert_called_once()
        mock_sign_tx.assert_called_once()
        mock_send_raw_tx.assert_called_once()
        mock_wait_for_transaction_receipt.assert_called_once()
        
        assert isinstance(result, BridgeTaskResult)
        assert result.ok is not None
        assert result.ok.tx_hash == '0x1234'
        assert result.ok.block_hash == '0x4567'
        assert result.ok.block_number == 1
        assert result.ok.gas_used == 21000


@pytest.mark.asyncio
async def test_relayer_blockchain_not_connected(provider):
    """
        Test that the relayer_blockchain is not connected and 
        raise RelayerBlockchainNotConnected.
    """
    with pytest.raises(BridgeRelayerBlockchainNotConnected):
        await provider.client_version()

@pytest.mark.asyncio  
async def test_client_version_with_blockchain_conneted(provider):
    """
        Test that the w3 is a mock using EthereumTester.
    """
    with patch.object(provider, "w3") as mock_w3:
        mock_w3.client_version = mock_client_version()
        assert await provider.client_version() == await mock_client_version()

def test__set_provider_returns_asyncweb3_instance(provider):
    """
        Test _set_provider that returns a AsyncWeb3 instance.
    """
    assert isinstance(provider._set_provider(), AsyncWeb3)

def test__set_contract_returns_AsyncContract_instance(provider):
    """
        Test _set_contract that returns a AsyncContract instance.
    """
    provider._set_contract()
    assert isinstance(provider._set_contract(), AsyncContract)


def test_create_event_dto_return_event_dto(provider):
    """
        Test create_event_dto that returns a EventDTO instance.
    """
    event_dto: EventDTO = provider.create_event_dto(EVENT_SAMPLE)
    assert isinstance(event_dto, EventDTO)
    assert event_dto.name == EVENT_SAMPLE.event # type: ignore
    assert event_dto.data == EVENT_SAMPLE.args # type: ignore

def test__handle_event_execute_callback(provider):
    """
        Test _handle_event that should execute a callback function with 
        EventDTO.
    
        args:
         event: Must be an EventDTO
         callback: Can be anything that an EventDTO as parameters. 
            The callback is defined and used in tha applciation layer.
    """
    def foo(event: EventDTO):
        assert event.name == EVENT_SAMPLE.event # type: ignore
        
    provider._handle_event(EVENT_SAMPLE, foo)

def test__execute_event_filters_returns_list_event_filter(provider):
    """
        Test _execute_event_filters that returns a list of event filter log.
    """
    async def foo():
        return 777
    event_filters = [foo()]
            
    with patch.object(
        provider, 
        "_create_event_filters"
    ) as mock_create_event_filters:
        mock_create_event_filters.return_value = event_filters
        result = provider._execute_event_filters()
        assert result[0] == 777

@pytest.mark.asyncio
async def test__handle_event_execute_callback_func(provider):
    """
        Test _log_loop that execute the callbak function.
    """
    def callback(event_dto):
        assert isinstance(event_dto, EventDTO)

    mock_event_filter = AsyncMock()
    attrs = {'get_new_entries.return_value': [EVENT_SAMPLE]}
    mock_event_filter.configure_mock(**attrs)
    await provider._loop_handle_event(
        event_filter=mock_event_filter,
        poll_interval=0,
        callback=callback,   
    )

@pytest.mark.asyncio
async def test_estimate_gas_success(provider, mock_bridge_task_dto):
    """
        Test _estimate_gas that returns estimated gas for a tx
    """
    mock_func = MagicMock()
    mock_func.return_value.estimate_gas = AsyncMock(return_value=100000)

    with patch.object(
        provider, 
        '_get_function_by_name', 
        return_value=mock_func
    ) as mock_get_function_by_name:
        estimated_gas = await provider._estimate_gas(mock_bridge_task_dto)

        mock_get_function_by_name.assert_called_once_with(mock_bridge_task_dto)
        mock_func.assert_called_once_with(**mock_bridge_task_dto.params)
        mock_func.return_value.estimate_gas.assert_called_once()
        assert estimated_gas == 100000

@pytest.mark.asyncio
async def test_estimate_gas_exception(provider, mock_bridge_task_dto):
    """
        Test _estimate_gas that raises exception
    """
    mock_func = MagicMock()
    mock_func.return_value.estimate_gas = AsyncMock(
        side_effect=Exception('Test Exception'))

    with patch.object(
        provider, 
        '_get_function_by_name', 
        return_value=mock_func
    ) as mock_get_function_by_name:
        with pytest.raises(Exception, match='Test Exception'):
            await provider._estimate_gas(mock_bridge_task_dto)

        mock_get_function_by_name.assert_called_once_with(mock_bridge_task_dto)
        mock_func.assert_called_once_with(**mock_bridge_task_dto.params)
        mock_func.return_value.estimate_gas.assert_called_once()

@pytest.mark.asyncio
async def test_get_block_data(provider):
    """
        Test _get_block_data that returns data from a block
    """
    mock_block_data = MagicMock(spec=BlockData)
    mock_block_data.number = 999

    with patch.object(
        provider.w3.eth, 
        'get_block', 
        new_callable=AsyncMock, 
        return_value=mock_block_data
    ) as mock_get_block:
        block_data = await provider._get_block_data()

        mock_get_block.assert_called_once_with("latest")
        assert block_data == mock_block_data
        assert block_data.number == 999

@pytest.mark.asyncio
async def test_get_block_data_exception(provider):
    """
        Test _get_block_data that raises an exception
    """
    with patch.object(
        provider.w3.eth, 
        'get_block', 
        new_callable=AsyncMock, 
        side_effect=Exception('Test Exception')
    ) as mock_get_block:
        with pytest.raises(Exception, match='Test Exception'):
            await provider._get_block_data()

        mock_get_block.assert_called_once_with("latest")

@pytest.mark.asyncio
async def test_create_event_filters_success(provider):
    """
        Test _create_event_filters that returns a list of event_filter
        Note that you have to specify which event to handle with
        provider.event_filter
    """
    mock_event_1 = MagicMock()
    mock_event_1.event_name = "OperationCreated"
    mock_event_1.create_filter.return_value = MagicMock(spec=Coroutine)

    mock_event_2 = MagicMock()
    mock_event_2.event_name = "FeesLockedConfirmed"
    mock_event_2.create_filter.return_value = MagicMock(spec=Coroutine)

    mock_event_3 = MagicMock()
    mock_event_3.event_name = "UnknownEvent"
    mock_event_3.create_filter.return_value = MagicMock(spec=Coroutine)

    provider.w3_contract.events = [mock_event_1, mock_event_2, mock_event_3]
    provider.event_filter = [
        'OperationCreated',
        'FeesLockedConfirmed',
    ]
    event_filters = provider._create_event_filters()

    assert len(event_filters) == 2
    assert mock_event_1.create_filter.called
    assert mock_event_2.create_filter.called
    assert not mock_event_3.create_filter.called

@pytest.mark.asyncio
async def test_create_event_filters_no_matching_events(provider):
    """
        Test _create_event_filters that returns no event filter if events
        are invalid 
    """
    mock_event_1 = MagicMock()
    mock_event_1.event_name = "UnknownEvent1"
    mock_event_1.create_filter.return_value = MagicMock(spec=Coroutine)

    mock_event_2 = MagicMock()
    mock_event_2.event_name = "UnknownEvent2"
    mock_event_2.create_filter.return_value = MagicMock(spec=Coroutine)

    provider.w3_contract.events = [mock_event_1, mock_event_2]

    event_filters = provider._create_event_filters()

    assert len(event_filters) == 0
    assert not mock_event_1.create_filter.called
    assert not mock_event_2.create_filter.called


@pytest.mark.asyncio
async def test_get_nonce_success(provider, mock_account):
    """
        Test _get_nonce that returns a Nonce instance
    """
    expected_nonce = 10

    with patch.object(
        provider.w3.eth, 
        'get_transaction_count', 
        new_callable=AsyncMock, 
        return_value=expected_nonce
    ) as mock_get_transaction_count:
        nonce = await provider._get_nonce(mock_account)

        mock_get_transaction_count.assert_called_once_with(mock_account.address)
        assert nonce == expected_nonce

@pytest.mark.asyncio
async def test_get_nonce_exception(provider, mock_account):
    """
        Test _get_nonce that raises an exception
    """
    with patch.object(
        provider.w3.eth, 
        'get_transaction_count', 
        new_callable=AsyncMock, 
        side_effect=Exception('Test Exception')
    ) as mock_get_transaction_count:
        with pytest.raises(Exception, match='Test Exception'):
            await provider._get_nonce(mock_account)

        mock_get_transaction_count.assert_called_once_with(mock_account.address)


@pytest.mark.asyncio
async def test_get_function_by_name_success(provider, mock_bridge_task_dto):
    """
        Test _get_function_by_name that returns a callable function 
        (smart contract function)
    """
    mock_func = MagicMock()

    with patch.object(
        provider.w3_contract, 
        'get_function_by_name', 
        return_value=mock_func
    ) as mock_get_function_by_name:
        func = provider._get_function_by_name(mock_bridge_task_dto)

        mock_get_function_by_name.assert_called_once_with(
            mock_bridge_task_dto.func_name)
        assert func == mock_func

@pytest.mark.asyncio
async def test_get_function_by_name_exception(provider, mock_bridge_task_dto):
    """
        Test _get_function_by_name that raise exception
    """
    with patch.object(
        provider.w3_contract, 
        'get_function_by_name', 
        side_effect=Exception('Test Exception')
    ) as mock_get_function_by_name:
        with pytest.raises(Exception, match='Test Exception'):
            provider._get_function_by_name(mock_bridge_task_dto)

        mock_get_function_by_name.assert_called_once_with(
            mock_bridge_task_dto.func_name)

@pytest.mark.asyncio
async def test_build_tx_success(
    provider, 
    mock_bridge_task_dto, 
    mock_account, 
    mock_nonce
):
    """
        Test _build_tx that returns a built transaction
    """
    mock_func = MagicMock()
    mock_func.return_value.build_transaction = AsyncMock(
        return_value={"transaction": "data"})

    built_tx = await provider._build_tx(
        func=mock_func,
        bridge_task_dto=mock_bridge_task_dto,
        account=mock_account,
        nonce=mock_nonce
    )

    mock_func.assert_called_once_with(**mock_bridge_task_dto.params)
    mock_func.return_value.build_transaction.assert_called_once_with(
        transaction={
            "from": mock_account.address,
            "nonce": mock_nonce,
        }
    )
    assert built_tx == {"transaction": "data"}

@pytest.mark.asyncio
async def test_build_tx_exception(
    provider, 
    mock_bridge_task_dto, 
    mock_account, 
    mock_nonce
):
    """
        Test _build_tx that raises an exception
    """
    mock_func = MagicMock()
    mock_func.return_value.build_transaction = AsyncMock(
        side_effect=Exception('Test Exception'))

    with pytest.raises(Exception, match='Test Exception'):
        await provider._build_tx(
            func=mock_func,
            bridge_task_dto=mock_bridge_task_dto,
            account=mock_account,
            nonce=mock_nonce
        )

    mock_func.assert_called_once_with(**mock_bridge_task_dto.params)
    mock_func.return_value.build_transaction.assert_called_once_with(
        transaction={
            "from": mock_account.address,
            "nonce": mock_nonce,
        }
    )


@pytest.mark.asyncio
async def test_sign_tx_success(provider, mock_account, mock_built_tx):
    """
        Test _sign_tx that returns a signed transaction
    """
    mock_signed_tx = MagicMock(spec=SignedTransaction)

    with patch.object(
        provider.w3.eth.account, 
        'sign_transaction', 
        return_value=mock_signed_tx
    ) as mock_sign_transaction:
        signed_tx = provider._sign_tx(mock_built_tx, mock_account)

        mock_sign_transaction.assert_called_once_with(
            mock_built_tx, private_key=mock_account.key)
        assert signed_tx == mock_signed_tx

@pytest.mark.asyncio
async def test_sign_tx_exception(provider, mock_account, mock_built_tx):
    """
        Test _sign_tx that raise an exception
    """
    with patch.object(
        provider.w3.eth.account, 
        'sign_transaction', 
        side_effect=Exception('Test Exception')
    ) as mock_sign_transaction:
        with pytest.raises(Exception, match='Test Exception'):
            provider._sign_tx(mock_built_tx, mock_account)

        mock_sign_transaction.assert_called_once_with(
            mock_built_tx, private_key=mock_account.key)

@pytest.mark.asyncio
async def test_send_raw_tx_success(provider, mock_signed_tx):
    """
        Test _send_raw_tx that returns a transaction hash
    """
    mock_tx_hash = MagicMock(
        spec=HexBytes, 
        hex=b"0x1234567890abcdef1234567890abcdef12345678"
    )

    with patch.object(
        provider.w3.eth, 
        'send_raw_transaction', 
        new_callable=AsyncMock, 
        return_value=mock_tx_hash
    ) as mock_send_raw_transaction:
        tx_hash = await provider._send_raw_tx(mock_signed_tx)

        mock_send_raw_transaction.assert_called_once_with(
            mock_signed_tx.rawTransaction)
        assert tx_hash == mock_tx_hash

@pytest.mark.asyncio
async def test_send_raw_tx_exception(provider, mock_signed_tx):
    """
        Test _send_raw_tx that raises an exception
    """
    with patch.object(
        provider.w3.eth, 
        'send_raw_transaction', 
        new_callable=AsyncMock, 
        side_effect=Exception('Test Exception')
    ) as mock_send_raw_transaction:
        with pytest.raises(Exception, match='Test Exception'):
            await provider._send_raw_tx(mock_signed_tx)

        mock_send_raw_transaction.assert_called_once_with(
            mock_signed_tx.rawTransaction)
    
@pytest.mark.asyncio
async def test_wait_for_transaction_receipt_success(
    provider, 
    mock_tx_hash, mock_tx_receipt
):
    """
        Test _wait_for_transaction_receipt that returns a transaction receipt
    """
    with patch.object(
        provider.w3.eth, 
        'wait_for_transaction_receipt', 
        new_callable=AsyncMock, 
        return_value=mock_tx_receipt
    ) as mock_wait_for_transaction_receipt:
        tx_receipt = await provider._wait_for_transaction_receipt(
            mock_tx_hash)

        mock_wait_for_transaction_receipt.assert_called_once_with(
            mock_tx_hash)
        assert tx_receipt == mock_tx_receipt

@pytest.mark.asyncio
async def test_wait_for_transaction_receipt_exception(
    provider, 
    mock_tx_hash
):
    """
        Test _wait_for_transaction_receipt that raises an exception
    """
    with patch.object(
        provider.w3.eth, 
        'wait_for_transaction_receipt', 
        new_callable=AsyncMock, 
        side_effect=Exception('Test Exception')
    ) as mock_wait_for_transaction_receipt:
        with pytest.raises(Exception, match='Test Exception'):
            await provider._wait_for_transaction_receipt(mock_tx_hash)

        mock_wait_for_transaction_receipt.assert_called_once_with(
            mock_tx_hash)
