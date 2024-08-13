"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from typing import Any, Callable, List

from src.relayer.domain.relayer import (
    BridgeTaskResult,
)
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
)


class IRelayerBlockchain(ABC):
    """Relayer Interface for blockchain events."""
    
    @abstractmethod
    async def get_block_number(self) -> int:
        """Get the block number.

        Returns:
            (int): The block number
        """
    
    @abstractmethod
    def set_chain_id(self, chain_id: int):
        """Set the blockchain id.

        Args:
            chain_id (int): The chain id
        """
        
    @abstractmethod
    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.
        """
   
    @abstractmethod
    def listen_events(self, callback: Callable, poll_interval: int) -> Any:
        """The blockchain event listener.

        Args:
            poll_interval int: The loop poll interval in second 
        """

    @abstractmethod
    async def call_contract_func(
        self, 
        bridge_task_dto: BridgeTaskDTO
    ) -> BridgeTaskResult:
        """Call a contract's function.
        
        Args:
            bridge_task_dto (BridgeTaskDTO): The bridge task DTO

        Returns:
            BridgeTaskResult: The bridge task execution result
        """
