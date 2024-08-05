"""Entities for Relayer Config."""
from dataclasses import dataclass
from typing import Any


@dataclass
class RelayerBlockchainConfigDTO:
    """Relayer blockchain config DTO."""
    
    chain_id: int
    rpc_url: str
    project_id: str
    pk: str
    wait_block_validation: int
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