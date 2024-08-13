from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.relayer.domain.event import EventDataDTO


class IEventDataStore(ABC):
    """Application state that remembers what blocks we have scanned in 
    the case of crash.
    """

    @abstractmethod
    def read_events(self) -> Dict[str, Any]:
        """Read events from data storage.

        Returns:
            Dict[str, Any]: The event state
        """

    def commit(self):
        """Commit events (state) to a data storage (file).
        
            Create file name and directory if not exist
        """

    @abstractmethod
    def save_events(self, events: List[EventDataDTO], auto_commit: bool):
        """Save incoming events.

        Args:
            event (List[EventDataDTO]): A collection of event datas
            auto_commit (bool): Commit state to data store. Default is True
        """

    @abstractmethod
    def save_event(self, event: EventDataDTO, auto_commit: bool):
        """Save incoming event.

        Args:
            event (EventDataDTO): An event data
            auto_commit (bool): Commit state to data store. Default is True
        """

    @abstractmethod
    def delete_event(self, since_block: int, auto_commit: bool):
        """Delete any data since this block was scanned.

        Purges any potential minor reorg data.

        Args:
            since_block (int): BLock limit to delete data
            auto_commit (bool): Commit state to data store. Default is True
        """

    @abstractmethod
    def get_last_scanned_block(self) -> int:
        """Get the last block stored

        Returns:
            int: The block number
        """

    @abstractmethod
    def set_last_scanned_block(self, block_numer: int):
        """Set the last scanned block

        Args:
            block_numer (int): The block number
        """

    @abstractmethod
    def is_event_stored(self, event_key: str) -> bool:
        """Check if the event has already been stored.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"

        Returns:
            bool: True if the event has been stored.
        """

    @abstractmethod
    def is_event_registered(self, event_key: str) -> bool:
        """Check if the event has already been registered.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"

        Returns:
            bool: True if the event has been registered.
        """

    @abstractmethod
    def set_event_as_registered(self, event_key: str):
        """Set the event as registered.

            Once an event has been scanned it has to be registered to be 
            handled.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"
        """