"""Bridge relayer configuration."""
import json
import os
import pathlib
from typing import Any, Dict, List
from dotenv import load_dotenv

import tomli
from jinja2 import Template

from src.relayer.domain.config import (
    EventRuleConfig,
    RelayerBlockchainConfigDTO,
    RelayerRegisterConfigDTO,
)
from src.relayer.domain.exception import (
    RelayerConfigABIAttributeMissing,
    RelayerConfigABIFileMissing,
    RelayerConfigBlockchainDataMissing,
    RelayerConfigError,
    RelayerConfigEventRuleKeyError,
    RelayerConfigRegisterDataMissing,
    RelayerConfigReplacePlaceholderTypeError,
    RelayerConfigTOMLFileMissing,
)

FILE_ABI_DEV = "abi_dev.json"
FILE_ABI_PRD = "abi.json"

FILE_TOML_DEV = "bridge_relayer_config_dev.toml"
FILE_TOML_PRD = "bridge_relayer_config.toml"

FILE_ENV_DEV = ".env.config.dev"
FILE_ENV_PRD = ".env.config.prod"


# Load .env
load_dotenv()


def get_root_path() -> pathlib.Path:
    """Get the root path.

    Returns:
        pathlib.Path: The root path
    """
    return pathlib.Path(__file__).parent.parent.parent.parent


def is_dev_env() -> bool:
    """Check if environment is dev or prod.

    Returns:
        bool: Return True if environment is Dev, False for Prod
    """
    if os.environ.get("DEV_ENV") == "False":
        return False
    return True


