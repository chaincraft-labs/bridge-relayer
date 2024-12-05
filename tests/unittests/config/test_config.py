import os
import pathlib
import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from src.relayer.config.config import (
    FILE_ABI_DEV,
    FILE_ABI_PRD,
    FILE_ENV_DEV,
    FILE_ENV_PRD,
    FILE_TOML_DEV,
    FILE_TOML_PRD,
    Config,
    Singleton,
    convert_error_to_hex,
    get_root_path,
    read_abis,
)
from src.relayer.domain.config import (
    EventRuleConfig, 
    RelayerBlockchainConfigDTO, 
    RelayerRegisterConfigDTO,
)

from src.relayer.domain.exception import (
    RelayerConfigABIFileMissing,
    RelayerConfigABIAttributeMissing,
    RelayerConfigBlockchainDataMissing,
    RelayerConfigError,
    RelayerConfigEventRuleKeyError,
    RelayerConfigRegisterDataMissing,
    RelayerConfigReplacePlaceholderTypeError,
    RelayerConfigTOMLFileMissing,
)

mock_abi = {
    "1": {"abi": "abi_content_for_chain_1"},
    "2": {"abi": "abi_content_for_chain_2"}
}

MODULE_PATH = 'src.relayer.config.config'

# --------------------------------------------------------------------
# F I X T U R E S
# --------------------------------------------------------------------

@pytest.fixture
def mock_abi_file_content():
    return json.dumps(mock_abi)

@pytest.fixture
def toml_file():
    return "test_config.toml"

@pytest.fixture
def toml_content():
    return """
    [relayer_blockchain]
    chainid1 = {key = "value"}

    [relayer_register]
    port = "8080"
    """

@pytest.fixture
def template_content():
    return """
    key = "{{ ENV_VAR }}"
    """

@pytest.fixture
def env_var_value():
    return "replaced_value"

@pytest.fixture
def blockchain_config_data():
    return {
        "relayer_blockchain": {
            "chainid1": {
                "rpc_url": 'https://fake.rpc_url.org',
                "project_id": 'ABCDEF123456789',
                "pk": 'abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567',
                "wait_block_validation": 6,
                "block_validation_second_per_block": 12,
                "smart_contract_address": '0x1234567890abcdef1234567890abcdef12345678',
                "smart_contract_deployment_block": 123456789,
                "abi": [{}],
                "client": 'middleware'
            }
        }
    }

@pytest.fixture
def blockchain_config_invalid_data():
    return {
        "relayer_blockchain": {
            "chainid1": {
                "key": 'value',
                
            }
        }
    }

@pytest.fixture
def register_config_data():
    return {
        "relayer_register": {
            "host": "localhost",
            "port": 1234,
            "user": "guest",
            "password": "guest",
            "queue_name": "fake.bridge.relayer.dev",
        }
    }

@pytest.fixture
def register_config_invalid_data():
    return {
        "relayer_register": {
            "key": "value",
        }
    }

@pytest.fixture
def relayer_event_rule():
    return {
        "relayer_event_rules": {
            "fakeEvent": {
                "origin": "chainIdFrom",
                "has_block_finality": True,
                "chain_func_name": "chainIdTo",
                "func_name": "fake_function_name",
                "func_condition": "fakeCondition",
                "depends_on": "fakeEventDependsOn",
            },
        }
    }

@pytest.fixture
def relayer_event_rule_invalid():
    return {
        "relayer_event_rules": {
            "key": "value",
        }
    }


