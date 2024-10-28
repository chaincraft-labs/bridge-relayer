from datetime import datetime, timezone
import re
from unittest.mock import MagicMock, patch
from eth_typing import ABIEvent
from hexbytes import HexBytes
import pytest
from attributedict.collections import AttributeDict

from web3 import EthereumTesterProvider, Web3
from web3.contract.contract import Contract
from web3.exceptions import BlockNotFound
from eth_account.datastructures import SignedTransaction

from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.domain.exception import (
    RelayerBlockchainBuildTxError,
    RelayerBlockchainFailedExecuteSmartContract, 
    RelayerBlockchainSendRawTxError, 
    RelayerBlockchainSignTxError,
    RelayerErrorBlockPending,
    RelayerEventsNotFound,
    RelayerFetchEventOutOfRetries,
)
from src.relayer.domain.event_db import (
    BridgeTaskActionDTO, 
    EventDTO, 
    EventDataDTO
)
from src.relayer.config.config import Config
from src.relayer.provider.relayer_blockchain_web3 import RelayerBlockchainProvider

from tests.conftest import EVENT_DATA_SAMPLE as event_data


APP_PATH = 'src.relayer.provider.relayer_blockchain_web3'
# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(scope="function")
def mock_abi():
    return [
        {
        "inputs": [
          {
            "internalType": "address",
            "name": "storageAddress",
            "type": "address"
          }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
      }
    ]

@pytest.fixture(scope="function")
def event_filters():
    return [
        'OperationCreated',
        'FeesDeposited',
        'FeesDepositConfirmed',
        'FeesLockedConfirmed',
        'FeesLockedAndDepositConfirmed',
        'OperationFinalized'
    ]

@pytest.fixture(scope="function")
def mock_log_receipts():
    # List[LogReceipt]
    return [
        AttributeDict({
            'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
            'topics': [HexBytes('0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333')], 
            'data': HexBytes('0x7e87776dbaf8294ccf33d838d00e781ee6f6f4c12fb42d1267003089bb9987b4000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000039f400000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000000000000000000000000000000000000000001b80000000000000000000000000000000000000000000000000000000000000539000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000038d7ea4c68000000000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000001400000000000000000000000000000000000000000000000000000000000000007616c6c66656174000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000041bf24e366b1b28332554020d0f7dc8ada16b0517570e6822c4aaa000573b769635440e2e7fa16f72bfcf8aa6e25e47c3a4876287fb9945429484bc1c725f694841c00000000000000000000000000000000000000000000000000000000000000'), 
            'blockNumber': 14836, 
            'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'), 
            'transactionIndex': 0, 
            'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'), 
            'logIndex': 0, 
            'removed': False
        }), 
        AttributeDict({
            'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
            'topics': [HexBytes('0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333')], 
            'data': HexBytes('0xbb3140d36c558ae7c7fd326fd3c494840cf37e654e276003785d8fbdad02b8a1000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000039f800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000000000000000000000000000000000000000001b80000000000000000000000000000000000000000000000000000000000000539000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000038d7ea4c68000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000001400000000000000000000000000000000000000000000000000000000000000007616c6c666561740000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000418ba2d03bc289b966fbf5535aca193e60636654e5386b7657b53466fe55cdb81d42ed1f314a86160ef628f5dbd407714a9b3a49100bd050719a51c877d09f6ecd1c00000000000000000000000000000000000000000000000000000000000000'), 
            'blockNumber': 14840, 
            'transactionHash': HexBytes('0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962'), 
            'transactionIndex': 0, 
            'blockHash': HexBytes('0xa776cd94ee4ba4e309d85636bace1831592dbb96d61658895caae9d7d3ec8756'), 
            'logIndex': 0, 
            'removed': False
        })
    ]

