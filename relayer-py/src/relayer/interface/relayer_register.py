"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from typing import Callable


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
