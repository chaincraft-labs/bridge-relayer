"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from typing import Any, Callable

from src.relayer.domain.relayer import (
    BridgeTaskResult,
)
from src.relayer.domain.relayer import (
    EventDTO,
    BridgeTaskDTO,
    RegisterEventResult,
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


class IRelayerRegister(ABC):
    """Relayer Interface for saving events as messages."""
    
    @abstractmethod
    def register_event(self, event: bytes):
        """Register the event.
            
        Args:
            event (bytes): An event
        """
        
    @abstractmethod
    def read_events(self, callback: Callable):
        """Consume event tasks.

        Args:
            callback (Callable): A callback function
        """



# class IRelayerTask(ABC):
#     """Interface for Relay task application."""
        
#     @abstractmethod
#     def read_bridge_task(self) -> BridgeTaskDTO:
#         """Read bridge task.

#         Returns:
#             BridgeTaskDTO: A BridgeTaskDTO
#         """