def load_env_file():
    """Load env file that depends on environment dev or prod."""
    if os.environ.get("DEV_ENV") == "True":
        load_dotenv(FILE_ENV_DEV)
    else:
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

    Raises:
        RelayerConfigTOMLFileMissing
    """
    path: pathlib.Path = pathlib.Path(__file__).parent / toml_file

    try:
        with path.open(mode="r") as file:
            config_content: str = file.read()
        return config_content
    except FileNotFoundError as e:
        raise RelayerConfigTOMLFileMissing(e)


def replace_placeholders(config_content: str) -> str:
    """Substitute double curly braces by values.

    Powered by Jinja template engine.

    Args:
        config_content (str): The toml content

    Returns:
        str: The toml content modified

    Raises:
        RelayerConfigReplacePlaceholderTypeError
    """
    try:
        template = Template(config_content)
        rendered_content: str = template.render(os.environ)
        return rendered_content
    except TypeError as e:
        raise RelayerConfigReplacePlaceholderTypeError(e)


def get_bridge_relayer_config() -> Dict[str, Any]:
    """Get the bridge relayer config values.

    Returns:
        Dict[str, Any]: The bridge relayer config

    Raises:
        RelayerConfigError
    """
    try:
        toml_file: str = get_toml_file()
        config_content: str = get_config_content(toml_file=toml_file)
        rendered_content: str = replace_placeholders(config_content)
        return tomli.loads(rendered_content)
    except (
        RelayerConfigTOMLFileMissing,
        RelayerConfigReplacePlaceholderTypeError
    ) as e:
        raise RelayerConfigError(e)


def read_abis() -> Any:
    """Read all ABIs content.

    Returns:
        Dict: The abis

    Raises:
        RelayerConfigABIFileMissing
        RelayerConfigABIAttributeMissing
    """
    abi_file: str = get_abi_file()
    path: pathlib.Path = pathlib.Path(__file__).parent / abi_file

    try:
        with path.open('r') as f:
            abi: Any = json.loads(f.read())
        return abi
    except FileNotFoundError as e:
        raise RelayerConfigABIFileMissing(e)
    except KeyError as e:
        raise RelayerConfigABIAttributeMissing(e)


# ---------------------------------------------------------------------------
# Exported functions
# ---------------------------------------------------------------------------


class Singleton(type):
    """Singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs) -> Any:
        """Override the default `__call__` to avoid creating multiple.

        Returns:
            Any: The instance
        """
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton,
                cls
            ).__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=Singleton):
    """Bridge relayer config."""

    def __init__(self) -> None:
        """Init the bridge relayer config."""
        self.bridge_relayer_config: Dict[str, Any] = \
            get_bridge_relayer_config()
        self.abi: Dict[str, Any] = read_abis()

    def get_abi(self, chain_id: int) -> Any:
        """Get the ABI content.

        Args:
            chain_id (int): The chain_id

        Returns:
            Any: The abi

        Raises:
            RelayerConfigABIAttributeMissing
        """
        try:
            return self.abi[str(chain_id)]
        except KeyError as e:
            raise RelayerConfigABIAttributeMissing(e)

    def get_blockchain_config(
        self,
        chain_id: int,
    ) -> RelayerBlockchainConfigDTO:
        """Get the bridge relayer blockchain config.

        Args:
            chain_id (int): The chain id

        Returns:
            RelayerBlockchainDTO: The bridge relayer blockchain config DTO

        Raises:
            RelayerConfigBlockchainDataMissing
        """
        relayer_blockchain: Dict[str, Any] = {}

        try:
            for k, v in self.bridge_relayer_config['relayer_blockchain'].items():  # noqa
                if k.lower() != f"chainid{chain_id}":
                    continue

                relayer_blockchain.update(v)
                relayer_blockchain.update({"chain_id": chain_id})
                relayer_blockchain.update(
                    {"abi": self.get_abi(chain_id=chain_id)}
                )

            return RelayerBlockchainConfigDTO(**relayer_blockchain)
        except (TypeError, KeyError) as e:
            raise RelayerConfigBlockchainDataMissing(
                f"chain_id={chain_id} "
                f"_bridge_relayer_config={self.bridge_relayer_config} "
                f"Error={e}"
            )

    def get_register_config(self) -> RelayerRegisterConfigDTO:
        """Get the bridge relayer event register config.

        Returns:
            RelayerRegisterDTO
        """
        try:
            for k, v in self.bridge_relayer_config['relayer_register'].items():
                if k == "port":
                    self.bridge_relayer_config['relayer_register'][k] = int(v)

            return RelayerRegisterConfigDTO(
                **self.bridge_relayer_config['relayer_register']
            )
        except (TypeError, KeyError) as e:
            raise RelayerConfigRegisterDataMissing(e)

    def get_relayer_event_rule(self, event_name: str) -> EventRuleConfig:
        """Get the bridge relayer event rule config.

        Args:
            event_name (str): The event name

        Returns:
            EventRuleConfig: The bridge relayer event rule config DTO

        Raises:
            BridgeRelayerConfigEventRuleKeyError
        """
        try:
            data: Dict[str, Any] = {}

            for k, v in self.bridge_relayer_config['relayer_event_rules'].items():  # noqa
                if event_name.lower() != k.lower():
                    continue

                data.update(v)
                data.update({"event_name": event_name})

            return EventRuleConfig(**data)
        except (KeyError, TypeError) as e:
            raise RelayerConfigEventRuleKeyError(e)

    def get_relayer_events(self) -> List[str]:
        """Get the bridge relayer events.

        Returns:
            EventRuleConfig: The bridge relayer event rule config DTO

        Raises:
            List[str]: A list of event names
        """
        try:
            events: List[str] = []

            for k in self.bridge_relayer_config['relayer_event_rules'].keys():
                events.append(k)

            return events
        except (KeyError, TypeError) as e:
            raise RelayerConfigEventRuleKeyError(e)

    def get_data_path(self) -> pathlib.Path:
        """Get the repository name."""
        data_path = self.bridge_relayer_config['environment']['data_path']
        return get_root_path() / data_path

    def get_repository_name(self) -> str:
        """Get the repository name."""
        return self.bridge_relayer_config['environment']['repository']
