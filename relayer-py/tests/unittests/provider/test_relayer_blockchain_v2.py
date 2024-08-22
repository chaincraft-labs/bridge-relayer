from datetime import datetime, timezone
import logging
from typing import List, Optional
from unittest.mock import MagicMock, PropertyMock, patch
from hexbytes import HexBytes
from attributedict.collections import AttributeDict
import pytest

from web3 import Web3
from eth_account.datastructures import SignedTransaction
from web3.contract.contract import Contract
from web3.exceptions import BlockNotFound
from web3.types import (
    EventData,
    LogReceipt,
    BlockData,
)

from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO, 
)
from src.relayer.domain.relayer import BridgeTaskDTO, BridgeTaskTxResult
from src.relayer.provider.relayer_blockchain_web3_v2 import (
    RelayerBlockchainProvider
)
from src.relayer.domain.exception import (
    RelayerErrorBlockPending,
    RelayerEventsNotFound,
    RelayerFetchEventOutOfRetries,
    RelayerBlockchainFailedExecuteSmartContract,
    RelayerClientVersionError,
)


# SAMPLE_ETH_GET_EVENT_DATAS: List[EventData] = [
#     AttributeDict({
#         'args': AttributeDict({
#             'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4',
#             'params': AttributeDict({
#                 'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'chainIdFrom': 440,
#                 'chainIdTo': 1337,
#                 'tokenName': 'allfeat',
#                 'amount': 1000000000000000,
#                 'nonce': 3,
#                 'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
#             }),
#             'blockStep': 14836
#         }),
#         'event': 'OperationCreated',
#         'logIndex': 0,
#         'transactionIndex': 0,
#         'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'),
#         'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
#         'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'),
#         'blockNumber': 14836
#     }),
#     AttributeDict({
#         'args': AttributeDict({
#             'operationHash': b"\xbb1@\xd3lU\x8a\xe7\xc7\xfd2o\xd3\xc4\x94\x84\x0c\xf3~eN'`\x03x]\x8f\xbd\xad\x02\xb8\xa1",
#             'params': AttributeDict({
#                 'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'chainIdFrom': 440,
#                 'chainIdTo': 1337,
#                 'tokenName': 'allfeat',
#                 'amount': 1000000000000000,
#                 'nonce': 4,
#                 'signature': b'\x8b\xa2\xd0;\xc2\x89\xb9f\xfb\xf5SZ\xca\x19>`cfT\xe58kvW\xb54f\xfeU\xcd\xb8\x1dB\xed\x1f1J\x86\x16\x0e\xf6(\xf5\xdb\xd4\x07qJ\x9b:I\x10\x0b\xd0Pq\x9aQ\xc8w\xd0\x9fn\xcd\x1c'
#             }),
#             'blockStep': 14840
#         }),
#         'event': 'OperationCreated',
#         'logIndex': 0,
#         'transactionIndex': 0,
#         'transactionHash': HexBytes('0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962'),
#         'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
#         'blockHash': HexBytes('0xa776cd94ee4ba4e309d85636bace1831592dbb96d61658895caae9d7d3ec8756'),
#         'blockNumber': 14840
#     })
# ]

#SAMPLE_ETH_GET_EVENT_DATAS_PENDING: List[EventData] = [
#     AttributeDict({
#         'args': AttributeDict({
#             'operationHash': b'~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4',
#             'params': AttributeDict({
#                 'from': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'to': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
#                 'chainIdFrom': 440,
#                 'chainIdTo': 1337,
#                 'tokenName': 'allfeat',
#                 'amount': 1000000000000000,
#                 'nonce': 3,
#                 'signature': b'\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c'
#             }),
#             'blockStep': 14836
#         }),
#         'event': 'OperationCreated',
#         'logIndex': None,
#         'transactionIndex': 0,
#         'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'),
#         'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
#         'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'),
#         'blockNumber': 14836
#     })
# ]

# SAMPLE_EVENT_FILTER_PARAMS = {
#     'topics': ['0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333'], 
#     'fromBlock': 14835, 
#     'toBlock': 14841
# }

