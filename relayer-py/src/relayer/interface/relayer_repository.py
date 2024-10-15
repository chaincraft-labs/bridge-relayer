from abc import ABC, abstractmethod
from typing import List

from src.relayer.domain.event_db import BridgeTaskDTO, EventDTO


class IRelayerRepository(ABC):
    """Interface for saving and retrieving events."""

    @abstractmethod
    async def setup(self, name: str):
        """
        Set up the repository.

        Args:
            name (str): The name of the repository to be set up.
            verbose (bool, optional): Whether to print verbose logs. 
                Defaults to False.
        """

    # -----------------------------------------------------------------
    #  Events
    # -----------------------------------------------------------------
    @abstractmethod
    async def save_event(self, event: EventDTO):
        """Save the event.

        Args:
            event (EventDTO): An event DTO

        Raises:
            RepositoryErrorOnSave
        """

    @abstractmethod
    async def get_events(self) -> List[EventDTO]:
        """Get all events.

        Returns:
            List[EventDTO]: A list of events.

        Raises:
            RepositoryErrorOnGet
        """

    @abstractmethod
    async def get_event(self, id: str) -> EventDTO:
        """Get the event.

        Args:
            id (str): The event id.

        Returns:
            EventDTO: The event DTO.

        Raises:
            RepositoryErrorOnGet
        """

    @abstractmethod
    async def delete_event(self, id: str):
        """Delete the event.

        Args:
            id (str): The event id.

        Raises:
            RepositoryErrorOnDelete
        """

    # -----------------------------------------------------------------
    # bridge task
    # -----------------------------------------------------------------
    @abstractmethod
    async def save_bridge_task(self, bridge_task: BridgeTaskDTO):
        """Save a bridge task.

        Args:
            bridge_task (BridgeTask): An event task.

        Raises:
            RepositoryErrorOnSave
        """

    @abstractmethod
    async def get_bridge_tasks(self) -> List[BridgeTaskDTO]:
        """Get all bridges tasks.

        Returns:
            List[BridgeTask]: A list of bridges tasks.

        Raises:
            RepositoryErrorOnGet
        """

    @abstractmethod
    async def get_bridge_task(self, id: str) -> BridgeTaskDTO:
        """Get a bridge task.

        Args:
            id (str): The bridge task id.
        
        Returns:
            BridgeTask: The bridge task.

        Raises:
            RepositoryErrorOnGet
        """

    # -----------------------------------------------------------------
    #  Last scanned block
    # -----------------------------------------------------------------
    @abstractmethod
    async def set_last_scanned_block(self, chain_id: int, block_numer: int):
        """Set the last scanned block number.

        Args:
            chain_id (int): The chain id.
            block_numer (int): The block number.

        Raises:
            RepositoryErrorOnSave
        """

    @abstractmethod
    async def get_last_scanned_block(self, chain_id: int) -> int:
        """Get the last scanned block stored.

        Args:
            chain_id (int): The chain id.

        Returns:
            int: The last scanned block number.

        Raises:
            RepositoryErrorOnGet
        """
