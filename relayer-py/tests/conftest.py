import sys
import os
from hexbytes import HexBytes
import pytest
from dotenv import load_dotenv
# from web3.datastructures import AttributeDict
from attributedict.collections import AttributeDict


TEST_ENV_FILE = ".env.test"
CHAIN_ID = 123
RPC_URL = "https://mock.test/fake_rpc_url:1234"
SMART_CONTRACT_ADDRESS = "0x11111a1aa11aaaa1aaaa111111a1111a1a1a111a"
GENESIS_BLOCK = 987
PROJECT_ID = "aaaa11a111a111a11a111aa1aaa1111a"
ABI_NAME = "abi_test"
WAIT_BLOCK_VALIDATION = 6
PK = "111aaa111aaa111aaa111aaaa111aaa111aaaa111aaaa111aaaa111aaa111aaa"

EVENT_SAMPLE = AttributeDict({
  'args': AttributeDict({
    'operationHash': '0xdc053a71d37822e8aa3f461c9e09f6fb37e9af9652d4e62f9197466806e62b5a', 
    'params': AttributeDict({
      'addressFrom': '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
      'addressTo': '0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11', 
      'chainidFrom': 80002, 
      'chainidTo': 411, 
      'tokenFrom': '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
      'tokenTo': '0x0000000000000000000000000000000000000000', 
      'amount': 100, 
      'nonce': 123, 
      'signature': 'f2c298be000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000064d794e616d650000000000000000000000000000000000000000000000000000'
    }), 
    'blockStep': 7866062
  }),
  'event': 'TokensAndFeesLockedAndValidated', 
  'logIndex': 3, 
  'transactionIndex': 1, 
  'transactionHash': HexBytes('0xb351dd79ccf7f10a514dadcedc37cc4b4b83050d393d0caf1dcc5e88bea5be0f'), 
  'address': '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
  'blockHash': HexBytes('0x6bda9dc6b3e26f8972b75a45da645dfde50677335b40a7d217d8aee4b0b38b26'), 
  'blockNumber': 7866062
})


DATA_TEST = AttributeDict({
  "TEST_ENV_FILE": TEST_ENV_FILE,
  "CHAIN_ID": CHAIN_ID,
  "RPC_URL": RPC_URL,
  "SMART_CONTRACT_ADDRESS": SMART_CONTRACT_ADDRESS,
  "GENESIS_BLOCK": GENESIS_BLOCK,
  "PROJECT_ID": PROJECT_ID,
  "ABI_NAME": ABI_NAME,
  "WAIT_BLOCK_VALIDATION": WAIT_BLOCK_VALIDATION,
  "PK": PK,
  "TEST_ENV_VALUES": {
      "123_RPC_URL": RPC_URL,
      "123_SMART_CONTRACT_ADDRESS": SMART_CONTRACT_ADDRESS,
      "123_GENESIS_BLOCK": GENESIS_BLOCK,
      "123_PROJECT_ID": PROJECT_ID,
      "123_ABI": ABI_NAME,
  },
  "ABI": {
    'abi_test': [{'inputs': [{'internalType': 'address',
        'name': 'newOwner',
        'type': 'address'}],
      'name': 'changeOwner',
      'outputs': [],
      'stateMutability': 'nonpayable',
      'type': 'function'},
      {'inputs': [],
      'name': 'getOwner',
      'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
      'stateMutability': 'nonpayable',
      'type': 'function'},
      {'inputs': [], 'stateMutability': 'nonpayable', 'type': 'constructor'},
      {'anonymous': False,
      'inputs': [{'indexed': True,
        'internalType': 'address',
        'name': 'owner',
        'type': 'address'}],
      'name': 'OwnerGet',
      'type': 'event'},
      {'anonymous': False,
      'inputs': [{'indexed': True,
        'internalType': 'address',
        'name': 'oldOwner',
        'type': 'address'},
        {'indexed': True,
        'internalType': 'address',
        'name': 'newOwner',
        'type': 'address'}],
      'name': 'OwnerSet',
      'type': 'event'}]
  },
  "REGISTER_CONFIG": AttributeDict({
    "host": "https://fake_localhost",
    "port": "5672",
    "user": "fake_user",
    "password": "fake_password",
    "queue_name": "fake_queue_name",
  }),
  "EVENT_DTO": {
        "name": 'FakeEventName', 
        "data": {'eventAttributeName': '0x1111111111111111111111111111111111111111'}, 
    },
  "EVENT_DATA": {
        "event": 'FakeEventName', 
        "args": {'eventAttributeName': '0x1111111111111111111111111111111111111111'}, 
        "address": '0x2111111111111111111111111111111111111111',
        "logIndex": 1, 
        "transactionIndex": 1, 
        "transactionHash": HexBytes('0x2222222222222222222222222222222222222222222222222222222222222222'), 
        "blockHash": HexBytes('0x322222222222222222222222222222222222222222222222222222222222222'), 
        "blockNumber": 123456,
    },
  "EVENT_SAMPLE": EVENT_SAMPLE
  },
)


sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")


@pytest.fixture(scope="session")
def setup_module(tmp_path_factory):
    """Create .env file before testing."""
    temp_file = tmp_path_factory.mktemp("test") / TEST_ENV_FILE
    with temp_file.open(mode="w") as f:
        for key, value in DATA_TEST.TEST_ENV_VALUES.items(): # type: ignore
            f.write(f"{key}={value}\n")
    
    load_dotenv(dotenv_path=temp_file)
