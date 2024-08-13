from dataclasses import dataclass, asdict
from typing import Any, Dict

from attributedict.collections import AttributeDict
from hexbytes import HexBytes

from src.relayer.domain.base import BaseResult


# Consume event from MQ
@dataclass
class BlockFinalityResult(BaseResult):
    """Result DTO for block finality."""


@dataclass
class DefineChainBlockFinalityResult(BaseResult):
    """Result DTO for define chain id for block finality."""


@dataclass
class CalculateBlockFinalityResult(BaseResult):
    """Result DTO for calculate block finality."""




@dataclass
class RegisterEventResult(BaseResult):
    """Result DTO for Register Event."""


@dataclass
class BridgeTaskResult(BaseResult):
    """Result DTO for bridge task."""


@dataclass
class BridgeTaskTxResult:
    """Result DTO for bridge task Transaction."""

    tx_hash: str
    block_hash: str
    block_number: int
    gas_used: int


#  Relayer blockchain Task

@dataclass
class BridgeTaskDTO:
    """DTO for blockchain bridge relayer contract's function."""

    func_name: str
    params: Dict[str, Any]


# Relayer blockchain Event

@dataclass
class EventDTO:
    """Event DTO from blockchain."""

    name: str
    data: Any
    block_key: str

    @staticmethod
    def data_as_dict(attr_dict: Any) -> Dict[str, Any]:
        """Convert AttributeDict to a standard dictionary.

        Args:
            attr_dict (_type_): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        if isinstance(attr_dict, AttributeDict):
            return {k: EventDTO.data_as_dict(v) for k, v in attr_dict.items()}
        elif isinstance(attr_dict, HexBytes):
            return attr_dict.hex()
        elif isinstance(attr_dict, list):
            return [EventDTO.data_as_dict(item) for item in attr_dict]
        else:
            return attr_dict

    def as_dict(self) -> Dict[str, Any]:
        """Convert AttributeDict to a standard dictionary.

        Args:
            attr_dict (_type_): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        self.data = EventDTO.data_as_dict(self.data)
        return asdict(self)


# Relayer register Event

@dataclass
class EventMessageDTO:
    """Event message to register."""

    name: str
    chain_id_source: int
    chain_id_target: int
    data: Any
