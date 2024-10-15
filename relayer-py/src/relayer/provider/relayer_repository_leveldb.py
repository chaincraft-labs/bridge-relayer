"""
Bridge relayer repository provider.

This provider uses a local database `sqlite` (asynchronous).
It is used to store bridge tasks and events for any chains.
"""
from typing import Any, List

import plyvel

from src.relayer.domain.event_db import BridgeTaskDTO, EventDTO
from src.relayer.domain.exception import (
    RepositoryDatabaseNotProvided, 
    RepositoryErrorOnDelete, 
    RepositoryErrorOnGet, 
    RepositoryErrorOnSave,
)
from src.relayer.interface.relayer_repository import IRelayerRepository
from src.utils.converter import from_bytes, to_bytes


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
        if name is None or name == "":
            raise RepositoryDatabaseNotProvided("Database name is not set")
        
        if self.db is None:
            self.db = plyvel.DB(str(name), create_if_missing=True)

    # -----------------------------------------------------------------
    #  Implemented functions
    # -----------------------------------------------------------------
    #  Events
    # -----------------------------------------------------------------
    async def save_event(self, event: EventDTO):
        """Save an event.

        Args:
            event (EventDTO): An event DTO

        Raises:
            RepositoryErrorOnSave
        """
        try:
            await self._save_data(
                prefix=self.prefix_event, 
                id=event.as_key(), 
                data=event
            )
        except Exception as e:
            err = f"An unexpected error occurred while saving event: {e}"
            raise RepositoryErrorOnSave(err)

    async def get_events(self) -> List[EventDTO]:
        """Get all events.

        Returns:
            List[EventDTO]: A list of events.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self._get_datas(self.prefix_event)
        except Exception as e:
            err = f"An unexpected error occurred while getting events: {e}"
            raise RepositoryErrorOnGet(err)

    async def get_event(self, id: str) -> EventDTO:
        """Get the event.

        Args:
            id (str): The event id.

        Returns:
            EventDTO: The event DTO.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self._get_data(prefix=self.prefix_event, id=id)
        except Exception as e:
            err = f"An unexpected error occurred while getting event: {e}"
            raise RepositoryErrorOnGet(err)

    async def delete_event(self, id: str):
        """Delete the event.

        Args:
            id (str): The event id.

        Raises:
            RepositoryErrorOnDelete
        """
        try:
            await self._delete_data(prefix=self.prefix_event, id=id)
        except Exception as e:
            err = f"An unexpected error occurred while deleting event: {e}"
            raise RepositoryErrorOnDelete(err)

    # -----------------------------------------------------------------
    # bridge task
    # -----------------------------------------------------------------
    async def save_bridge_task(self, bridge_task: BridgeTaskDTO):
        """Save a bridge task.

        Args:
            bridge_task (BridgeTask): A bridge task.

        Raises:
            RepositoryErrorOnSave
        """
        try:
            await self._save_data(
                prefix=self.prefix_bridge_task, 
                id=bridge_task.as_key(),
                data=bridge_task,
            )
        except Exception as e:
            err = f"An unexpected error occurred while saving bridge task: {e}"
            raise RepositoryErrorOnSave(err)

    async def get_bridge_tasks(self) -> List[BridgeTaskDTO]:
        """Get all bridges tasks.

        Returns:
            List[BridgeTask]: A list of bridges tasks.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self._get_datas(prefix=self.prefix_bridge_task)
        except Exception as e:
            err = f"An unexpected error occurred while getting bridge task: {e}"
            raise RepositoryErrorOnGet(err)
 
    async def get_bridge_task(self, id: str) -> BridgeTaskDTO:
        """Get a bridge task.

        Args:
            id (str): The bridge task id.
        
        Returns:
            BridgeTask: The bridge task.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self._get_data(prefix=self.prefix_bridge_task, id=id)
        except Exception as e:
            err = f"An unexpected error occurred while getting bridge task: {e}"
            raise RepositoryErrorOnGet(err)

    # -----------------------------------------------------------------
    #  Last scanned block
    # -----------------------------------------------------------------
    async def set_last_scanned_block(self, chain_id: int, block_numer: int):
        """Set the last scanned block number.

        Args:
            chain_id (int): The chain id.
            block_numer (int): The block number.

        Raises:
            RepositoryErrorOnSave
        """
        try:
            await self._save_data(
                prefix=self.prefix_last_scanned_block, 
                id=chain_id,
                data=block_numer,
            )
        except Exception as e:
            err = (
                f"An unexpected error occurred while saving last scanned "
                f"block: {e}"
            )
            raise RepositoryErrorOnSave(err)

    async def get_last_scanned_block(self, chain_id: int) -> int:
        """Get the last scanned block stored.

        Args:
            chain_id (int): The chain id.

        Returns:
            int: The last scanned block number.

        Raises:
            RepositoryErrorOnGet
        """
        
        try:
            return await self._get_data(
                prefix=self.prefix_last_scanned_block, 
                id=chain_id
            )
        except Exception as e:
            err = (
                f"An unexpected error occurred while getting last scanned "
                f"block: {e}"
            )
            raise RepositoryErrorOnGet(err)

# -----------------------------------------------------------------
#  Private functions
# -----------------------------------------------------------------
    async def _save_data(self, prefix: str, id: str, data: Any):
        """Save data by prefix and id.

        Args:
            prefix (str): The prefix
            id (str): The id
            data (Any): The data
        """
        key = f"{prefix}{id}".encode('utf-8')
        self.db.put(key, to_bytes(data))

    async def _get_datas(self, prefix: str) -> List[Any]:
        """Get all datas by prefix.

        Args:
            prefix (str): The prefix

        Returns:
            List[Any]: A list of data.
        """
        return [
            from_bytes(value) 
            for key, value in self.db.iterator(prefix=prefix.encode('utf-8'))
        ]

    async def _get_data(self, prefix: str, id: str) -> Any:
        """Get the data by prefix and id.

        Args:
            prefix (str): The prefix
            id (str): The id

        Returns:
            EventDTO: The event
        """
        key = f"{prefix}{id}".encode('utf-8')
        return from_bytes(self.db.get(key))

    async def _delete_data(self, prefix: str, id: str):
        """Delete data by prefix and id.

        Args:
            prefix (str): The prefix
            id (str): The id
        """
        key = f"{prefix}{id}".encode('utf-8')
        self.db.delete(key)