@pytest.fixture(scope="function")
def mock_event_datas():
    # List[EventData] =
    return [
        AttributeDict({
            'args': AttributeDict({
                'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4',
                'params': AttributeDict({
                    'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
                    'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
                    'chainIdFrom': 440,
                    'chainIdTo': 1337,
                    'tokenName': 'allfeat',
                    'amount': 1000000000000000,
                    'nonce': 3,
                    'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
                }),
                'blockStep': 14836
            }),
            'event': 'OperationCreated',
            'logIndex': 0,
            'transactionIndex': 0,
            'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'),
            'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
            'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'),
            'blockNumber': 14836
        }),
        AttributeDict({
            'args': AttributeDict({
                'operationHash': b"\xbb1@\xd3lU\x8a\xe7\xc7\xfd2o\xd3\xc4\x94\x84\x0c\xf3~eN'`\x03x]\x8f\xbd\xad\x02\xb8\xa1",
                'params': AttributeDict({
                    'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
                    'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
                    'chainIdFrom': 440,
                    'chainIdTo': 1337,
                    'tokenName': 'allfeat',
                    'amount': 1000000000000000,
                    'nonce': 4,
                    'signature': b'\x8b\xa2\xd0;\xc2\x89\xb9f\xfb\xf5SZ\xca\x19>`cfT\xe58kvW\xb54f\xfeU\xcd\xb8\x1dB\xed\x1f1J\x86\x16\x0e\xf6(\xf5\xdb\xd4\x07qJ\x9b:I\x10\x0b\xd0Pq\x9aQ\xc8w\xd0\x9fn\xcd\x1c'
                }),
                'blockStep': 14840
            }),
            'event': 'OperationCreated',
            'logIndex': 0,
            'transactionIndex': 0,
            'transactionHash': HexBytes('0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962'),
            'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
            'blockHash': HexBytes('0xa776cd94ee4ba4e309d85636bace1831592dbb96d61658895caae9d7d3ec8756'),
            'blockNumber': 14840
        })
    ]


@pytest.fixture(scope="function")
def mock_w3_contract(mock_abi):
    w3 = Web3(EthereumTesterProvider())
    contract_address = "0x3aAde2dCD2Df6a8cAc689EE797591b2913658659"
    return w3.eth.contract(address=contract_address, abi=mock_abi)


@pytest.fixture
def example_bridge_task_action():
    """Create an example bridge task."""
    return BridgeTaskActionDTO(
        operation_hash=event_data.args['operationHash'].hex(),
        func_name="func_name",
        params=event_data.args['params'],
    )

@pytest.fixture(scope="function")
def mock_built_tx():
    return dict(
        nonce=1,
        maxFeePerGas=2000000000,
        maxPriorityFeePerGas=1000000000,
        gas=100000,
        to='0xabcdef1234567890abcdef1234567890abcdef12',
        value=1,
        data=b'',
    )

@pytest.fixture(scope="function")
def mock_signed_tx():
    # For info
    # transaction_dict = {
    #     'to': '0xF0109fC8DF283027b6285cc889F5aA624EaC1F55',
    #     'value': 1000000000,
    #     'gas': 2000000,
    #     'maxFeePerGas': 2000000000,
    #     'maxPriorityFeePerGas': 1000000000,
    #     'nonce': 0,
    #     'chainId': 1,
    #     'type': '0x2',  # the type is optional and, if omitted, will be interpreted based on the provided transaction parameters
    #     'accessList': (  # accessList is optional for dynamic fee transactions
    #         {
    #             'address': '0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae',
    #             'storageKeys': (
    #                 '0x0000000000000000000000000000000000000000000000000000000000000003',
    #                 '0x0000000000000000000000000000000000000000000000000000000000000007',
    #             )
    #         },
    #         {
    #             'address': '0xbb9bc244d798123fde783fcc1c72d3bb8c189413',
    #             'storageKeys': ()
    #         },
    #     )
    # }
    encoded_transaction = HexBytes('0x02f8e20180843b9aca008477359400831e848094f0109fc8df283027b6285cc889f5aa624eac1f55843b9aca0080f872f85994de0b295669a9fd93d5f28d9ec85e40f4cb697baef842a00000000000000000000000000000000000000000000000000000000000000003a00000000000000000000000000000000000000000000000000000000000000007d694bb9bc244d798123fde783fcc1c72d3bb8c189413c001a0b9ec671ccee417ff79e06e9e52bfa82b37cf1145affde486006072ca7a11cf8da0484a9beea46ff6a90ac76e7bbf3718db16a8b4b09cef477fb86cf4e123d98fde')
    hash = HexBytes('0xe85ce7efa52c16cb5c469c7bde54fbd4911639fdfde08003f65525a85076d915')
    signature_r = 84095564551732371065849105252408326384410939276686534847013731510862163857293
    signature_s = 32698347985257114675470251181312399332782188326270244072370350491677872459742
    signature_v = 1

    return SignedTransaction(
        rawTransaction=encoded_transaction,
        hash=hash,
        r=signature_r,
        s=signature_s,
        v=signature_v
    )


