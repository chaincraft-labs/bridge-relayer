import sys
import os
from hexbytes import HexBytes
import pytest
from dotenv import load_dotenv
from attributedict.collections import AttributeDict


# This is an EvenData object from Web3 library
# operationHash = '0xabcdef0000000000000000000000000000123456'
# signature = 0x123456abcdef0000000000000000000000123456
EVENT_DATA_SAMPLE = AttributeDict({
  'args': AttributeDict({
    'operationHash': b'\xab\xcd\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x124V',
    'params': AttributeDict({
      'from': '0x1234567890abcdef1234567890abcdef12345678',
      'to': '0xabc123def4567890abcdef1234567890abcdef12',
      'chainIdFrom': 1,
      'chainIdTo': 2,
      'tokenName': 'AAA',
      'amount': 100,
      'nonce': 123,
      'signature': b'\x124V\xab\xcd\xef\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x124V'
    }),
    'blockStep': 123111
  }),
  'event': 'TokensAndFeesLockedAndValidated',
  'logIndex': 3,
  'transactionIndex': 1,
  'transactionHash': HexBytes('0x5555555555555555555555555555555555555555555555555555555555555555'), 
  'address': '0x1234567890abcdef1234567890abcdef12345678',
  'blockHash': HexBytes('0x666666666666666666666666666666666666666666666666666666666666666'), 
  'blockNumber': 123123
})


TEST_ENV_FILE = ".env.test"
DATA_TEST = AttributeDict({
  "TEST_ENV_FILE": ".env.test",
  "CHAIN_ID": 123,
  "RPC_URL": "https://mock.test/fake_rpc_url:1234",
  "SMART_CONTRACT_ADDRESS": "0x11111a1aa11aaaa1aaaa111111a1111a1a1a111a",
  "SMART_CONTRACT_DEPLOYMENT_BLOCK": 987,
  "PROJECT_ID": "aaaa11a111a111a11a111aa1aaa1111a",
  "ABI_NAME": "abi_test",
  "WAIT_BLOCK_VALIDATION": 6,
  "BLOCK_VALIDATION_SECOND_PER_BLOCK": 0,
  "PK": "111aaa111aaa111aaa111aaaa111aaa111aaaa111aaaa111aaaa111aaa111aaa",
  "CLIENT": "middleware",
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
  },
)

EVENT_TASKS = {
    "0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234": {
        "OperationCreated": {
            "chain_id": 1,
            "block_key": "25633-0x0000000000000000000000000000000000000000000000000000000000000001-0",
            "status": "completed"
        },
        "FeesDeposited": {
            "chain_id": 2,
            "block_key": "42378-0x0000000000000000000000000000000000000000000000000000000000000001-0",
            "status": "completed"
        },
        "FeesDepositConfirmed": {
            "chain_id": 2,
            "block_key": "42390-0x0000000000000000000000000000000000000000000000000000000000000002-0",
            "status": "completed"
        },
        "FeesLockedConfirmed": {
            "chain_id": 1,
            "block_key": "25640-0x0000000000000000000000000000000000000000000000000000000000000002-0",
            "status": "completed"
        },
        "FeesLockedAndDepositConfirmed": {
            "chain_id": 1,
            "block_key": "25641-0x0000000000000000000000000000000000000000000000000000000000000003-0",
            "status": "completed"
        },
        "OperationFinalized": {
            "chain_id": 2,
            "block_key": "42394-0x0000000000000000000000000000000000000000000000000000000000000003-0",
            "status": "completed"
        }
    },
    "0xabcedf0123456789abcdef123456789abcdef123456789abcdef123456789abc": {
        "OperationCreated": {
            "chain_id": 1,
            "block_key": "25709-0x0000000000000000000000000000000000000000000000000000000000000004-0",
            "status": "completed"
        },
        "FeesDeposited": {
            "chain_id": 2,
            "block_key": "42530-0x0000000000000000000000000000000000000000000000000000000000000004-0",
            "status": "completed"
        },
        "FeesLockedConfirmed": {
            "chain_id": 1,
            "block_key": "25716-0x0000000000000000000000000000000000000000000000000000000000000005-0",
            "status": "completed"
        },
        "FeesLockedAndDepositConfirmed": {
            "chain_id": 1,
            "block_key": "25717-0x0000000000000000000000000000000000000000000000000000000000000006-0",
            "status": "completed"
        }
    }
}

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