# SAMPLE_ETH_GET_LOGS: List[LogReceipt] = [
#     AttributeDict({
#         'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
#         'topics': [HexBytes('0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333')], 
#         'data': HexBytes('0x7e87776dbaf8294ccf33d838d00e781ee6f6f4c12fb42d1267003089bb9987b4000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000039f400000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000000000000000000000000000000000000000001b80000000000000000000000000000000000000000000000000000000000000539000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000038d7ea4c68000000000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000001400000000000000000000000000000000000000000000000000000000000000007616c6c66656174000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000041bf24e366b1b28332554020d0f7dc8ada16b0517570e6822c4aaa000573b769635440e2e7fa16f72bfcf8aa6e25e47c3a4876287fb9945429484bc1c725f694841c00000000000000000000000000000000000000000000000000000000000000'), 
#         'blockNumber': 14836, 
#         'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'), 
#         'transactionIndex': 0, 
#         'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'), 
#         'logIndex': 0, 
#         'removed': False
#     }), 
#     AttributeDict({
#         'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b', 
#         'topics': [HexBytes('0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333')], 
#         'data': HexBytes('0xbb3140d36c558ae7c7fd326fd3c494840cf37e654e276003785d8fbdad02b8a1000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000039f800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c800000000000000000000000000000000000000000000000000000000000001b80000000000000000000000000000000000000000000000000000000000000539000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000038d7ea4c68000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000001400000000000000000000000000000000000000000000000000000000000000007616c6c666561740000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000418ba2d03bc289b966fbf5535aca193e60636654e5386b7657b53466fe55cdb81d42ed1f314a86160ef628f5dbd407714a9b3a49100bd050719a51c877d09f6ecd1c00000000000000000000000000000000000000000000000000000000000000'), 
#         'blockNumber': 14840, 
#         'transactionHash': HexBytes('0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962'), 
#         'transactionIndex': 0, 
#         'blockHash': HexBytes('0xa776cd94ee4ba4e309d85636bace1831592dbb96d61658895caae9d7d3ec8756'), 
#         'logIndex': 0, 
#         'removed': False
#     })
# ]

# SAMPLE_GET_EVENT_ABI = {
#     "anonymous": False,
#     "inputs": [
#         {
#             "indexed": False,
#             "internalType": "bytes32",
#             "name": "operationHash",
#             "type": "bytes32",
#         },
#         {
#             "components": [
#                 {"internalType": "address", "name": "from", "type": "address"},
#                 {"internalType": "address", "name": "to", "type": "address"},
#                 {"internalType": "uint256", "name": "chainIdFrom", "type": "uint256"},
#                 {"internalType": "uint256", "name": "chainIdTo", "type": "uint256"},
#                 {"internalType": "string", "name": "tokenName", "type": "string"},
#                 {"internalType": "uint256", "name": "amount", "type": "uint256"},
#                 {"internalType": "uint256", "name": "nonce", "type": "uint256"},
#                 {"internalType": "bytes", "name": "signature", "type": "bytes"},
#             ],
#             "indexed": False,
#             "internalType": "struct RelayerBase.OperationParams",
#             "name": "params",
#             "type": "tuple",
#         },
#         {
#             "indexed": False,
#             "internalType": "uint256",
#             "name": "blockStep",
#             "type": "uint256",
#         },
#     ],
#     "name": "OperationCreated",
#     "type": "event",
# }

# -----------------------------------------------------------------
# F I X T U R E S
# -----------------------------------------------------------------

@pytest.fixture(scope="function")
def events():
    return [
        'OperationCreated',
        'FeesLockedConfirmed',
        'FeesLockedAndDepositConfirmed',
        'FeesDeposited',
        'FeesDepositConfirmed',
        'OperationFinalized'
    ]

def deep_copy(obj):
    if isinstance(obj, dict):
        return {k: deep_copy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_copy(item) for item in obj]
    elif isinstance(obj, AttributeDict):
        return AttributeDict({k: deep_copy(v) for k, v in obj.items()})
    else:
        return obj

@pytest.fixture(autouse=True)
def disable_logging():
    # Disable logging during tests
    logging.disable(logging.CRITICAL)
    yield
    # Enable loggin after tests
    logging.disable(logging.NOTSET)