@pytest.fixture(scope="function")
def bridge_relayer_config():
    blockchain_config = {
        "rpc_url": "http://1.0.0.1:1111/",
        "project_id": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "pk": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "wait_block_validation": 2,
        "block_validation_second_per_block": 5,
        "smart_contract_address": "0x1212121212122121212121212121212121212121",
        "smart_contract_deployment_block": 0,
        "client": "",
    }

    blockchain_config.update({"abi": [{}], "chain_id": 1})
    return RelayerBlockchainConfigDTO(**blockchain_config)

@pytest.fixture(scope="function")
def contract_errors():
    return {
        '0x6997e49b': 'RelayerBase__BlockConfirmationNotReached',
        '0x127ad5d9': 'RelayerBase__CallerHasNotRole',
        '0xdd72e359': 'RelayerBase__InvalidOperationHash'
    }


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

@pytest.fixture(scope="function")
def mock_provider():
    mock_config = MagicMock(spec=Config)
    mock_web3 = MagicMock(spec=Web3)
    mock_w3_contract = MagicMock(spec=Contract)

    provider = RelayerBlockchainProvider()
    provider.w3 = mock_web3
    provider.w3_contract = mock_w3_contract
    provider.config = mock_config
    return provider

# --------------------------------------------------------------------
# T E S T S
# --------------------------------------------------------------------

# -------------------- init ------------------------------------------
def test_init(mock_provider):
    assert mock_provider.chain_id is None
    assert mock_provider.events == []
    assert mock_provider.filters == {}
    assert mock_provider.relay_blockchain_config == {}
    assert mock_provider.block_timestamps == {}
    assert mock_provider.min_scan_chunk_size == 10
    assert mock_provider.max_scan_chunk_size == 10000
    assert mock_provider.max_request_retries == 30
    assert mock_provider.request_retry_seconds == 3.0
    assert mock_provider.num_blocks_rescan_for_forks == 10
    assert mock_provider.chunk_size_decrease == 0.5
    assert mock_provider.chunk_size_increase == 2.0
    assert mock_provider.config is not None

# --------------------------------------------------------------------
# Private methods
# --------------------------------------------------------------------

# -------------------- _build_tx -------------------------------------
def test_build_tx(
    mock_provider, 
    example_bridge_task_action,
    mock_built_tx
):
    """
        Test _build_tx that returns the transaction as dict
    """
    class MockW3Contract:
        def __init__(self, **kwargs):
            pass
        def build_transaction(self, **kwargs):
            return mock_built_tx
    
    transaction = mock_provider._build_tx(
        func=MockW3Contract,
        params=example_bridge_task_action.params,
        account_address="0x0000000000000000000000000000000000000000",
        nonce=1,
    )
    assert transaction == mock_built_tx