@pytest.fixture(scope="function")
def bridge_relayer_config():
    return {
        "environment": {"mode": "dev", "data_path": "data", "repository": "bridge.dev"},
        "relayer_blockchain": {
            "ChainId1": {
                "rpc_url": "http://1.0.0.1:1111/",
                "project_id": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "pk": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "wait_block_validation": 2,
                "block_validation_second_per_block": 5,
                "smart_contract_address": "0x1212121212122121212121212121212121212121",
                "smart_contract_deployment_block": 0,
                "client": "",
            },
            "ChainId2": {
                "rpc_url": "http://1.0.0.2:2222/",
                "project_id": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "pk": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "wait_block_validation": 2,
                "block_validation_second_per_block": 5,
                "smart_contract_address": "0x3434343434343434343434343434343434343434",
                "smart_contract_deployment_block": 0,
                "client": "middleware",
            },
        },
        "relayer_register": {
            "host": "localhost",
            "port": "5672",
            "user": "guest",
            "password": "guest",
            "queue_name": "bridge.relayer.dev",
        },
        "relayer_event_rules": {
            "OperationCreated": {
                "origin": "chainIdFrom",
                "has_block_finality": True,
                "chain_func_name": "chainIdTo",
                "func_name": "sendFeesLockConfirmation",
                "depends_on": "FeesDeposited",
            },
            "FeesDeposited": {
                "origin": "chainIdTo",
                "has_block_finality": True,
                "chain_func_name": "chainIdTo",
                "func_name": "sendFeesLockConfirmation",
                "depends_on": "OperationCreated",
            },
            "FeesDepositConfirmed": {
                "origin": "chainIdTo",
                "has_block_finality": False,
                "chain_func_name": "chainIdFrom",
                "func_name": "receiveFeesLockConfirmation",
            },
            "FeesLockedConfirmed": {
                "origin": "chainIdFrom",
                "has_block_finality": False,
                "chain_func_name": "chainIdFrom",
                "func_name": "confirmFeesLockedAndDepositConfirmed",
            },
            "FeesLockedAndDepositConfirmed": {
                "origin": "chainIdFrom",
                "has_block_finality": False,
                "chain_func_name": "chainIdTo",
                "func_name": "completeOperation",
            },
            "OperationFinalized": {
                "origin": "chainIdTo",
                "has_block_finality": False,
                "chain_func_name": "chainIdFrom",
                "func_name": "receivedFinalizedOperation",
            },
        },
    }

@pytest.fixture(scope="function")
def abis():
    return {
        "1": [
            {

            }
        ],
        "2": [
            {

            }
        ],
    }

@pytest.fixture(scope="function")
def abis_data():
    return {
        "1": [
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
            },
            {
                "inputs": [],
                "name": "RelayerBase__BlockConfirmationNotReached",
                "type": "error"
            },
            {
                "inputs": [
                    {
                        "internalType": "string",
                        "name": "role",
                        "type": "string"
                    }
                ],
                "name": "RelayerBase__CallerHasNotRole",
                "type": "error"
            },
            {
                "inputs": [],
                "name": "RelayerBase__InvalidOperationHash",
                "type": "error"
            },
        ],
        "2": [
            {

            }
        ],
    }

# --------------------------------------------------------------------
# T E S T S
# --------------------------------------------------------------------
# Test root path
# --------------------------------------------------------------------
@patch("src.relayer.config.config.__file__", "/mocked/path/to/src/relayer/config/config.py")
def test_get_root_path():
    """
        Test root path determination.
    """
    expected_path = pathlib.Path("/mocked/path/to")

    assert get_root_path() == expected_path

# --------------------------------------------------------------------
# is_dev_env
# --------------------------------------------------------------------
@pytest.mark.parametrize("dev_env_value, expected", [
    ("True", True),
    ("False", False),
    (None, True),
])
@patch.dict(os.environ, {}, clear=True)
def test_is_dev_env_return_expected_bool(dev_env_value, expected):
    """
        Test environment determination based on DEV_ENV variable.
    """
    if dev_env_value is not None:
        os.environ["DEV_ENV"] = dev_env_value
    
    from src.relayer.config.config import is_dev_env
    assert is_dev_env() == expected

# --------------------------------------------------------------------
# load_env_file
# --------------------------------------------------------------------
@pytest.mark.parametrize("dev_env_value, expected", [
    ("True", FILE_ENV_DEV),
    ("False", FILE_ENV_PRD),
    (None, FILE_ENV_PRD),
])
@patch(f"{MODULE_PATH}.load_dotenv")
def test_load_env_file_returns_expected_file(
    mock_load_dotenv, 
    dev_env_value, 
    expected
):
    """
        Test loading the .env file according to the environment.
    """
    if dev_env_value is not None:
        os.environ["DEV_ENV"] = dev_env_value
    else:
        os.environ.pop("DEV_ENV", None)

    from src.relayer.config.config import load_env_file

    load_env_file()
    mock_load_dotenv.assert_called_with(expected)

    if "DEV_ENV" in os.environ:
        del os.environ["DEV_ENV"]