@pytest.fixture(scope="function")
def provider(events):
    provider = RelayerBlockchainProvider()
    provider.connect_client(chain_id=123)
    provider.set_event_filter(events=events)
    return provider

@pytest.fixture(scope="function")
def event_datas():
    SAMPLE_ETH_GET_EVENT_DATAS: List[EventData] = [
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

    # data = SAMPLE_ETH_GET_EVENT_DATAS.copy()
    return SAMPLE_ETH_GET_EVENT_DATAS

@pytest.fixture(scope="function")
def event_data_pending():
    # data = SAMPLE_ETH_GET_EVENT_DATAS_PENDING.copy()
    # return data
    SAMPLE_ETH_GET_EVENT_DATAS_PENDING: List[EventData] = [
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
            'logIndex': None,
            'transactionIndex': 0,
            'transactionHash': HexBytes('0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd'),
            'address': '0x8613A4029EaA95dA61AE65380aC2e7366451bF2b',
            'blockHash': HexBytes('0x2e8712c4ecb88731917889f0f398080a0913d938187e219b290ce28118b39d06'),
            'blockNumber': 14836
        })
    ]

    return SAMPLE_ETH_GET_EVENT_DATAS_PENDING

@pytest.fixture(scope="function")
def filter_params():
    # data = SAMPLE_EVENT_FILTER_PARAMS.copy()
    # return data
    SAMPLE_EVENT_FILTER_PARAMS = {
        'topics': ['0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333'], 
        'fromBlock': 14835, 
        'toBlock': 14841
    }
    return SAMPLE_EVENT_FILTER_PARAMS


@pytest.fixture(scope="function")
def get_logs():
    # data = SAMPLE_ETH_GET_LOGS.copy()
    # return data
    SAMPLE_ETH_GET_LOGS: List[LogReceipt] = [
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
    return SAMPLE_ETH_GET_LOGS

@pytest.fixture(scope="function")
def get_event_abi():
    # data = SAMPLE_GET_EVENT_ABI.copy()
    # return data
    SAMPLE_GET_EVENT_ABI = {
        "anonymous": False,
        "inputs": [
            {
                "indexed": False,
                "internalType": "bytes32",
                "name": "operationHash",
                "type": "bytes32",
            },
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "chainIdFrom", "type": "uint256"},
                    {"internalType": "uint256", "name": "chainIdTo", "type": "uint256"},
                    {"internalType": "string", "name": "tokenName", "type": "string"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "indexed": False,
                "internalType": "struct RelayerBase.OperationParams",
                "name": "params",
                "type": "tuple",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "blockStep",
                "type": "uint256",
            },
        ],
        "name": "OperationCreated",
        "type": "event",
    }
    return SAMPLE_GET_EVENT_ABI

@pytest.fixture
def mock_w3():
    mock = MagicMock(spec=Web3)
    mock.eth = MagicMock()
    return mock

@pytest.fixture
def mock_config():
    return MagicMock()

@pytest.fixture
def mock_abi():
    return MagicMock()

@pytest.fixture
def mock_provider(mock_w3, mock_config, mock_abi):
    with patch('src.relayer.config.config.get_blockchain_config', return_value=mock_config):
        with patch('src.relayer.config.config.get_abi', return_value=mock_abi):
            provider = RelayerBlockchainProvider()
            provider.w3 = mock_w3
            return provider
        
@pytest.fixture
def bridge_task_dto():
    return BridgeTaskDTO(
        func_name="func_name",
        params={"key": "value"},
    )

@pytest.fixture
def get_blockchain_config():
    config = RelayerBlockchainConfigDTO(
        chain_id=123, 
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=0,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        genesis_block=123456789, 
        abi=[{}], 
        client='middleware'
    )
    return config        