def test_build_tx_raise_exception(
    mock_provider, 
    example_bridge_task_action,
):
    """
        Test _build_tx that raise RelayerBlockchainBuildTxError
    """
    class MockW3Contract:
        def __init__(self, **kwargs):
            pass
        def build_transaction(self, **kwargs):
            raise Exception('Error')
        
    with pytest.raises(RelayerBlockchainBuildTxError):
        mock_provider._build_tx(
            func=MockW3Contract,
            params=example_bridge_task_action.params,
            account_address="0x0000000000000000000000000000000000000000",
            nonce=1,
        )

def test_build_tx_raise_exception_manage_contract_error(
    mock_provider, 
    example_bridge_task_action,
    contract_errors,
):
    """
        Test _build_tx that raise RelayerBlockchainBuildTxError
    """
    mock_provider.errors = contract_errors
    class MockW3Contract:
        def __init__(self, **kwargs):
            pass
        def build_transaction(self, **kwargs):
            raise Exception(('0x6997e49b', '0x6997e49b'))
    
    expected = "Build transaction failed! error=('0x6997e49b', 'RelayerBase__BlockConfirmationNotReached')"

    with pytest.raises(RelayerBlockchainBuildTxError, match=re.escape(expected)):
        mock_provider._build_tx(
            func=MockW3Contract,
            params=example_bridge_task_action.params,
            account_address="0x0000000000000000000000000000000000000000",
            nonce=1,
        )

# -------------------- _sign_tx --------------------------------------
def test_sign_tx(
    mock_provider,
    mock_built_tx,
    mock_signed_tx
):
    """
        Test _sign_tx that returns the signed transaction instance SignedTransaction
    """
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.sign_transaction = MagicMock(
        return_value=mock_signed_tx
    )
    
    signed_tx = mock_provider._sign_tx(
        built_tx=mock_built_tx,
        account_key="0x0000000000000000000000000000000000000000"
    )
    assert type(signed_tx) is SignedTransaction

def test_sign_tx_raise_exception(
    mock_provider,
    mock_built_tx,
):
    """
        Test _sign_tx that raise RelayerBlockchainSignTxError
    """
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.sign_transaction = MagicMock(
        side_effect=Exception('Error')
    )
    
    with pytest.raises(RelayerBlockchainSignTxError):
        mock_provider._sign_tx(
            built_tx=mock_built_tx,
            account_key="0x0000000000000000000000000000000000000000"
        )

# -------------------- _send_raw_tx ----------------------------------
def test_send_raw_tx(
    mock_provider,
    mock_signed_tx
):
    """
        Test _send_raw_tx that returns the transaction hash as HexBytes
    """
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.send_raw_transaction = MagicMock(return_value=HexBytes(b'tx_hash'))
    
    tx_hash = mock_provider._send_raw_tx(signed_tx=mock_signed_tx)
    assert tx_hash == HexBytes(b'tx_hash')


def test_send_raw_tx_raise_exception(
    mock_provider,
    mock_signed_tx
):
    """
        Test _send_raw_tx that raise RelayerBlockchainSendRawTxError
    """
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.send_raw_transaction = MagicMock(side_effect=Exception('Error'))
    
    with pytest.raises(RelayerBlockchainSendRawTxError):
        mock_provider._send_raw_tx(signed_tx=mock_signed_tx)

# -------------------- _set_provider ---------------------------------
def test_set_provider(
    mock_provider,
    bridge_relayer_config
):
    """
        Test _set_provider that returns a Web3 instance
    """
    mock_provider.relay_blockchain_config = bridge_relayer_config
    assert type(mock_provider._set_provider()) is Web3

# -------------------- _set_contract ---------------------------------
def test_set_contract(
    mock_provider,
    mock_w3_contract,
    bridge_relayer_config
):
    """
        Test _set_contract that returns a Contract instance
    """
    mock_provider.relay_blockchain_config = bridge_relayer_config
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.contract = MagicMock(return_value=mock_w3_contract)

    assert isinstance(mock_provider._set_contract(), Contract)

