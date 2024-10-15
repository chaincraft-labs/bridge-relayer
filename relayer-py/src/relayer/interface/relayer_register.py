"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from typing import Callable


class IRelayerRegister(ABC):
    """Relayer Interface for saving events as messages."""
    
    @abstractmethod
    async def register_event(self, event: bytes) -> None:
        """Register the event.

        Args:
            event (bytes): An event.

        Raises:
            RelayerRegisterEventFailed
        """
        
    @abstractmethod
    async def read_events(self, callback: Callable) -> None:
        """Read all event tasks.

        Args:
            callback (Callable): A callback function.

        Raises:
            BridgeRelayerReadEventFailed
        """