# -----------------------------------------------------------------
# T E S T S
# -----------------------------------------------------------------
def test_relayer_blockchain_provider_init():
    """
        Test init RelayerBlockchainProvider with default parameters and values
    """
    provider = RelayerBlockchainProvider(
        min_scan_chunk_size=10,
        max_scan_chunk_size=10000, 
        max_request_retries=30, 
        request_retry_seconds=3.0,
        num_blocks_rescan_for_forks=10,
        chunk_size_decrease=0.5,
        chunk_size_increase=2.0,
    )

    assert provider.events == []
    assert provider.filters == {}
    assert provider.relay_blockchain_config == {}
    assert provider.min_scan_chunk_size == 10
    assert provider.max_scan_chunk_size == 10000
    assert provider.max_request_retries == 30
    assert provider.request_retry_seconds == 3.0
    assert provider.num_blocks_rescan_for_forks == 10
    assert provider.chunk_size_decrease == 0.5
    assert provider.chunk_size_increase == 2.0

def test_connect_client(provider):
    """
        Test connect_client that 
          - set chain_id
          - get blockchain config
          - set Web3 instance
          - set Contract instance 
    """
    provider = RelayerBlockchainProvider()
    chain_id = 123
    provider.connect_client(chain_id)

    assert provider.chain_id == 123
    assert provider.relay_blockchain_config != {}
    assert str(provider.relay_blockchain_config) == 'ChainId123'
    assert isinstance(provider.w3, Web3)
    assert isinstance(provider.w3_contract, Contract)

def test_set_event_filter_success(provider, events):
    """
        Test set_event_filter that set a list of events
        list[type[BaseContractEvent]]
    """
    provider.set_event_filter(events=events)

    assert len(provider.events) == len(events)
    assert provider.events[0].event_name == events[0]
    assert provider.events[5].event_name == events[5]

def test_set_event_filter_raise_exception_with_invalid_events(provider, events):
    """
        Test set_event_filter that raises BridgeRelayerEventsNotFound
        with an invalid event name provided
    """
    with pytest.raises(RelayerEventsNotFound):
        provider.set_event_filter(events=['invalid_event_name'])

def test_set_provider_returns_web3_instance(provider):
    """
        Test _set_provider that returns a Web3 instance.
    """
    assert isinstance(provider._set_provider(), Web3)

def test_set_contract_returns_Contract_instance(provider):
    """
        Test _set_contract that returns a Contract instance.
    """
    provider._set_contract()
    assert isinstance(provider._set_contract(), Contract)

def test_get_suggested_scan_end_block(mock_provider, mock_w3):
    """
        Test get_suggested_scan_end_block that returns the last block minus 1
    """
    mock_w3.eth.block_number = 100
    assert mock_provider.get_suggested_scan_end_block() == 99

def test_get_block_timestamp(mock_provider, mock_w3):
    """
        Test get_block_timestamp that return the block's timestamp
    """
    block_num = 1
    mock_block_data = {
        "timestamp": 1609459200
    }
    mock_w3.eth.get_block.return_value = mock_block_data
    assert mock_provider.get_block_timestamp(block_num) == \
        datetime.fromtimestamp(1609459200, timezone.utc)

def test_get_block_timestamp_exception(mock_provider, mock_w3):
    """
        Test get_block_timestamp that returns None when block not found
    """
    block_num = 1
    mock_w3.eth.get_block.side_effect = BlockNotFound("Block not found")
    assert mock_provider.get_block_timestamp(block_num) is None

def test_get_block_when(mock_provider, mock_w3):
    """
        Test get_block_when that returns the block timestamp
    """
    block_num = 1
    block_timestamps = {}
    mock_block_data = {
        "timestamp": 1609459200
    }
    mock_w3.eth.get_block.return_value = mock_block_data

    assert mock_provider.get_block_when(block_num, block_timestamps) == \
        datetime.fromtimestamp(1609459200, timezone.utc)
    assert block_timestamps[block_num] == \
        datetime.fromtimestamp(1609459200, timezone.utc)

def test_estimate_next_chunk_size(mock_provider):
    """
        Test estimate_next_chunk_size that returns the optinal cunk size 
        depending on events received.
    """
    current_chuck_size = 10
    event_found_count = 0
    assert mock_provider.estimate_next_chunk_size(current_chuck_size, event_found_count) == 20

    event_found_count = 1
    assert mock_provider.estimate_next_chunk_size(current_chuck_size, event_found_count) == 10

    current_chuck_size = 1
    event_found_count = 0
    assert mock_provider.estimate_next_chunk_size(current_chuck_size, event_found_count) == 10

    current_chuck_size = 10001
    event_found_count = 0
    assert mock_provider.estimate_next_chunk_size(current_chuck_size, event_found_count) == 10000