# --------------------------------------------------------------------
# get_toml_file
# --------------------------------------------------------------------
@pytest.mark.parametrize("dev_env_value, expected", [
    ("True", FILE_TOML_DEV),
    ("False", FILE_TOML_PRD),
    (None, FILE_TOML_PRD),
])
@patch(f"{MODULE_PATH}.load_env_file")
def test_get_toml_file_returns_expected_file(mock_load_env_file, dev_env_value, expected):
    """
        Test getting the TOML file name according to the environment.
    """
    if dev_env_value is not None:
        os.environ["DEV_ENV"] = dev_env_value
    from src.relayer.config.config import get_toml_file

    assert get_toml_file() == expected
    mock_load_env_file.assert_called_once()

# --------------------------------------------------------------------
# get_abi_file
# --------------------------------------------------------------------
@pytest.mark.parametrize("dev_env_value, expected", [
    ("True", FILE_ABI_DEV),
    ("False", FILE_ABI_PRD),
    (None, FILE_ABI_PRD),
])
def test_get_abi_file_returns_expected_file(dev_env_value, expected):
    if dev_env_value is not None:
        os.environ["DEV_ENV"] = dev_env_value

    from src.relayer.config.config import get_abi_file
    assert get_abi_file() == expected

# --------------------------------------------------------------------
# get_config_content
# --------------------------------------------------------------------
@patch(f"{MODULE_PATH}.pathlib.Path.open")
def test_get_config_content_success(mock_open, toml_file, toml_content):
    """
        Test successful retrieval of TOML file content.
    """
    mock_open.return_value.__enter__.return_value.read.return_value = toml_content
    from src.relayer.config.config import get_config_content

    assert get_config_content(toml_file) == toml_content

@patch(f"{MODULE_PATH}.pathlib.Path.open", side_effect=FileNotFoundError)
def test_get_config_content_missing(mock_open, toml_file):
    """
        Test exception raised when TOML file is missing.
    """
    from src.relayer.config.config import get_config_content
    from src.relayer.domain.exception import RelayerConfigTOMLFileMissing

    with pytest.raises(RelayerConfigTOMLFileMissing):
        get_config_content(toml_file)

# --------------------------------------------------------------------
# replace_placeholders
# --------------------------------------------------------------------
@patch.dict(os.environ, {"ENV_VAR": "replaced_value"})
def test_replace_placeholders_success(template_content, env_var_value):
    """
        Test successful replacement of placeholders with environment variables.
    """
    from src.relayer.config.config import replace_placeholders

    replaced_content = replace_placeholders(template_content)
    assert "key = \"replaced_value\"" in replaced_content

@pytest.mark.parametrize("config_content", [
    (True),
    (False),
    (None),
    ([123]),
    (123),
    ({"k": 123}),
])
@patch.dict(os.environ, {}, clear=True)
def test_replace_placeholders_type_error(config_content):
    """
        Test exception raised when placeholder replacement fails.
        Only str permits
    """
    from src.relayer.config.config import replace_placeholders
    from src.relayer.domain.exception import RelayerConfigReplacePlaceholderTypeError

    with pytest.raises(RelayerConfigReplacePlaceholderTypeError):
        replace_placeholders(config_content)

# --------------------------------------------------------------------
# get_bridge_relayer_config
# --------------------------------------------------------------------
@patch(f"{MODULE_PATH}.get_toml_file", return_value="test_config.toml")
@patch(f"{MODULE_PATH}.get_config_content")
@patch(f"{MODULE_PATH}.replace_placeholders")
def test_get_bridge_relayer_config_success(
    mock_replace_placeholders, 
    mock_get_config_content, 
    mock_get_toml_file, 
    toml_content
):
    """
        Test successful retrieval of bridge relayer config.
    """
    mock_get_config_content.return_value = toml_content
    mock_replace_placeholders.return_value = toml_content

    from src.relayer.config.config import get_bridge_relayer_config
    config = get_bridge_relayer_config()

    assert isinstance(config, dict)
    assert "relayer_blockchain" in config