# -------------------- _fetch_event_logs -----------------------------
def test_fetch_event_logs(
    mock_provider,
    mock_log_receipts,
    mock_event_datas
):
    """
        Test _fetch_event_logs that returns the event logs
    """
    mock_provider.w3.codec = MagicMock()
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.get_logs = MagicMock(return_value=[mock_log_receipts[0]])
    mock_event_type = MagicMock()
    mock_event_type._get_event_abi = MagicMock(spec=ABIEvent)

    with patch(f'{APP_PATH}.construct_event_filter_params') as mock_construct_event_filter_params:
        mock_construct_event_filter_params.return_value = (None, None)
        with patch(f'{APP_PATH}.get_event_data') as mock_get_event_data:
            mock_get_event_data.return_value = mock_event_datas[0]
            # act
            result = mock_provider._fetch_event_logs(
                event_type=mock_event_type,
                from_block=1,
                to_block=2
            )
            assert type(result) is list
            assert result == [mock_event_datas[0]]


# -------------------- _retry_web3_call ------------------------------
def test_retry_web3_call(
    mock_provider,
    mock_event_datas
):
    """
        Test _retry_web3_call that returns the end_block and the event logs
    """
    mock_fetch_event_logs = MagicMock(return_value=[mock_event_datas[0]])
    mock_event_type = MagicMock()
    mock_event_type._get_event_abi = MagicMock(spec=ABIEvent)
    
    (end_block, events) = mock_provider._retry_web3_call(
        fetch_event_logs=mock_fetch_event_logs,
        event_type=mock_event_type,
        start_block=1,
        end_block=2,
        retries=2,
        delay=0
    )
    assert end_block == 2
    assert events == [mock_event_datas[0]]

def test_retry_web3_call_manage_exception_but_returns_values(
    mock_provider,
    mock_event_datas
):
    """
        Test _retry_web3_call that returns the end_block and the event logs
    """
    retries_on_exception = 0
    def mock_fetch_event_logs(**args):
        nonlocal retries_on_exception
        if retries_on_exception <= 1:
            retries_on_exception += 1
            raise Exception('Error')
        return [mock_event_datas[0]]

    mock_event_type = MagicMock()
    mock_event_type._get_event_abi = MagicMock(spec=ABIEvent)
    
    (end_block, events) = mock_provider._retry_web3_call(
        fetch_event_logs=mock_fetch_event_logs,
        event_type=mock_event_type,
        start_block=1,
        end_block=2,
        retries=3,
        delay=0
    )
    assert end_block == 1
    assert events == [mock_event_datas[0]]

def test_retry_web3_call_with_exception(
    mock_provider,
    mock_event_datas
):
    """
        Test _retry_web3_call that raise RelayerFetchEventOutOfRetries
    """
    retries_on_exception = 0
    def mock_fetch_event_logs(**args):
        nonlocal retries_on_exception
        if retries_on_exception <= 1:
            retries_on_exception += 1
            raise Exception('Error')
        return [mock_event_datas[0]]
    mock_event_type = MagicMock()
    mock_event_type._get_event_abi = MagicMock(spec=ABIEvent)
    
    with pytest.raises(RelayerFetchEventOutOfRetries):
        mock_provider._retry_web3_call(
            fetch_event_logs=mock_fetch_event_logs,
            event_type=mock_event_type,
            start_block=1,
            end_block=2,
            retries=2,
            delay=0
        )

# -------------------- _create_event_data_dto ------------------------
def test_create_event_data_dto_raise_exception(
    mock_provider,
    mock_event_datas,
):
    """
        Test _create_event_data_dto that raise RelayerErrorBlockPending
    """
    mock_event_datas[0]['logIndex'] = None

    with pytest.raises(RelayerErrorBlockPending):
        mock_provider._create_event_data_dto(event=mock_event_datas[0])