def test_fetch_event_logs_returns_event_datas(
    provider, 
    get_logs, 
    event_datas, 
    filter_params
):
    """
        Test fetch_event_logs that returns event datas
    """
    with patch.object(provider.w3.eth, 'get_logs', return_value=get_logs) as mock_get_logs:
        # act
        result_event_datas = provider.fetch_event_logs(
            event_type=provider.events[0],
            from_block=filter_params['fromBlock'],
            to_block=filter_params['toBlock']
        )

        assert result_event_datas == event_datas
        mock_get_logs.assert_called_with(
            filter_params=filter_params
        )

def test_fetch_event_logs_returns_empty_list_with_no_logs(
    provider, 
    filter_params
):
    """
        Test fetch_event_logs that returns an empty list with no logs from get_logs
    """
    with patch.object(provider.w3.eth, 'get_logs', return_value=[]) as mock_get_logs:
        # act
        result_event_datas = provider.fetch_event_logs(
            event_type=provider.events[0],
            from_block=filter_params['fromBlock'],
            to_block=filter_params['toBlock']
        )

        assert result_event_datas == []
        mock_get_logs.assert_called_with(
            filter_params=filter_params
        )

def test_fetch_event_logs_raises_exception_out_of_retries(
    provider, 
    filter_params
):
    """
        Test _retry_web3_call that raise BridgeRelayerFetchEventOutOfRetries 
        with out of retries
    """
    fetch_event_logs = MagicMock(side_effect=Exception("fake fetch exception"))

    with pytest.raises(
        RelayerFetchEventOutOfRetries,
        match="Fetch event error! Out of retries!"
    ):
        provider._retry_web3_call(
            fetch_event_logs=fetch_event_logs,
            event_type=provider.event_filter[0],
            start_block=filter_params['fromBlock'],
            end_block=filter_params['toBlock'],
            retries=2,
            delay=0
        )
    
def test_fetch_event_logs_returns_event(provider, filter_params, event_datas):
    """
        Test _retry_web3_call that returns events and the end_block
    """
    fetch_event_logs = MagicMock(return_value=event_datas)
    (
        end_block, 
        events
    ) = provider._retry_web3_call(
        fetch_event_logs=fetch_event_logs,
        event_type=provider.event_filter[0],
        start_block=filter_params['fromBlock'],
        end_block=filter_params['toBlock'],
        retries=2,
        delay=0
    )
    assert end_block == filter_params['toBlock']
    assert events == event_datas

def test_scan_chunk_raise_exception_block_idx_is_none_pending(
    provider, 
    event_data_pending
):
    """
        Test scan_chunk that raises BridgeRelayerErrorBlockPending if block 
        is pending => logIndex = None
    """
    with patch.object(provider, '_retry_web3_call') as mock_retry_web3_call:
        mock_end_block = 20
        mock_events = event_data_pending
        mock_retry_web3_call.return_value = (mock_end_block, mock_events)

        with pytest.raises(
            RelayerErrorBlockPending,
            match="Somehow tried to scan a pending block"
        ):
            provider.scan(
                start_block=0, 
                end_block=20, 
            )

def test_scan_chunk_success(provider, event_datas):
    """
        Test scan_chunk 
    """
    events = ['OperationCreated']
    provider.set_event_filter(events=events)
        
    with patch.object(provider, '_retry_web3_call') as mock_retry_web3_call:
        mock_end_block = 20
        mock_events = event_datas
        mock_retry_web3_call.return_value = (mock_end_block, mock_events)
        mock_end_block_timestamp = datetime(2024, 8, 7, 15, 9, 14, 607810)
        provider.get_block_when = MagicMock(return_value=mock_end_block_timestamp)
        
        # act
        event_datas_dto = provider.scan(start_block=0, end_block=20)

        # assert
        assert event_datas_dto.end_block == mock_end_block
        assert event_datas_dto.end_block_timestamp == mock_end_block_timestamp
        # assert event_datas_dto.event_data_keys == [
        #     '14836-0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd-0',
        #     '14840-0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962-0',
        # ]
        assert mock_retry_web3_call.call_count == 1
        provider.get_block_when.assert_called_with(
            block_num=mock_end_block,
            block_timestamps={}
        )
        assert event_datas_dto.event_datas[0].block_datetime == mock_end_block_timestamp
        assert event_datas_dto.event_datas[0].event == event_datas[0]
        assert event_datas_dto.event_datas[1].event == event_datas[1]