@pytest.mark.parametrize("exception", [
    RelayerConfigTOMLFileMissing,
    RelayerConfigReplacePlaceholderTypeError
])
@patch(f"{MODULE_PATH}.get_toml_file", return_value="test_config.toml")
@patch(f"{MODULE_PATH}.get_config_content")
@patch(f"{MODULE_PATH}.replace_placeholders")
def test_get_bridge_relayer_config_raise_exception(
    mock_replace_placeholders, 
    mock_get_config_content, 
    mock_get_toml_file, 
    toml_content,
    exception
):
    """
        Test successful retrieval of bridge relayer config.
    """
    if exception == RelayerConfigTOMLFileMissing:
        mock_get_config_content.side_effect = exception
        mock_replace_placeholders.return_value = toml_content
    else:
        mock_get_config_content.return_value = toml_content
        mock_replace_placeholders.side_effect = exception

    from src.relayer.config.config import get_bridge_relayer_config

    with pytest.raises(RelayerConfigError):
        get_bridge_relayer_config()


# --------------------------------------------------------------------
# read_abis
# --------------------------------------------------------------------
@patch(f"{MODULE_PATH}.get_abi_file", return_value="mocked_abi.json")
@patch("pathlib.Path.open", new_callable=mock_open, read_data='{"key": "value"}')
def test_read_abis_success(mock_open_file, mock_get_abi_file):
    """
    Test that read_abis reads the ABI file and returns the correct content.
    """
    expected_abi = {"key": "value"}
    result = read_abis()

    mock_open_file.assert_called_once_with("r")
    assert result == expected_abi

@patch(f"{MODULE_PATH}.get_abi_file", return_value="mocked_abi.json")
@patch("pathlib.Path.open", side_effect=FileNotFoundError)
def test_read_abis_file_not_found(mock_open_file, mock_get_abi_file):
    """
    Test that read_abis raises RelayerConfigABIFileMissing if the file is not found.
    """
    with pytest.raises(RelayerConfigABIFileMissing):
        read_abis()

    mock_open_file.assert_called_once_with("r")

@patch(f"{MODULE_PATH}.get_abi_file", return_value="mocked_abi.json")
@patch("pathlib.Path.open", new_callable=mock_open, read_data='{"wrong_key": "value"}')
def test_read_abis_key_error(mock_open_file, mock_get_abi_file):
    """
    Test that read_abis raises RelayerConfigABIAttributeMissing if a required key is missing.
    """
    with patch("json.loads", side_effect=KeyError("missing_key")):
        with pytest.raises(RelayerConfigABIAttributeMissing):
            read_abis()

    mock_open_file.assert_called_once_with("r")


def test_convert_error_to_hex():
    """Test convert_error_to_hex"""
    expected = '0x6997e49b'
    error_name = 'RelayerBase__BlockConfirmationNotReached'
    assert convert_error_to_hex(error_name) == expected


# -------------------------------------------
# Config class
# -------------------------------------------
@patch(f"{MODULE_PATH}.get_bridge_relayer_config", side_effect=RelayerConfigError)
@patch(f"{MODULE_PATH}.read_abis", return_value={})
def test_config_init_raise_exception_1(
    mock_read_abis, 
    mock_bridge_relayer_config
):
    """
        Test that the Config raise exception.

        get_bridge_relayer_config raise RelayerConfigError
    """
    Singleton._instances = {}
    with pytest.raises(RelayerConfigError):
        Config()

@pytest.mark.parametrize("exception", [
    RelayerConfigABIFileMissing,
    RelayerConfigABIAttributeMissing
])
@patch(f"{MODULE_PATH}.get_bridge_relayer_config", return_value={})
@patch(f"{MODULE_PATH}.read_abis")
def test_config_init_raise_exception_2(
    mock_read_abis, 
    mock_bridge_relayer_config,
    exception,
):
    """
        Test that the Config raise exception.

        read_abis raise RelayerConfigABIFileMissing
    """
    mock_read_abis.side_effect = exception
    with pytest.raises(exception):
        Config()