def test_create_event_data_dto_returns_none(
    mock_provider,
    mock_event_datas,
):
    """
        Test _create_event_data_dto that returns None if block_datetime is None
    """
    mock_provider.chain_id = 1
    mock_provider.get_block_timestamp = MagicMock(return_value=None)
    event = mock_provider._create_event_data_dto(event=mock_event_datas[0])
    assert event is None

def test_create_event_data_dto(
    mock_provider,
    mock_event_datas,
):
    """
        Test _create_event_data_dto that returns the EventDTO
    """
    mock_provider.chain_id = 1
    mock_provider.get_block_timestamp = MagicMock(
        return_value=datetime(2024, 8, 7, 15, 9, 14, 607810)
    )
    event = mock_provider._create_event_data_dto(event=mock_event_datas[0])
    assert event.block_datetime == datetime(2024, 8, 7, 15, 9, 14, 607810)

# --------------------------------------------------------------------
# Public methods
# --------------------------------------------------------------------

# -------------------- connect_client --------------------------------
def test_connect_client(
    mock_provider,
    bridge_relayer_config,
    contract_errors
):
    """
        Test connect_client that 
          - set chain_id
          - get blockchain config
          - set Web3 instance
          - set Contract instance 
    """
    chain_id = 1
    mock_provider.config.get_blockchain_config = MagicMock(
        return_value=bridge_relayer_config
    )
    mock_provider.config.get_smart_contract_errors = MagicMock(
        return_value=contract_errors
    )
    mock_web3 = MagicMock(spec=Web3)
    mock_w3_contract = MagicMock(spec=Contract)
    mock_provider._set_provider = MagicMock(return_value=mock_web3)
    mock_provider._set_contract = MagicMock(return_value=mock_w3_contract)

    # act
    mock_provider.connect_client(chain_id)

    assert mock_provider.chain_id == chain_id
    assert mock_provider.relay_blockchain_config == bridge_relayer_config
    assert mock_provider.w3 == mock_web3
    assert mock_provider.w3_contract == mock_w3_contract
    assert mock_provider.errors == contract_errors

# -------------------- set_event_filter ------------------------------
def test_set_event_filter(
    mock_provider,
    event_filters
):
    """
        Test _set_event_filter that returns the event type
    """
    mock_provider.w3_contract.events = {
        'OperationCreated': {},
        'FeesDeposited': {},
        'FeesDepositConfirmed': {},
        'FeesLockedConfirmed': {},
        'FeesLockedAndDepositConfirmed': {},
        'OperationFinalized': {},
    }

    mock_provider.set_event_filter(events=event_filters)
    
def test_set_event_filter_raise_exception(
    mock_provider,
    event_filters
):
    """
        Test _set_event_filter that raise RelayerEventsNotFound
    """
    mock_provider.w3_contract.events = {
        'OperationCreated': {},
        'FeesDeposited': {},
    }

    with pytest.raises(RelayerEventsNotFound):
        mock_provider.set_event_filter(events=event_filters)

# -------------------- get_current_block_number ----------------------
def test_get_current_block_number(
    mock_provider,
):
    """
        Test _get_current_block_number that returns the current block number
    """
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.block_number = 1
    block_number = mock_provider.get_current_block_number()
    assert block_number == 1

# -------------------- client_version --------------------------------
def test_client_version(
    mock_provider,
):
    """
        Test _client_version that returns the client version
    """
    mock_provider.w3 = MagicMock()
    mock_provider.w3.client_version = '1.0.0'
    client_version = mock_provider.client_version()
    assert client_version == '1.0.0'

# -------------------- get_account_address ---------------------------
def test_get_account_address(
    mock_provider,
    bridge_relayer_config
):
    """
        Test _get_account_address that returns the account address
    """
    def from_key(pk):
       return LocalAccount()

    class LocalAccount:
        address = '0x0000000000000000000000000000000000000000'

    mock_provider.relay_blockchain_config = bridge_relayer_config
    mock_provider.w3 = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.from_key = MagicMock(
        return_value=from_key(bridge_relayer_config.pk)
    )
    # act
    account_address = mock_provider.get_account_address()
    assert account_address == '0x0000000000000000000000000000000000000000'

