"""Relayer blockchain provider mocked."""
from typing import Any, Callable

from src.relayer.domain.relayer import (
    BridgeTaskDTO, 
    BridgeTaskResult
)
from src.relayer.interface.relayer import IRelayerBlockchain

    
class MockRelayerBlockchainProvider(IRelayerBlockchain):
    """Mock RelayerBlockchainProvider provider"""

    async def get_block_number(self) -> int:
        raise NotImplementedError

    def set_chain_id(self, chain_id: int):
        raise NotImplementedError

    def listen_events(
        self, 
        callback: Callable[..., Any], 
        poll_interval: int
    ) -> Any:
        raise NotImplementedError

    async def call_contract_func(
        self, 
        bridge_task_dto: BridgeTaskDTO
    ) -> BridgeTaskResult:
        raise NotImplementedError
