import importlib
import os
import sys
from unittest.mock import patch
import pytest

from src.relayer.domain.config import (
    EventRuleConfig,
    RelayerBlockchainConfigDTO, 
    RelayerRegisterConfigDTO,
)
from src.relayer.domain.exception import (
    BridgeRelayerConfigABIAttributeMissing, 
    BridgeRelayerConfigABIFileMissing, 
    BridgeRelayerConfigBlockchainDataMissing,
    BridgeRelayerConfigEventRuleKeyError,
    BridgeRelayerConfigRegisterDataMissing, 
    BridgeRelayerConfigReplacePlaceholderTypeError, 
    BridgeRelayerConfigTOMLFileMissing
)

from src.relayer.config.config import load_env_file

# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
@pytest.fixture(scope="function")
def config():
    os.environ['DEV_ENV'] = "True"
    if 'src.relayer.config.config' in sys.modules:
        importlib.reload(sys.modules['src.relayer.config.config'])
    import src.relayer.config.config as config
    return config

@pytest.fixture(scope="function")
def blockchain_config():
    config = RelayerBlockchainConfigDTO(
        chain_id=123, 
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=12,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        genesis_block=123456789, 
        abi=[{}], 
        client='middleware'
    )
    return config

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
def config_prod():
    os.environ['DEV_ENV'] = "False"
    if 'src.relayer.config.config' in sys.modules:
        importlib.reload(sys.modules['src.relayer.config.config'])
    import src.relayer.config.config as config
    return config

# Clean up the environment variable after tests
def teardown_function():
    if 'DEV_ENV' in os.environ:
        del os.environ['DEV_ENV']

pytest.fixture(autouse=True)(teardown_function)

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_get_blockchain_config_returns_dto_with_chain_id(config, blockchain_config):
    """
        Test get_blockchain_config returns a RelayerBlockchainConfigDTO DTO.
    """
    with patch('src.relayer.config.config.get_blockchain_config', return_value=blockchain_config):
        chain_id = 123
        blockchain_config_dto = config.get_blockchain_config(chain_id=chain_id)
        assert str(blockchain_config_dto) == f"ChainId{chain_id}"
        assert isinstance(blockchain_config_dto, RelayerBlockchainConfigDTO)
        assert blockchain_config_dto.chain_id == chain_id
        assert blockchain_config_dto.rpc_url ==  "https://fake.rpc_url.org"
        assert blockchain_config_dto.smart_contract_address == "0x1234567890abcdef1234567890abcdef12345678"
        assert blockchain_config_dto.genesis_block == 123456789
        assert blockchain_config_dto.block_validation_second_per_block == 12
        assert blockchain_config_dto.wait_block_validation == 6
        assert blockchain_config_dto.client == 'middleware'
        assert blockchain_config_dto.project_id == 'JMFW2926FNFKRMFJF1FNNKFNKNKHENFL'
        assert blockchain_config_dto.pk == 'abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567'
        assert blockchain_config_dto.abi == [{}]
    
def test_get_blockchain_config_raise_exception_with_bad_chain_id(config):
    """
        Test get_blockchain_config raises 
        BridgeRelayerConfigBlockchainDataMissing with missing positional 
        arguments.
    """
    with pytest.raises(BridgeRelayerConfigBlockchainDataMissing):
        config.get_blockchain_config(chain_id=0)
    
def test_get_register_config_returns_dto_with(config, register_config):
    """
        Test get_register_config returns a RelayerRegisterConfigDTO DTO.
    """
    with patch('src.relayer.config.config.get_register_config', return_value=register_config):
        register_config_dto = config.get_register_config()
        assert isinstance(register_config_dto, RelayerRegisterConfigDTO)
        assert register_config_dto.host == "localhost"
        assert register_config_dto.port == 5672
        assert register_config_dto.user == "guest"
        assert register_config_dto.queue_name == "bridge.relayer.dev"

    
def test_get_register_config_raise_exception_with_data_missing(config):
    """
        Test get_register_config raises 
        BridgeRelayerConfigRegisterDataMissing with missing positional 
        arguments.
    """
    with patch('src.relayer.config.config._get_bridge_relayer_config'):
        with pytest.raises(BridgeRelayerConfigRegisterDataMissing):
            config.get_register_config()