# -------------------- get_block_timestamp ---------------------------
def test_get_block_timestamp_raise_exception_1(
    mock_provider,
):
    """
        Test _get_block_timestamp that returns None with exception
    """
    mock_provider.w3 = MagicMock()
    mock_provider.w3.eth.get_block.side_effect = BlockNotFound('error')
    
    block_timestamp = mock_provider.get_block_timestamp(block_num=1)
    assert block_timestamp is None

def test_get_block_timestamp_raise_exception_2(
    mock_provider,
):
    """
        Test _get_block_timestamp that returns None with exception
    """
    mock_provider.w3 = MagicMock(spec=Web3)
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.get_block = MagicMock(return_value=123)
    
    block_timestamp = mock_provider.get_block_timestamp(block_num=1)
    assert block_timestamp is None

def test_get_block_timestamp_raise_exception_3(
    mock_provider,
):
    """
        Test _get_block_timestamp that returns None with exception
    """
    mock_provider.w3 = MagicMock(spec=Web3)
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.get_block = MagicMock(return_value={"timestamp": "123"})
    
    block_timestamp = mock_provider.get_block_timestamp(block_num=1)
    assert block_timestamp is None

def test_get_block_timestamp(
    mock_provider,
):
    """
        Test _get_block_timestamp that returns None with exception
    """
    mock_provider.w3 = MagicMock(spec=Web3)
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.get_block = MagicMock(return_value={"timestamp": 0})
    
    block_timestamp = mock_provider.get_block_timestamp(block_num=1)
    assert block_timestamp == datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)
# -------------------- scan ------------------------------------------
def test_scan(
    mock_provider,
    mock_event_datas,
    example_event_dto,
):
    """
        Test _scan that returns the block number
    """
    mock_provider.events = ['OperationCreated']
    mock_provider._retry_web3_call = MagicMock(return_value=(2, [mock_event_datas[0]]))
    mock_provider._create_event_data_dto = MagicMock(return_value=example_event_dto)  
    (
        events_dto, 
        new_end_block
    ) = mock_provider.scan(start_block=1, end_block=10)
    assert new_end_block == 2
    assert events_dto == [example_event_dto]

def test_scan_no_events_no_event_dto_list(
    mock_provider,
    mock_event_datas,
    example_event_dto,
):
    """
        Test _scan that returns the block number
    """
    mock_provider.events = []
    mock_provider._retry_web3_call = MagicMock(return_value=(2, [mock_event_datas[0]]))
    mock_provider._create_event_data_dto = MagicMock(return_value=example_event_dto)  
    (
        events_dto, 
        new_end_block
    ) = mock_provider.scan(start_block=1, end_block=10)
    assert new_end_block == 10
    assert events_dto == []

def test_scan_no_event_data_no_event_dto_list(
    mock_provider,
    example_event_dto,
):
    """
        Test _scan that returns the block number
    """
    mock_provider.events = ['OperationCreated']
    mock_provider._retry_web3_call = MagicMock(return_value=(2, []))
    mock_provider._create_event_data_dto = MagicMock(return_value=example_event_dto)  
    (
        events_dto, 
        new_end_block
    ) = mock_provider.scan(start_block=1, end_block=10)
    assert new_end_block == 2
    assert events_dto == []

def test_scan_no_event_dto_no_event_dto_llist(
    mock_provider,
    mock_event_datas,
):
    """
        Test _scan that returns the block number
    """
    mock_provider.events = ['OperationCreated']
    mock_provider._retry_web3_call = MagicMock(return_value=(2, [mock_event_datas[0]]))
    mock_provider._create_event_data_dto = MagicMock(return_value=None)  
    (
        events_dto, 
        new_end_block
    ) = mock_provider.scan(start_block=1, end_block=10)
    assert new_end_block == 2
    assert events_dto == []

