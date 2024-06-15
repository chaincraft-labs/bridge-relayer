from dataclasses import dataclass
from typing import Any, Dict

from src.relayer.domain.base import BaseResult

# Result DTO

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

# Relayer register Event

@dataclass
class EventMessageDTO:
    """Event message to register."""
    
    name: str
    chain_id_source: int
    chain_id_target: int
    data: Any