def test_scan_chunk_success_with_events_empty_list(provider, event_datas):
    """
        Test scan_chunk 
    """
    events = ['OperationCreated']
    provider.set_event_filter(events=events)
        
    with patch.object(provider, '_retry_web3_call') as mock_retry_web3_call:
        mock_end_block = 20
        mock_events = [None]
        mock_retry_web3_call.return_value = (mock_end_block, mock_events)
        mock_end_block_timestamp = datetime(2024, 8, 7, 15, 9, 14, 607810)
        provider.get_block_when = MagicMock(return_value=mock_end_block_timestamp)

        # act
        event_datas_dto = provider.scan(start_block=0, end_block=20)
        assert event_datas_dto.end_block == mock_end_block
        assert event_datas_dto.end_block_timestamp == mock_end_block_timestamp
        # assert event_datas_dto.event_data_keys == []

def test_scan_chunk_success_with_datetime_is_none(provider, event_datas):
    """
        Test scan_chunk 
    """
    events = ['OperationCreated']
    provider.set_event_filter(events=events)
        
    with patch.object(provider, '_retry_web3_call') as mock_retry_web3_call:
        mock_end_block = 20
        mock_events = event_datas
        mock_retry_web3_call.return_value = (mock_end_block, mock_events)
        mock_end_block_timestamp = None
        provider.get_block_when = MagicMock(return_value=mock_end_block_timestamp)

        # act
        event_datas_dto = provider.scan(start_block=0, end_block=20)
        assert event_datas_dto.end_block == mock_end_block
        assert event_datas_dto.end_block_timestamp == mock_end_block_timestamp
        # assert event_datas_dto.event_data_keys == []




def test_call_contract_func_success(
    get_blockchain_config,
    mock_provider, 
    bridge_task_dto
):
    """
        Test call_contract_func that returns a BridgeTaskTxResult instance
    """
    mock_provider.relay_blockchain_config = get_blockchain_config
    mock_provider.w3_contract = MagicMock()

    tx = mock_provider.call_contract_func(bridge_task_dto=bridge_task_dto)
    assert isinstance(tx, BridgeTaskTxResult)

def test_call_contract_func_failed(
    get_blockchain_config,
    mock_provider, 
    bridge_task_dto
):
    """
        Test call_contract_func that raise RelayerBlockchainFailedExecuteSmartContract
    """
    mock_provider.relay_blockchain_config = get_blockchain_config
    mock_provider.w3_contract = MagicMock()
    mock_provider._send_raw_tx = MagicMock(side_effect=Exception('Test Exception'))

    with pytest.raises(
        RelayerBlockchainFailedExecuteSmartContract,
        match="Test Exception"
    ):
        mock_provider.call_contract_func(bridge_task_dto=bridge_task_dto)

def test_get_block_number_success(mock_provider, mock_w3):
    """
        Test get_block_number that returns block number
    """
    mock_w3.eth.block_number = 100   
    assert mock_provider.get_block_number() == 100
    
def test_build_tx_raise_exception(mock_provider, bridge_task_dto):
    """
        Test _build_tx that raise RelayerBlockchainFailedExecuteSmartContract
    """
    class Callback:
        def __init__(self, **kwargs):
            pass
        def build_transaction(self, **kwargs):
            raise Exception('Test Exception')

    with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
        mock_provider._build_tx(
            func=Callback,
            bridge_task_dto=bridge_task_dto,
            account_address="0x0000000000000000000000000000000000000000",
            nonce=1,
        )