def test_scan_event_data_is_noneno_event_dto_list(
    mock_provider,
):
    """
        Test _scan that returns the block number
    """
    mock_provider.events = ['OperationCreated']
    mock_provider._retry_web3_call = MagicMock(return_value=(2, [None]))
    mock_provider._create_event_data_dto = MagicMock(return_value=None)  
    (
        events_dto, 
        new_end_block
    ) = mock_provider.scan(start_block=1, end_block=10)
    assert new_end_block == 2
    assert events_dto == []


# -------------------- call_contract_func ----------------------------
def test_call_contract_func(
    mock_provider,
    example_bridge_task_action,
    bridge_relayer_config
):
    """
        Test _call_contract_func that returns the call result
    """
    class MockTxReceipt:
        transactionHash = HexBytes('0x123456')
        blockHash = HexBytes('0x123456')
        blockNumber = 123
        gasUsed = 777
        status = 1


    mock_provider.relay_blockchain_config = bridge_relayer_config
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.from_key = MagicMock()
    mock_provider.w3.eth.get_transaction_count = MagicMock()
    mock_provider.w3_contract.get_function_by_name = MagicMock()
    mock_provider._build_tx = MagicMock()
    mock_provider._sign_tx = MagicMock()
    mock_provider._send_raw_tx = MagicMock()
    mock_provider.w3.eth.wait_for_transaction_receipt = MagicMock(
        return_value=MockTxReceipt()
    )

    bridge_task_tx = mock_provider.call_contract_func(
        bridge_task_action_dto=example_bridge_task_action
    )
    assert bridge_task_tx.tx_hash == '0x123456'
    assert bridge_task_tx.block_hash == '0x123456'
    assert bridge_task_tx.block_number == 123
    assert bridge_task_tx.gas_used == 777
    assert bridge_task_tx.status == 1

def test_call_contract_func_raise_exception(
    mock_provider,
    example_bridge_task_action,
    bridge_relayer_config
):
    """
        Test call_contract_func that raise RelayerBlockchainFailedExecuteSmartContract
        with status = 0
    """
    class MockTxReceipt:
        transactionHash = HexBytes('0x123456')
        blockHash = HexBytes('0x123456')
        blockNumber = 123
        gasUsed = 777
        status = 0


    mock_provider.relay_blockchain_config = bridge_relayer_config
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.from_key = MagicMock()
    mock_provider.w3.eth.get_transaction_count = MagicMock()
    mock_provider.w3_contract.get_function_by_name = MagicMock()
    mock_provider._build_tx = MagicMock()
    mock_provider._sign_tx = MagicMock()
    mock_provider._send_raw_tx = MagicMock()
    mock_provider.w3.eth.wait_for_transaction_receipt = MagicMock(
        return_value=MockTxReceipt()
    )

    with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
        mock_provider.call_contract_func(
            bridge_task_action_dto=example_bridge_task_action
        )

def test_call_contract_func_raise_exception_2(
    mock_provider,
    example_bridge_task_action,
    bridge_relayer_config
):
    """
        Test call_contract_func that raise RelayerBlockchainFailedExecuteSmartContract
        with exception of any method called
    """
    mock_provider.relay_blockchain_config = bridge_relayer_config
    mock_provider.w3.eth = MagicMock()
    mock_provider.w3.eth.account = MagicMock()
    mock_provider.w3.eth.account.from_key = MagicMock()
    mock_provider.w3.eth.get_transaction_count = MagicMock()
    mock_provider.w3_contract.get_function_by_name = MagicMock()
    mock_provider._build_tx = MagicMock()
    mock_provider._sign_tx = MagicMock()
    mock_provider._send_raw_tx = MagicMock()
    mock_provider.w3.eth.wait_for_transaction_receipt = MagicMock(
        side_effect=Exception('Error')
    )

    with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
        mock_provider.call_contract_func(
            bridge_task_action_dto=example_bridge_task_action
        )