"""Entities for Relayer Config."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RelayerBlockchainConfigDTO:
    """Relayer blockchain config DTO."""
    
    chain_id: int
    rpc_url: str
    project_id: str
    pk: str
    wait_block_validation: int
    block_validation_second_per_block: int
    smart_contract_address: str
    genesis_block: int
    abi: Any
    client: str
    
    def __str__(self) -> str:
        return f"ChainId{self.chain_id}"
    
    
@dataclass
class RelayerRegisterConfigDTO:
    """Relayer register config DTO."""
    host: str
    port: int
    user: str
    password: str
    queue_name: str


@dataclass
class EventRuleConfig:
    """Event rule config."""

    event_name: str
    origin: str
    has_block_finality: bool
    chain_func_name: Optional[str] = None
    func_name: Optional[str] = None
    func_condition: Optional[str] = None
    depends_on: Optional[str] = None
