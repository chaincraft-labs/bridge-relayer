import importlib
import os
import sys
from unittest.mock import patch
import pytest

from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO, 
    RelayerRegisterConfigDTO,
)
from src.relayer.domain.exception import (
    BridgeRelayerConfigABIAttributeMissing, 
    BridgeRelayerConfigABIFileMissing, 
    BridgeRelayerConfigBlockchainDataMissing,
    BridgeRelayerConfigRegisterDataMissing, 
    BridgeRelayerConfigReplacePlaceholderTypeError, 
    BridgeRelayerConfigTOMLFileMissing
)

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
def config_prod():
    os.environ['DEV_ENV'] = "False"
    if 'src.relayer.config.config' in sys.modules:
        importlib.reload(sys.modules['src.relayer.config.config'])
    import src.relayer.config.config as config
    return config

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_get_blockchain_config_returns_dto_with_chain_id(config):
    """
        Test get_blockchain_config returns a RelayerBlockchainConfigDTO DTO.
    """
    chain_id = 123
    blockchain_config_dto = config.get_blockchain_config(chain_id=chain_id)
    assert str(blockchain_config_dto) == f"ChainId{chain_id}"
    assert isinstance(blockchain_config_dto, RelayerBlockchainConfigDTO)
    assert blockchain_config_dto.chain_id == chain_id
    assert blockchain_config_dto.rpc_url ==  "https://fake.rpc_url.org"
    assert blockchain_config_dto.project_id == os.environ[f"PROJECT_ID_{chain_id}"]
    assert blockchain_config_dto.smart_contract_address == "0x1234567890abcdef1234567890abcdef12345678"
    assert blockchain_config_dto.genesis_block == 123456789
    assert blockchain_config_dto.pk == os.environ[f"PK_{chain_id}"]
    
def test_get_blockchain_config_raise_exception_with_bad_chain_id(config):
    """
        Test get_blockchain_config raises 
        BridgeRelayerConfigBlockchainDataMissing with missing positional 
        arguments.
    """
    with pytest.raises(BridgeRelayerConfigBlockchainDataMissing):
        config.get_blockchain_config(chain_id=0)        
    
def test_get_register_config_returns_dto_with(config):
    """
        Test get_register_config returns a RelayerRegisterConfigDTO DTO.
    """
    register_config_dto = config.get_register_config()
    assert isinstance(register_config_dto, RelayerRegisterConfigDTO)
    assert register_config_dto.host == "localhost"
    assert register_config_dto.port == 5672
    assert register_config_dto.user == "guest"
    assert register_config_dto.password == os.environ["RELAYER_REGISTER_PASSWORD"]
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
def test_load_env_file_with_valid_file(config):
    """
        Test load_env_file that exports all values from the env.config.dev 
        file.
    """
    config.load_env_file()
    assert os.environ["PROJECT_ID_411"] == "YZDVs36JnDusFSQZZ42ly3ihIgHQ24eC"
    assert os.environ["PROJECT_ID_80002"] == "YZDVs36JnDusFSQZZ42ly3ihIgHQ24eC"
    assert os.environ["PK_411"] == "673e1858045114d92030ad9d6395d462281e63bcd2b96258a04f7ef8dcd4edad"
    assert os.environ["PK_80002"] == "673e1858045114d92030ad9d6395d462281e63bcd2b96258a04f7ef8dcd4edad"
    assert os.environ["RELAYER_REGISTER_PASSWORD"] == "guest"

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