def test_build_tx_success(mock_provider, bridge_task_dto):
    """
        Test _build_tx that returns the transaction as dict
    """
    class Callback:
        def __init__(self, **kwargs):
            pass
        def build_transaction(self, **kwargs):
            return {"k": "v"}
    
    transaction = mock_provider._build_tx(
        func=Callback,
        bridge_task_dto=bridge_task_dto,
        account_address="0x0000000000000000000000000000000000000000",
        nonce=1,
    )
    assert transaction == {"k": "v"}

def test_sign_tx_raise_exception(mock_provider, mock_w3):
    """
        Test _sign_tx that raise RelayerBlockchainFailedExecuteSmartContract
    """
    mock_w3.eth.account = MagicMock()
    mock_w3.eth.account.sign_transaction = MagicMock(side_effect=Exception('Test Exception'))

    with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
        mock_provider._sign_tx(
            built_tx={"k": "v"},
            account_key="0x0000000000000000000000000000000000000000"
        )

def test_sign_tx_success(mock_provider, mock_w3):
    """
        Test _sign_tx that returns the signed transaction
    """
    mock_w3.eth.account = MagicMock()
    mock_w3.eth.account.sign_transaction = MagicMock(
        spec=SignedTransaction, return_value='signed_tx'
    )
    
    signed_tx = mock_provider._sign_tx(
        built_tx={"k": "v"},
        account_key="0x0000000000000000000000000000000000000000"
    )
    assert signed_tx == 'signed_tx'

def test_send_raw_tx_raise_exception(mock_provider, mock_w3):
    """
        Test _send_raw_tx that raise RelayerBlockchainFailedExecuteSmartContract
    """
    mock_w3.eth = MagicMock()
    mock_w3.eth.send_raw_transaction = MagicMock(side_effect=Exception('Test Exception'))

    with pytest.raises(RelayerBlockchainFailedExecuteSmartContract):
        mock_provider._send_raw_tx(signed_tx="signed_tx")

def test_send_raw_tx_success(mock_provider, mock_w3):
    """
        Test _send_raw_tx that returns the transaction hash
    """
    mock_signed_tx = MagicMock()
    mock_signed_tx._sign_tx = MagicMock()
        
    mock_w3.eth = MagicMock()
    mock_w3.eth.send_raw_transaction = MagicMock(return_value=HexBytes(b'tx_hash'))
    
    tx_hash = mock_provider._send_raw_tx(signed_tx=mock_signed_tx)
    assert tx_hash == HexBytes(b'tx_hash')

def test_get_account_address_success(mock_provider, mock_w3, get_blockchain_config):
    """
        Test get_account_address that returns the account address
    """ 
    mock_provider.relay_blockchain_config = get_blockchain_config
    mock_account = MagicMock()
    mock_account.address = "0x0000000000000000000000000000000000000000"

    mock_w3.eth.account = MagicMock()
    mock_w3.eth.account.from_key = MagicMock(return_value=mock_account)
    
    address = mock_provider.get_account_address()
    assert address =="0x0000000000000000000000000000000000000000"

def test_client_version_success(mock_provider, mock_w3):
    """
        Test client_version that returns the client version
    """
    mock_w3.client_version = "777"
    assert mock_provider.client_version() == "777"

def test_client_version_failed(mock_provider, mock_w3):
    """
        Test client_version that raise RelayerClientVersionError
    """
    type(mock_w3).client_version = PropertyMock(
        side_effect=Exception('Test exception'))

    with pytest.raises(RelayerClientVersionError):
        mock_provider.client_version()
    
def test_is_contract_deployed_returns_true(mock_provider, mock_w3):
    """
        Test is_contract_deployed that returns True
    """
    mock_provider.w3_contract = MagicMock()
    mock_w3.eth.get_code = MagicMock()
    assert mock_provider.is_contract_deployed() is True 

def test_is_contract_deployed_returns_false(mock_provider, mock_w3):
    """
        Test is_contract_deployed that returns False
    """
    mock_provider.w3_contract = MagicMock()
    mock_w3.eth.get_code = MagicMock(side_effect=Exception('Test Exception'))
    assert mock_provider.is_contract_deployed() is False