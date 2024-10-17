"""Repository application."""


from src.relayer.domain.event_db import BridgeTaskDTO, EventDTO
from src.relayer.domain.exception import (
    RepositoryErrorOnGet,
    RepositoryErrorOnSave
)
from src.relayer.interface.relayer_repository import IRelayerRepository
from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging


class Repository(RelayerLogging, BaseApp):
    """Repository application."""

    def __init__(
        self,
        repository_provider: IRelayerRepository,
    ):
        """Init the repository application."""
        super().__init__(level="INFO")
        # providers
        self.provider: IRelayerRepository = repository_provider

    async def setup(self, repository_name: str) -> None:
        """Configure the repository.

        Args:
            repository_name (str): The name of the repository to be set up.
        """
        await self.provider.setup(name=str(repository_name))

    async def get_last_scanned_block(self, chain_id: int):
        """Get the last scanned block number.

        Args:
            chain_id (int): The chain id

        Returns:
            _type_: The last scanned block number

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self.provider.get_last_scanned_block(chain_id)
        except RepositoryErrorOnGet:
            return 0

    async def set_last_scanned_block(self, chain_id: int, block_numer: int):
        """Set the last scanned block number.

        Args:
            chain_id (int): The chain id
            block_numer (int): The block number

        Raises:
            RepositoryErrorOnSave
        """
        try:
            await self.provider.set_last_scanned_block(
                chain_id=chain_id,
                block_numer=block_numer
            )
        except RepositoryErrorOnSave:
            raise

    async def set_event_as_registered(self, event: EventDTO):
        """Set the event as registered.

            Once an event has been scanned it has to be registered to be
            handled.

        Args:
            event (EventDTO): The event DTO

        Raises:
            RepositoryErrorOnSave
        """
        try:
            event.handled = "registered"
            await self.provider.save_event(event=event)
        except RepositoryErrorOnSave:
            raise

    async def get_event(self, id: str) -> EventDTO:
        """Get event from the repository.

        Args:
            id (str): The event id

        Returns:
            EventDTO: The event

        Raises:
            RepositoryErrorOnGet:
        """
        try:
            return await self.provider.get_event(id=id)
        except RepositoryErrorOnGet:
            raise

    async def is_event_stored(self, event: EventDTO) -> bool:
        """Check if the event has already been stored.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bool: True if the event has been stored.
        """
        try:
            return await self.provider.get_event(id=event.as_key()) == event
        except RepositoryErrorOnGet:
            return False

    async def is_event_registered(self, event: EventDTO) -> bool:
        """Check if the event has already been registered.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bool: True if the event has been registered.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            event = await self.provider.get_event(id=event.as_key())
            return event.handled == "registered"

        except RepositoryErrorOnGet:
            return False

    async def store_event(self, event: EventDTO) -> bool:
        """Store event in the repository.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bool: True if the event has been stored.
        """
        new_event = False

        if not await self.is_event_stored(event):
            new_event = True

            self.logger.info(
                f"{self.Emoji.info.value}"
                f"chain_id={event.chain_id} "
                f"operationHash={event.data.operation_hash_str} "
                f"New event received {event.as_key()}"
            )

            await self.provider.save_event(event=event)
        return new_event

    async def get_bridge_task(self, id: str) -> BridgeTaskDTO:
        """Get the bridge task.

        Args:
            id (str): The bridge task id

        Returns:
            BridgeTask: The bridge task

        Raises:
            RepositoryErrorOnGet:
        """
        try:
            return await self.provider.get_bridge_task(id=id)
        except RepositoryErrorOnGet:
            raise

    async def get_bridge_tasks(self) -> BridgeTaskDTO:
        """Get all bridges tasks.

        Returns:
            List[BridgeTask]: A list of bridges tasks.

        Raises:
            RepositoryErrorOnGet
        """
        try:
            return await self.provider.get_bridge_tasks()
        except RepositoryErrorOnGet:
            raise

    async def save_event(self, event: EventDTO):
        """Save an event.

        Args:
            event (EventDTO): An event DTO

        Raises:
            RepositoryErrorOnSave:
        """
        try:
            await self.provider.save_event(event=event)
        except RepositoryErrorOnSave:
            raise

    async def save_bridge_task(self, bridge_task: BridgeTaskDTO):
        """Save a bridge task.

        Args:
            bridge_task (BridgeTask): A bridge task

        Raises:
            RepositoryErrorOnSave:
        """
        try:
            await self.provider.save_bridge_task(bridge_task=bridge_task)
        except RepositoryErrorOnSave:
            raise
