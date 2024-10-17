"""Bridge Relayer event listener from RPC node."""
from typing import Callable, List, Optional
from time import sleep, time
from datetime import datetime
from tqdm import tqdm

from src.relayer.application.repository import Repository
from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.config.config import Config
from src.relayer.domain.config import (
    RelayerRegisterConfigDTO,
    RelayerBlockchainConfigDTO,
)
from src.relayer.domain.event_db import (
    EventDTO,
    EventScanDTO,
)
from src.relayer.domain.exception import (
    RelayerEventScanFailed,
    RelayerRegisterEventFailed,
    RepositoryErrorOnGet,
    RepositoryErrorOnSave,
)
from src.relayer.interface.relayer_register import IRelayerRegister
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain
from src.relayer.interface.relayer_repository import IRelayerRepository
from src.utils.converter import to_bytes


class ListeEvents(RelayerLogging, BaseApp):
    """Listen blockchain events."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        relayer_repository_provider: IRelayerRepository,
        chain_id: int,
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000,
        chunk_size_increase: float = 2.0,
        log_level: str = 'info',
    ) -> None:
        """Init blockchain event listener instance.

        Args:
            relayer_blockchain_event (IRelayerBlockchain):
                The relayer blockchain provider
            relayer_register_provider (IRelayerRegister):
                The relayer blockchain configuration
            relayer_repository_provider (IRelayerRepository):
                The relayer repository
            chain_id (int): The chain id
            min_scan_chunk_size (int, optional): Minimum chunk size. \
                Defaults to 10.
            max_scan_chunk_size (int, optional): Maximum chunk size. \
                Defaults to 10000.
            chunk_size_increase (float, optional): Chunk size increase. \
                Defaults to 2.0.
            log_level (str): The log level. Defaults to 'info'.
        """
        super().__init__(level=log_level)
        self.log_level = log_level
        self.chain_id: int = chain_id

        # configurations (singleton)
        self.config = Config()
        self.register_config: RelayerRegisterConfigDTO = \
            self.config.get_register_config()
        self.blockchain_config: RelayerBlockchainConfigDTO = \
            self.config.get_blockchain_config(chain_id)
        self.event_filters: List[str] = self.config.get_relayer_events()
        data_path = self.config.get_data_path()
        repo_name = self.config.get_repository_name()
        self.repository_name = str(
            data_path / f"{self.chain_id}.events.{repo_name}"
        )

        # providers
        self.blockchain_provider: IRelayerBlockchain = \
            relayer_blockchain_provider
        self.register_provider: IRelayerRegister = relayer_register_provider

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = min_scan_chunk_size
        self.max_scan_chunk_size = max_scan_chunk_size
        self.chunk_size_increase = chunk_size_increase

        # Repository Application
        self.repository = Repository(relayer_repository_provider)

    async def __call__(
        self,
        resume_events: bool = False,
        start_chunk_size: int = 20,
        block_to_delete: int = 10,
        progress_bar: bool = True,
        as_service: bool = False,
        log_level: str = 'info',
    ) -> None:
        """Event scanner from RPC node.

        Assume we might have scanned the blocks all the way to the last
        Ethereum block that mined a few seconds before the previous scan
        run ended.
        Because there might have been a minor Ethereum chain reorganisations
        since the last scan ended, we need to discard the last few blocks
        from the previous scan results.

        Args:
            resume_events (bool, optional): Scan all events from the last \
                scan. Defaults to False.
            start_chunk_size (int, optional): Chunk size. Defaults to 20.
            block_to_delete (int, optional): How many blocks to delete. \
                Defaults to 10.
            progress_bar (bool, optional): Show progress bar. Defaults to True.
            as_service (bool, optional): Run as service. Defaults to False.
            log_level (str, optional): The log level. Defaults to 'info'.

        """
        self.log_level = log_level
        # setup the repository
        await self.repository.setup(repository_name=self.repository_name)

        # setup and connect to the blockchain
        self.blockchain_provider.connect_client(chain_id=self.chain_id)
        self.blockchain_provider.set_event_filter(events=self.event_filters)
        start_block = self.get_suggested_scan_end_block()
        end_block: int = self.get_suggested_scan_end_block()

        if resume_events:
            try:
                last_scanned_block: int = \
                    await self.repository.get_last_scanned_block(self.chain_id)
            except RepositoryErrorOnGet:
                last_scanned_block = 0

            start_block: int = max(
                last_scanned_block - block_to_delete,
                self.blockchain_config.genesis_block,
            )

        start = time()
        scan = self.scan

        if progress_bar:
            scan = self.run_scan_with_progress_bar_render

        self.show_cli_title(start_block, end_block)
        scan_as_service = True

        while scan_as_service:
            try:
                event_scan_dto: EventScanDTO = scan(
                    start_block=start_block,
                    end_block=end_block,
                    start_chunk_size=start_chunk_size
                )
            except RelayerEventScanFailed as e:
                msg = (f"chain_id={self.chain_id} {e}")
                self.logger.error(f"{self.Emoji.fail.value}{msg}")
                self.print_log("alert", msg)
                return

            scanned_events: List[EventDTO] = event_scan_dto.events
            total_chunks_scanned: int = event_scan_dto.chunks_scanned
            events_registered = False

            for scanned_event in scanned_events:
                if scanned_event is None:
                    continue

                if await self.repository.is_event_registered(scanned_event):
                    continue

                events_registered = True
                await self.repository.store_event(event=scanned_event)
                await self.register_event(event=scanned_event)

            if events_registered:
                duration = time() - start
                self.print_log(
                    "success",
                    f"chain_id={self.chain_id} Scanned total "
                    f"{len(scanned_events)} events, "
                    f"in {duration} seconds, total {total_chunks_scanned} "
                    f"chunk scans performed"
                )
            events_registered = False

            try:
                await self.repository.set_last_scanned_block(
                    chain_id=self.chain_id,
                    block_numer=end_block
                )
            except RepositoryErrorOnSave:
                msg = (
                    f"chain_id={self.chain_id} "
                    "Unable to save last scanned block with bloc number="
                    f"{end_block}"
                )
                self.logger.error(f"{self.Emoji.fail.value}{msg}")

            if as_service is False:
                scan_as_service = False
            else:
                sleep(1)
                end_block: int = self.get_suggested_scan_end_block()
                start_block = end_block - block_to_delete

    async def register_event(self, event: EventDTO) -> None:
        """Register event in message queuing.

        Args:
            event (EventDTO): The event DTO
        """
        if not await self.repository.is_event_registered(event):
            try:
                await self.register_provider.register_event(to_bytes(event))
                await self.repository.set_event_as_registered(event)

            except (
                RelayerRegisterEventFailed,
                RepositoryErrorOnSave,
            ) as e:
                self.logger.info(
                    f"{self.Emoji.warn.value}chain_id={self.chain_id} {e}"
                )

    def show_cli_title(
        self,
        start_block: int,
        end_block: int
    ) -> None:
        """Print CLI title.

        Args:
            start_block (int): The first block included in the scan
            end_block (int): The last block included in the scan
        """
        title_length = 20
        blocks_to_scan = end_block - start_block

        self.print_log(
            "none",
            f"{"rpc_url":<{title_length}} : {self.blockchain_config.rpc_url}\n"
            f"{"client version":<{title_length}} : "
            f"{self.blockchain_provider.client_version()}\n"
            f"{"chain_id":<{title_length}} : {self.chain_id}\n"
            f"{"Account address":<{title_length}} : "
            f"{self.blockchain_provider.get_account_address()}\n"
            f"{"Contract address":<{title_length}} : "
            f"{self.blockchain_config.smart_contract_address}\n"
            f"{"genesis block":<{title_length}} : "
            f"{self.blockchain_config.genesis_block}\n"
            f"{"start_block":<{title_length}} : {start_block}\n"
            f"{"end_block":<{title_length}} : {end_block}\n"
            f"{"blocks_to_scan":<{title_length}} : {blocks_to_scan}\n"
        )

        self.print_log('main', "Waiting for events. To exit press CTRL+C")

    def get_suggested_scan_end_block(self) -> int:
        """Get the last mined block on Ethereum chain we are following.

            Do not scan all the way to the final block, as this
            block might not be mined yet before last block number

        Returns:
            int: The suggested block number
        """
        current_block = self.blockchain_provider.get_current_block_number()
        if current_block <= 0:
            return 0
        return current_block - 1

    def estimate_next_chunk_size(
        self,
        current_chuck_size: float,
        event_found_count: int
    ) -> int:
        """Estimate the optimal chunk size.

        Scanner might need to scan the whole blockchain for all events

        * Minimize API calls over empty blocks
        * Make sure that one scan chunk does not try to process too \
            many entries once, as we try to control commit buffer size and \
            potentially asynchronous busy loop
        * Do not overload node serving JSON-RPC API by asking data for too \
            many events at a time

        Args:
            current_chuck_size (float): The current chunk size
            event_found_count (int): The number of events found

        Returns:
            int: The next chunk size
        """
        if event_found_count > 0:
            # When we encounter first events, reset the chunk size window
            current_chuck_size = self.min_scan_chunk_size
        else:
            current_chuck_size *= self.chunk_size_increase

        current_chuck_size = max(self.min_scan_chunk_size, current_chuck_size)
        current_chuck_size = min(self.max_scan_chunk_size, current_chuck_size)
        return int(current_chuck_size)

    def scan(
        self,
        start_block: int,
        end_block: int,
        start_chunk_size: int = 20,
        progress_callback: Optional[Callable] = None,
    ) -> EventScanDTO:
        """Scan events from blockchain (rpc node).

        Args:
            start_block (int): start_block: The first block included
                in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch \
                over JSON-RPC on the first attempt. Defaults to 20.
            progress_callback (Optional[Callable], optional): If this is an \
                UI application, update the progress of the scan. \
                    Defaults to None.

        Returns:
            EventScanDTO:  All processed events, number of chunks used

        Raises:
            RelayerEventScanFailed
        """
        if start_block > end_block:
            msg = "Failed scan! Start block is greater than end block."
            raise RelayerEventScanFailed(msg)

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        events: List[EventDTO] = []
        current_block = start_block
        end_block_timestamp: Optional[datetime] = None

        while current_block <= end_block:
            estimated_end_block = current_block + chunk_size

            (
                events_scanned,
                end_block
            ) = self.blockchain_provider.scan(
                start_block=current_block,
                end_block=estimated_end_block,
            )

            current_end = end_block
            events += events_scanned
            end_block_timestamp = \
                self.blockchain_provider.get_block_timestamp(end_block)

            if progress_callback is not None:
                progress_callback(
                    start_block=start_block,
                    end_block=end_block,
                    current_block=current_block,
                    current_block_timestamp=end_block_timestamp,
                    chunk_size=chunk_size,
                    events_count=len(events_scanned)
                )

            # Try to guess how many blocks to fetch over `eth_getLogs`
            # API next time
            chunk_size: int = self.estimate_next_chunk_size(
                current_chuck_size=chunk_size,
                event_found_count=len(events_scanned)
            )

            # Set where the next chunk starts
            current_block = current_end + 1
            total_chunks_scanned += 1

        return EventScanDTO(
            events=events,
            chunks_scanned=total_chunks_scanned
        )

    def run_scan_with_progress_bar_render(
        self,
        start_block: int,
        end_block: int,
        start_chunk_size: int,
    ) -> EventScanDTO:
        """Scan and render a progress bar in the console.

        Args:
            Args:
            start_block (int): start_block: The first block included
                in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch \
                over JSON-RPC on the first attempt. Defaults to 20.

        Returns:
            EventScanDTO: All processed events, number of chunks used
        """
        blocks_to_scan = end_block - start_block

        with tqdm(total=blocks_to_scan) as progress_bar:
            def _update_progress(
                start_block: int,
                end_block: int,
                current_block: int,
                current_block_timestamp: Optional[datetime],
                chunk_size: int,
                events_count: int,
            ):
                if current_block_timestamp:
                    formatted_time = \
                        current_block_timestamp.strftime("%d-%m-%Y")
                else:
                    formatted_time = "no block time available"

                progress_bar.set_description(
                    f"{self.Emoji.blockFinality.value}"
                    f"chain_id={self.chain_id} "
                    f"Current block: {current_block} ({formatted_time}), "
                    f"blocks in a scan batch: {chunk_size}, events "
                    f"processed in a batch {events_count}"
                )
                progress_bar.update(chunk_size)

            # Run the scan
            return self.scan(
                start_block=start_block,
                end_block=end_block,
                start_chunk_size=start_chunk_size,
                progress_callback=_update_progress
            )
