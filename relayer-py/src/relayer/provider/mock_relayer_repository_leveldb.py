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
        raise NotImplementedError

    async def save_event(self, event: EventDTO):
        raise NotImplementedError

    async def get_events(self) -> List[EventDTO]:
        raise NotImplementedError

    async def get_event(self, id: str) -> EventDTO:
        raise NotImplementedError

    async def delete_event(self, id: str):
        raise NotImplementedError

    async def save_bridge_task(self, bridge_task: BridgeTaskDTO):
        raise NotImplementedError

    async def get_bridge_tasks(self) -> List[BridgeTaskDTO]:
        raise NotImplementedError

    async def get_bridge_task(self, id: str) -> BridgeTaskDTO:
        raise NotImplementedError

    async def set_last_scanned_block(self, chain_id: int, block_numer: int):
        raise NotImplementedError

    async def get_last_scanned_block(self, chain_id: int) -> int:
        raise NotImplementedError