def test_bridge_relayer_config_envi_is_dev(config):
    """
        Test bridge_relayer_config is set to dev env.
    """
    assert config.is_dev_env() is True

# ----------------------------------------------------------
# Internal fonctions
# ----------------------------------------------------------
@patch('src.relayer.config.config.load_dotenv')
def test_load_env_file_dev(mock_load_dotenv):
    # Set the environment variable to simulate dev environment
    os.environ['DEV_ENV'] = 'True'

    # Call the function
    load_env_file()

    # Assert that load_dotenv was called with the dev file
    mock_load_dotenv.assert_any_call(".env.config.dev")
    mock_load_dotenv.assert_any_call(".env.config.prod")

@patch('src.relayer.config.config.load_dotenv')
def test_load_env_file_prod(mock_load_dotenv):
    # Set the environment variable to simulate prod environment
    os.environ['DEV_ENV'] = 'False'

    # Call the function
    load_env_file()

    # Assert that load_dotenv was called with the prod file
    mock_load_dotenv.assert_any_call(".env.config.prod")


def test_get_toml_file_returns_prod_env(config_prod):
    """
        Test get_toml_file that returns the toml_file for prod env.
    """
    assert config_prod.get_toml_file() == config_prod.FILE_TOML_PRD
    
def test_get_config_content_raise_exception_toml_file_missing(config):
    """
        Test get_config_content that raises BridgeRelayerConfigTOMLFileMissing 
        if file is missing.
    """
    toml_file: str = "missing_file"
    with pytest.raises(BridgeRelayerConfigTOMLFileMissing):
        config.get_config_content(toml_file)

@pytest.mark.parametrize("config_content", [
    (True),
    (123),
    (None),
    ({"k": "v"}),
    ([1, "2", True, None])
])
def test_replace_placeholders_raise_exception_with_bad_content(
    config, 
    config_content
):
    """
        Test replace_placeholders that raises 
        BridgeRelayerConfigReplacePlaceholderTypeError with bad_content.
    """
    with pytest.raises(BridgeRelayerConfigReplacePlaceholderTypeError):
        config.replace_placeholders(config_content)
    
# ABI
def test_get_abi_file_returns_valid_file_for_dev(config):
    """
        Test get_abi that returns an abi file for dev env
    """
    abi_file = config.get_abi_file()
    assert abi_file == config.FILE_ABI_DEV
    
def test_get_abi_file_raises_exception_file_missing(config):
    """
        Test get_abi that raises BridgeRelayerConfigABIFileMissing 
        when abi.json file is missing
    """
    with patch('src.relayer.config.config.get_abi_file', return_value="missing_abi_file"):
        with pytest.raises(BridgeRelayerConfigABIFileMissing):
            config.get_abi(chain_id=80002)             
    
def test_get_abi_returns_valid_abi(config):
    """
        Test get_abi that returns an abi for a specific chain_id
    """
    abi = config.get_abi(chain_id=80002)
    assert len(abi) > 0

def test_get_abi_file_returns_valid_file_for_prod(config_prod):
    """
        Test get_abi_file that returns an abi file for dev env
    """
    abi_file = config_prod.get_abi_file()
    assert abi_file == config_prod.FILE_ABI_PRD

def test_get_abi_raise_exception_with_invalid_chain_id(config):
    """
        Test get_abi that raises BridgeRelayerConfigABIAttributeMissing with 
        invalid chain_id
    """
    with pytest.raises(BridgeRelayerConfigABIAttributeMissing):
        config.get_abi(chain_id=777)

def test_get_relayer_event_rules_raise_exception_with_invalid_event_name(config):
    """
        Test get_relayer_event_rules that raises 
        BridgeRelayerConfigRelayerEventRulesDataMissing with invalid event_name
    """
    with pytest.raises(BridgeRelayerConfigEventRuleKeyError):
        config.get_relayer_event_rule(event_name="invalid_event_name")
    
def test_get_relayer_event_rules_returns_valid_event_rule(config):
    """
        Test get_relayer_event_rules that returns valid event rule
    """
    event_rule = config.get_relayer_event_rule(event_name="OperationCreated")
    assert isinstance(event_rule, EventRuleConfig)
    assert event_rule.event_name == "OperationCreated"
