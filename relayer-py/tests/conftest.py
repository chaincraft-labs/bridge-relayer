import sys
import os
from hexbytes import HexBytes
import pytest
from dotenv import load_dotenv
from attributedict.collections import AttributeDict


TEST_ENV_FILE = ".env.test"
CHAIN_ID = 123
RPC_URL = "https://mock.test/fake_rpc_url:1234"
SMART_CONTRACT_ADDRESS = "0x11111a1aa11aaaa1aaaa111111a1111a1a1a111a"
GENESIS_BLOCK = 987
PROJECT_ID = "aaaa11a111a111a11a111aa1aaa1111a"
ABI_NAME = "abi_test"
WAIT_BLOCK_VALIDATION = 6
BLOCK_VALIDATION_SECOND_PER_BLOCK = 0
PK = "111aaa111aaa111aaa111aaaa111aaa111aaaa111aaaa111aaaa111aaa111aaa"
CLIENT = "middleware"
EVENT_SAMPLE = AttributeDict({
  'args': AttributeDict({
    'operationHash': '0xdc053a71d37822e8aa3f461c9e09f6fb37e9af9652d4e62f9197466806e62b5a',
    'params': AttributeDict({
      'from': '0x66F91393Be9C04039997763AEE11b47c5d04A486',
      'to': '0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11',
      'chainIdFrom': 80002,
      'chainIdTo': 440,
      'tokenName': 'AAA',
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
  "BLOCK_VALIDATION_SECOND_PER_BLOCK": BLOCK_VALIDATION_SECOND_PER_BLOCK,
  "PK": PK,
  "CLIENT": CLIENT,
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
    "block_key": "12345-0xb351dd79ccf7f10a514dadcedc37cc4b4b83050d393d0caf1dcc5e88bea5be0f-0"
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

EVENT_TASKS = {
    "9633a43eac9216ea58f17033f0a01f36ef4b17bf49bc2061ee0dd999fb291bcd": {
        "OperationCreated": {
            "chain_id": 1337,
            "block_key": "25633-0x8bcf687c57814f790bf690ae079efe1ad12e5e9746cc2e6228c99acb431ed20d-0",
            "status": "completed"
        },
        "FeesDeposited": {
            "chain_id": 440,
            "block_key": "42378-0x14b0149466dcf05cbeb47939659f486864741d1c40b32c39bd8f9648fd1a0960-0",
            "status": "completed"
        },
        "FeesDepositConfirmed": {
            "chain_id": 440,
            "block_key": "42390-0x8998ef6d3caf767c688069d310b0de25e541d4d48826d34f6e740276ad5ac119-0",
            "status": "completed"
        },
        "FeesLockedConfirmed": {
            "chain_id": 1337,
            "block_key": "25640-0xed4598e971a7fe86a6c838e5d61afde11b594e814275ddf8d53e020ce07cdaf8-0",
            "status": "completed"
        },
        "FeesLockedAndDepositConfirmed": {
            "chain_id": 1337,
            "block_key": "25641-0x912843ba699485be079e4341133d14598b0530c0520388549d1f8a554806f2ce-0",
            "status": "completed"
        },
        "OperationFinalized": {
            "chain_id": 4040,
            "block_key": "42394-0xdaa8fbb76a0c2ff3ff8de7e02b80e701df3e23122f63a43a5c024737e0303655-0",
            "status": "completed"
        }
    },
    "15c2424a47a2e3731250107bb1c92a30820e3f460338143ee5053d02e4112ed4": {
        "OperationCreated": {
            "chain_id": 1337,
            "block_key": "25709-0xfd748493d7b6ef51854a7667862454cb228a4de2624cc905bcad864f68f0f206-0",
            "status": "completed"
        },
        "FeesDeposited": {
            "chain_id": 440,
            "block_key": "42530-0xb6d6272d74076d91ee0539dd491c8a61da2177ff425794e77ab4e52ab018dafc-0",
            "status": "completed"
        },
        "FeesLockedConfirmed": {
            "chain_id": 1337,
            "block_key": "25716-0xd901b567b127eb062d4724f5ebcca214d1821500867fb384078cf99e5a41eab8-0",
            "status": "completed"
        },
        "FeesLockedAndDepositConfirmed": {
            "chain_id": 1337,
            "block_key": "25717-0x5b41135ed6b5fd3f79a5b0cecec1e530dffc749ba8746131f5b4723f0fe243be-0",
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

