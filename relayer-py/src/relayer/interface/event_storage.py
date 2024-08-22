from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.relayer.domain.event import EventDataDTO


class IEventDataStore(ABC):
    """Application state that remembers what blocks we have scanned in 
    the case of crash.
    """

    @abstractmethod
    def set_chain_id(self, chain_id: int):
        """Set the chain id.

        Args:
            chain_id (int): The chain id
        """

    @abstractmethod
    def save_event(self, event: EventDataDTO, auto_commit: bool):
        """Save incoming event.

        Args:
            event (EventDataDTO): An event data
            auto_commit (bool): Commit state to data store. Default is True
        """

    @abstractmethod
    def save_event_task(
        self,
        chain_id: int,
        block_key: str,
        operation_hash: str,
        event_name: str,
        auto_commit: bool,
        status: str,
    ):
        """Save event task.

        Args:
            chain_id (int): The chain id
            block_key (str): the block key e.g: "block_number-tx_hash-log_index"
            operation_hash (str): The operation hash
            event_name (str): The event name
            auto_commit (bool): Commit state to data store.
            status (str): The status of the event.
        """

    @abstractmethod
    def delete_event(
        self,
        current_block: int,
        block_to_delete: int,
        auto_commit: bool
    ):
        """Delete any data since this block was scanned.

        Purges any potential minor reorg data.

        Args:
            current_block: (int): The current block on chain
            block_to_delete (int): Number of blocks to delete
            auto_commit (bool): Commit state to data store. Default is True
        """

    @abstractmethod
    def set_last_scanned_block(self, block_numer: int, auto_commit: bool):
        """Set the last scanned block

        Args:
            block_numer (int): The block number
            auto_commit (bool): Commit state to data store.
        """

    @abstractmethod
    def set_event_as_registered(self, event_key: str, auto_commit: bool):
        """Set the event as registered.

            Once an event has been scanned it has to be registered to be 
            handled.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"
            auto_commit (bool): Commit state to data store.
        """

    @abstractmethod
    def read_event_tasks(self) -> Dict[str, Any]:
        """Read event tasks from data storage.

        Returns:
            Dict[str, Any]: The event state
        """

    @abstractmethod
    def get_event_task_status(
        self, 
        operation_hash: str, 
        event_name: str
    ) -> Optional[str]:
        """Get event task status.

        Args:
            operation_hash (str): The operation hash
            event_name (str): The event name

        Returns:
            Optional[str]: The event task status.
        """

    @abstractmethod
    def get_last_scanned_block(self) -> int:
        """Get the last block stored

        Returns:
            int: The block number
        """

    @abstractmethod
    def get_event(
        self, 
        chain_id: int, 
        event_key: str
    ) -> Optional[EventDataDTO]:
        """Get the event

        Args:
            chain_id (int): The chain id
            event_key (str): The event key

        Returns:
            Optional[EventDataDTO]: The event data DTO. None if not found
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