@patch(f"{MODULE_PATH}.read_abis", return_value={"1": {"abi": "value1"}, "2": {"abi": "value2"}})
@patch(f"{MODULE_PATH}.get_bridge_relayer_config", return_value={"some_key": "some_value"})
def test_config_singleton(mock_get_bridge_relayer_config, mock_read_abis):
    """
    Test that Config is a singleton, and that the get_bridge_relayer_config
    and read_abis functions are called correctly during instantiation.
    """
    config1 = Config()
    config2 = Config()

    assert config1 is config2

    mock_get_bridge_relayer_config.assert_called_once()
    mock_read_abis.assert_called_once()

    assert config1.bridge_relayer_config == {"some_key": "some_value"}
    assert config1.abi == {"1": {"abi": "value1"}, "2": {"abi": "value2"}}


#
# ------------------- get_abi -------------------
def test_get_abi_success(
    bridge_relayer_config,
    abis,
):
    """
    Test that get_abi returns the correct content.
    """
    config = Config()
    config.bridge_relayer_config = bridge_relayer_config
    config.abi = abis

    chain_id = 1
    assert config.get_abi(chain_id=chain_id) == abis[str(chain_id)]
    
def test_get_abi_success_raise_exception_1(
    bridge_relayer_config,
    abis,
):
    """
    Test that get_abi returns the correct content.

    Raises RelayerConfigABIFileMissing
    """
    config = Config()
    config.bridge_relayer_config = bridge_relayer_config
    config.abi = {}

    with pytest.raises(RelayerConfigABIAttributeMissing):
        config.get_abi(chain_id=1)

# ------------------- get_blockchain_config -------------------

@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_blockchain_config_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis
):
    """
        Test get_blockchain_config.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    config.get_abi = MagicMock()
    config.get_abi.return_value = abis["1"]
    
    result = config.get_blockchain_config(chain_id=1)

    config.get_abi.assert_called_once_with(chain_id=1)
    assert type(result) is RelayerBlockchainConfigDTO
    assert result.chain_id == 1
    assert result.rpc_url == bridge_relayer_config['relayer_blockchain']['ChainId1']['rpc_url']
    assert result.project_id == bridge_relayer_config['relayer_blockchain']['ChainId1']['project_id']
    assert result.pk == bridge_relayer_config['relayer_blockchain']['ChainId1']['pk']
    assert result.wait_block_validation == bridge_relayer_config['relayer_blockchain']['ChainId1']['wait_block_validation']
    assert result.block_validation_second_per_block == bridge_relayer_config['relayer_blockchain']['ChainId1']['block_validation_second_per_block']
    assert result.smart_contract_address == bridge_relayer_config['relayer_blockchain']['ChainId1']['smart_contract_address']
    assert result.smart_contract_deployment_block == bridge_relayer_config['relayer_blockchain']['ChainId1']['smart_contract_deployment_block']
    assert result.client == bridge_relayer_config['relayer_blockchain']['ChainId1']['client']
    assert result.abi == abis["1"]

@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_blockchain_config_raise_exception(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis
):
    """
        Test get_blockchain_config raise RelayerConfigBlockchainDataMissing.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    config.get_abi = MagicMock()
    config.get_abi.return_value = abis["1"]

    with pytest.raises(RelayerConfigBlockchainDataMissing):
        config.get_blockchain_config(chain_id=1111)

@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_blockchain_config_raise_exception_2(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis
):
    """
        Test get_blockchain_config raise RelayerConfigBlockchainDataMissing.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    config.get_abi = MagicMock()
    config.get_abi.return_value = abis["1"]

    with pytest.raises(RelayerConfigBlockchainDataMissing):
        config.get_blockchain_config(chain_id=b'1111')
    
# ------------------- get_register_config -------------------
@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_register_config_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis,
):
    """
        Test get_register_config.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    result = config.get_register_config()

    assert type(result) is RelayerRegisterConfigDTO
    assert result.host == bridge_relayer_config['relayer_register']['host']
    assert result.port == bridge_relayer_config['relayer_register']['port']
    assert result.user == bridge_relayer_config['relayer_register']['user']
    assert result.password == bridge_relayer_config['relayer_register']['password']
    assert result.queue_name == bridge_relayer_config['relayer_register']['queue_name']


