"""Bridge relayer configuration."""
import json
import pathlib
import os
from typing import Any, Dict
from dotenv import load_dotenv
import tomli
from jinja2 import Template

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
    BridgeRelayerConfigTOMLFileMissing,
)

FILE_ABI_DEV = "abi_dev.json"
FILE_ABI_PRD = "abi.json"

FILE_TOML_DEV = "bridge_relayer_config_dev.toml"
FILE_TOML_PRD = "bridge_relayer_config.toml"

FILE_ENV_DEV = ".env.config.dev"
FILE_ENV_PRD = ".env.config.prod"

# Load .env
load_dotenv()

def is_dev_env() -> bool:
    """Check if environment is dev or prod.

    Returns:
        bool: Return True if environment is Dev, False for Prod
    """
    if os.environ.get("DEV_ENV") and os.environ["DEV_ENV"] == "False":
        return False
    return True


def load_env_file():
    """Load env file that depends on environment dev or prod."""
    if is_dev_env():
        load_dotenv(FILE_ENV_DEV)
    
    load_dotenv(FILE_ENV_PRD)


def get_toml_file() -> str:
    """Get the toml file name.

    Depends on environment value set in .env 
        DEV_ENV=True

    Returns:
        str: The toml file name
    """
    load_env_file()
    
    if is_dev_env():
        return FILE_TOML_DEV
    return FILE_TOML_PRD

    

def get_abi_file() -> str:
    """Get the abi file name.
    
    Depends on environment value set in .env 
        DEV_ENV=True

    Returns:
        str: The abi file name
    """
    if is_dev_env():
        return FILE_ABI_DEV
    return FILE_ABI_PRD
   

def get_config_content(toml_file: str) -> str:
    """Get the toml content file.

    Args:
        toml_file (str): The toml file name

    Returns:
        str: The toml content file
    """
    path: pathlib.Path = pathlib.Path(__file__).parent / toml_file

    try:
        with path.open(mode="r") as file:
            config_content: str = file.read()
            return config_content
    except FileNotFoundError as e:
        raise BridgeRelayerConfigTOMLFileMissing(e)
    
    
def replace_placeholders(config_content: str) -> str:
    """Substitute double curly braces by values.
    
    Powered by Jinja template engine.

    Args:
        config_content (str): The toml content

    Returns:
        str: The toml content modified
    """
    try:
        template = Template(config_content)
        rendered_content: str = template.render(os.environ)
        return rendered_content
    except TypeError as e:
        raise BridgeRelayerConfigReplacePlaceholderTypeError(e)


def get_abi(chain_id: int) -> Any:
    """Get the ABI content.

    Args:
        chain_id (int): The chain_id

    Returns:
        Any: The abi
    """
    abi_file: str = get_abi_file()
    path: pathlib.Path = pathlib.Path(__file__).parent / abi_file

    try:
        with path.open('r') as f:
            abi: Any = json.loads(f.read())
            return abi[str(chain_id)]
    except FileNotFoundError as e:
        raise BridgeRelayerConfigABIFileMissing(e)
    except KeyError as e:
        raise BridgeRelayerConfigABIAttributeMissing(e)

def _get_bridge_relayer_config()-> Dict[str, Any]:
    """Get the bridge relayer config values.

    Returns:
        Dict[str, Any]: The bridge relayer config
    """
    toml_file: str = get_toml_file()
    config_content: str = get_config_content(toml_file=toml_file)
    rendered_content: str = replace_placeholders(config_content)
    _bridge_relayer_config: Dict[str, Any] = tomli.loads(rendered_content)
    
    return _bridge_relayer_config


def get_blockchain_config(chain_id: int) -> RelayerBlockchainConfigDTO:
    """Get the bridge relayer blockchain config.

    Args:
        chain_id (int): The chain id

    Returns:
        RelayerBlockchainDTO: The bridge relayer blockchain config DTO
    """
    _bridge_relayer_config: Dict[str, Any] = _get_bridge_relayer_config()
    relayer_blockchain: Dict[str, Any] = {}
    
    for k, v in _bridge_relayer_config['relayer_blockchain'].items():
        if k.lower() != f"chainid{chain_id}":
            continue
        
        relayer_blockchain.update(v)
        relayer_blockchain.update({"chain_id": chain_id})
        relayer_blockchain.update({"abi": get_abi(chain_id=chain_id)})
    
    try:
        return RelayerBlockchainConfigDTO(**relayer_blockchain)
    except TypeError as e:
        raise BridgeRelayerConfigBlockchainDataMissing(
            f"chain_id={chain_id} Error={e} _bridge_relayer_config={_bridge_relayer_config}"
        )


def get_register_config() -> RelayerRegisterConfigDTO:
    """Get the bridge relayer event register config.

    Returns:
        RelayerRegisterDTO: The bridge relayer event register config DTO
    """
    _bridge_relayer_config: Dict[str, Any] = _get_bridge_relayer_config()
    try:
        for k, v in _bridge_relayer_config['relayer_register'].items():
            if k == "port":
                _bridge_relayer_config['relayer_register'][k] = int(v)

        return RelayerRegisterConfigDTO(**_bridge_relayer_config['relayer_register'])
    except TypeError as e:
        raise BridgeRelayerConfigRegisterDataMissing(e)


def get_relayer_event_rule(event_name: str) -> EventRuleConfig:
    """Get the bridge relayer event rule config.

    Args:
        event_name (str): The event name

    Returns:
        EventRuleConfig: The bridge relayer event rule config DTO
    """
    _bridge_relayer_config: Dict[str, Any] = _get_bridge_relayer_config()
    data: Dict[str, Any] = {}
    
    for k, v in _bridge_relayer_config['relayer_event_rules'].items():
        if event_name.lower() != k.lower():
            continue
        
        data.update(v)
        data.update({"event_name": event_name})
    
    try:
        return EventRuleConfig(**data)
    except TypeError as e:
        raise BridgeRelayerConfigEventRuleKeyError(e)
