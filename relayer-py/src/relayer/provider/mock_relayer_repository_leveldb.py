"""
Bridge relayer repository provider.

This provider uses a local database `sqlite` (asynchronous).
It is used to store bridge tasks and events for any chains.
"""
from typing import List

import plyvel

from src.relayer.domain.event_db import BridgeTaskDTO, EventDTO
from src.relayer.interface.relayer_repository import IRelayerRepository


class RelayerRepositoryProvider(IRelayerRepository):
    """Bridge relayer repository provider for event and bridge task state."""

    def __init__(self):
        """Init the bridge data provider.

        Args:
            log_level (str): The log level. Defaults to 'info'.
        """
        self.db: plyvel.DB = None
        self.prefix_event = "event-"
        self.prefix_bridge_task = "bridge-task-"
        self.prefix_last_scanned_block = "last-scanned-block-"

    async def setup(self, name: str):
        """
        Set up the repository.

        Args:
            name (str): The name of the repository to be set up.
            verbose (bool, optional): Whether to print verbose logs.
                Defaults to False.
        """
        raise NotImplementedError

    async def save_event(self, event: EventDTO):
        """Save an event.

        Args:
            event (EventDTO): An event DTO

        Raises:
            RepositoryErrorOnSave
        """
        raise NotImplementedError

    async def get_events(self) -> List[EventDTO]:
        """Get all events.

        Returns:
            List[EventDTO]: A list of events.

        Raises:
            RepositoryErrorOnGet
        """
        raise NotImplementedError

    async def get_event(self, id: str) -> EventDTO:
        """Get the event.

        Args:
            id (str): The event id.

        Returns:
            EventDTO: The event DTO.

        Raises:
            RepositoryErrorOnGet
        """
        raise NotImplementedError

    async def delete_event(self, id: str):
        """Delete the event.

        Args:
            id (str): The event id.

        Raises:
            RepositoryErrorOnDelete
        """
        raise NotImplementedError

    async def save_bridge_task(self, bridge_task: BridgeTaskDTO):
        """Save a bridge task.

        Args:
            bridge_task (BridgeTask): A bridge task.

        Raises:
            RepositoryErrorOnSave
        """
        raise NotImplementedError

    async def get_bridge_tasks(self) -> List[BridgeTaskDTO]:
        """Get all bridges tasks.

        Returns:
            List[BridgeTask]: A list of bridges tasks.

        Raises:
            RepositoryErrorOnGet
        """
        raise NotImplementedError

    async def get_bridge_task(self, id: str) -> BridgeTaskDTO:
        """Get a bridge task.

        Args:
            id (str): The bridge task id.

        Returns:
            BridgeTask: The bridge task.

        Raises:
            RepositoryErrorOnGet
        """
        raise NotImplementedError

    async def set_last_scanned_block(self, chain_id: int, block_numer: int):
        """Set the last scanned block number.

        Args:
            chain_id (int): The chain id.
            block_numer (int): The block number.

        Raises:
            RepositoryErrorOnSave
        """
        raise NotImplementedError

    async def get_last_scanned_block(self, chain_id: int) -> int:
        """Get the last scanned block stored.

        Args:
            chain_id (int): The chain id.

        Returns:
            int: The last scanned block number.

        Raises:
            RepositoryErrorOnGet
        """
        raise NotImplementedError