def test_get_register_config_raise_exception():
    """
        Test get_register_config raise RelayerConfigRegisterDataMissing.
    """
    Config._instances = {}
    config = Config()
    config.bridge_relayer_config = {}

    with pytest.raises(RelayerConfigRegisterDataMissing):
        config.get_register_config()

# ------------------- get_relayer_event_rule -------------------
@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_relayer_event_rule_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis,
):
    """
        Test get_relayer_event_rule.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config
    event_name = "OperationCreated"


    config = Config()
    result = config.get_relayer_event_rule(event_name=event_name)

    assert type(result) is EventRuleConfig
    assert result.event_name == event_name
    assert result.origin == bridge_relayer_config["relayer_event_rules"][event_name]["origin"]
    assert result.has_block_finality == bridge_relayer_config["relayer_event_rules"][event_name]["has_block_finality"]
    assert result.chain_func_name == bridge_relayer_config["relayer_event_rules"][event_name]["chain_func_name"]
    assert result.func_condition is None
    assert result.depends_on == bridge_relayer_config["relayer_event_rules"][event_name]["depends_on"]

def test_get_relayer_event_rule_raise_exception():
    """
        Test get_relayer_event_rule raise RelayerConfigEventRuleKeyError
    """
    Config._instances = {}
    config = Config()
    config.bridge_relayer_config = {}

    with pytest.raises(RelayerConfigEventRuleKeyError):
        config.get_relayer_event_rule("OperationCreated")

# ------------------- get_relayer_events -------------------
@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_relayer_events_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis,
):
    """
        Test get_relayer_events.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    result = config.get_relayer_events()

    assert result == [
        'OperationCreated', 
        'FeesDeposited', 
        'FeesDepositConfirmed', 
        'FeesLockedConfirmed', 
        'FeesLockedAndDepositConfirmed', 
        'OperationFinalized'
    ]

def test_get_relayer_events_raise_exception():
    """
        Test get_relayer_events raise RelayerConfigEventRuleKeyError
    """
    Config._instances = {}
    config = Config()
    config.bridge_relayer_config = {}

    with pytest.raises(RelayerConfigEventRuleKeyError):
        config.get_relayer_events()

# ------------------- get_data_path -------------------

@patch(f"{MODULE_PATH}.get_root_path")
@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_data_path_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    mock_get_root_path,
    bridge_relayer_config,
    abis,
):
    """
        Test get_data_path.
    """
    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config
    fake_path = pathlib.Path("fake_path")
    mock_get_root_path.return_value = fake_path

    config = Config()
    result = config.get_data_path()

    assert result == fake_path / bridge_relayer_config['environment']['data_path']

@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_repository_name_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis
):
    """Test get_repository_name"""

    Config._instances = {}
    mock_read_abis.return_value = abis
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config

    config = Config()
    result = config.get_repository_name()

    assert result == bridge_relayer_config['environment']['repository']



@patch(f"{MODULE_PATH}.get_bridge_relayer_config")
@patch(f"{MODULE_PATH}.read_abis")
def test_get_smart_contract_errors_success(
    mock_read_abis,
    mock_get_bridge_relayer_config,
    bridge_relayer_config,
    abis_data
):
    """Test get_repository_name"""
    expected = {
        '0x6997e49b': 'RelayerBase__BlockConfirmationNotReached',
        '0x127ad5d9': 'RelayerBase__CallerHasNotRole',
        '0xdd72e359': 'RelayerBase__InvalidOperationHash'
    },

    Config._instances = {}
    mock_read_abis.return_value = abis_data
    mock_get_bridge_relayer_config.return_value = bridge_relayer_config
    config = Config()
    config.get_smart_contract_errors(chain_id=1) == expected
