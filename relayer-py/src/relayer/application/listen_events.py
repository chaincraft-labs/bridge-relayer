"""Bridge Relayer event listener from RPC node."""
from typing import Callable, List, Optional
from time import sleep, time
from datetime import datetime
from tqdm import tqdm

from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.config.config import (
    get_blockchain_config,
    get_register_config,
)
from src.relayer.domain.config import (
    RelayerRegisterConfigDTO,
    RelayerBlockchainConfigDTO,
)
from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO,
    EventDatasScanDTO,
)
from src.relayer.domain.exception import (
    RelayerEventScanFailed,
    RelayerRegisterEventFailed,
    EventDataStoreNoBlockToDelete
)
from src.relayer.interface.relayer_register import IRelayerRegister
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain
from src.relayer.interface.event_storage import IEventDataStore
from src.utils.converter import to_bytes


class ListeEvents(RelayerLogging, BaseApp):
    """Listen blockchain events."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        event_datastore_provider: IEventDataStore,
        chain_id: int,
        event_filters: List[str],
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000,
        chunk_size_increase: float = 2.0,
        log_level: str = 'info',
    ) -> None:
        """Init blockchain event listener instance.

        Args:
            relayer_blockchain_event (IRelayerBlockchainEvent):
                The relayer blockchain provider
            relayer_blockchain_config (RelayerBlockchainConfigDTO):
                The relayer blockchain configuration
            event_datastore_provider (IEventDataStore): The event datastore
            chain_id (int): The chain id
            event_filters (List): The list of event to manage
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
        self.event_filters: List[str] = event_filters
        # configurations
        self.register_config: RelayerRegisterConfigDTO = get_register_config()
        self.blockchain_config: RelayerBlockchainConfigDTO = \
            get_blockchain_config(chain_id)
        # providers
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.evt_store: IEventDataStore = event_datastore_provider
        # Set chain id
        self.evt_store.set_chain_id(chain_id)
        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = min_scan_chunk_size
        self.max_scan_chunk_size = max_scan_chunk_size
        self.chunk_size_increase = chunk_size_increase

    async def __call__(
            self,
            start_chunk_size: int = 20,
            block_to_delete: int = 10,
            progress_bar: bool = True,
            auto_commit: bool = True,
            as_service: bool = False,
            log_level: str = 'info',
        ) -> None:
        """Event scanner from RPC node

        Assume we might have scanned the blocks all the way to the last 
        Ethereum block that mined a few seconds before the previous scan 
        run ended.
        Because there might have been a minor Ethereum chain reorganisations
        since the last scan ended, we need to discard the last few blocks 
        from the previous scan results.

        Args:
            start_chunk_size (int, optional): Chunk size. Defaults to 20.
            block_to_delete (int, optional): How many blocks to delete. \
                Defaults to 10.
            progress_bar (bool, optional): Show progress bar. Defaults to True.
            auto_commit (bool, optional): Commit state to data store. \
                Defaults to True.
            as_service (bool, optional): Run as service. Defaults to False.
            log_level (str, optional): The log level. Defaults to 'info'.

        """
        super().__init__(level=log_level)
        self.log_level = log_level
        self.rb_provider.connect_client(chain_id=self.chain_id)
        self.rb_provider.set_event_filter(events=self.event_filters)
        current_block: int = self.rb_provider.get_current_block_number()
        self.delete_event(
            current_block=current_block,
            block_to_delete=block_to_delete,
            auto_commit=auto_commit
        )
        last_scanned_block: int = self.evt_store.get_last_scanned_block()
        end_block: int = self.get_suggested_scan_end_block()        
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
                event_datas_dto: EventDatasScanDTO = scan(
                    start_block=start_block,
                    end_block=end_block,
                    start_chunk_size=start_chunk_size
                )
            except RelayerEventScanFailed as e:
                msg = (f"chain_id={self.chain_id} {e}")
                self.logger.error(f"{self.Emoji.fail.value}{msg}")
                self.print_log("alert", msg)
                return
            
            all_event_datas: List[EventDataDTO] = event_datas_dto.event_datas
            total_chunks_scanned: int = event_datas_dto.chunks_scanned
            stored_events: List[EventDataDTO] = []

            for event_data_dto in all_event_datas:
                if event_data_dto is None:
                    continue

                stored_events = self.store_event(event_data_dto, auto_commit)
                await self.register_event(event_data_dto, auto_commit)

            if len(stored_events) > 0:
                duration = time() - start
                self.print_log(
                    "success",
                    f"chain_id={self.chain_id} Scanned total "
                    f"{len(all_event_datas)} events, "
                    f"in {duration} seconds, total {total_chunks_scanned} "
                    f"chunk scans performed"
                )

            self.evt_store.set_last_scanned_block(end_block, auto_commit)

            if as_service is False:
                scan_as_service = False
            else:
                sleep(1)
                end_block: int = self.get_suggested_scan_end_block()
                start_block = end_block - block_to_delete

    def store_event(
        self, 
        event: EventDataDTO,
        auto_commit: bool = False,
    ) -> List[EventDataDTO]:
        """Store event in the state.

        Args:
            event (EventDataDTO): The event DTO
            auto_commit (bool, optional): Commit state to data store. \
                Defaults to False.

        Returns:
            List[EventDataDTO]: List of stored events
        """
        stored_events: List[EventDataDTO] = []

        # Store event if needed
        if not self.evt_store.is_event_stored(event_key=event.as_key()):
            stored_events.append(event)
            
            self.logger.info(
                f"{self.Emoji.info.value}"
                f"chain_id={event.chain_id} "
                f"operationHash={event.data.operation_hash_str} "
                f"New event received {event.as_key()}"
            )

            self.evt_store.save_event(event=event, auto_commit=auto_commit)
        return stored_events

    async def register_event(
        self, 
        event: EventDataDTO, 
        auto_commit: bool = False,
    ) -> None:
        """Register event in message queuing.

        Args:
            event (EventDataDTO): The event DTO
        """
        if not self.evt_store.is_event_registered(event_key=event.as_key()):
            try:
                await self.rr_provider.register_event(event=to_bytes(event))
                self.evt_store.set_event_as_registered(
                    event.as_key(), 
                    auto_commit,
                )

            except RelayerRegisterEventFailed as e:
                pass


    def show_cli_title(
        self,
        start_block: int,
        end_block: int
    ) -> None:
        """Print CLI title

        Args:
            start_block (int): The first block included in the scan
            end_block (int): The last block included in the scan
        """
        title_length = 20
        blocks_to_scan = end_block - start_block

        self.print_log(
            "none", 
            f"{"rpc_url":<{title_length}} : {self.blockchain_config.rpc_url}\n"
            f"{"client version":<{title_length}} : {self.rb_provider.client_version()}\n"
            f"{"chain_id":<{title_length}} : {self.chain_id}\n"
            f"{"Account address":<{title_length}} : {self.rb_provider.get_account_address()}\n"
            f"{"Contract address":<{title_length}} : {self.blockchain_config.smart_contract_address}\n"
            f"{"genesis block":<{title_length}} : {self.blockchain_config.genesis_block}\n"
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
        return self.rb_provider.get_current_block_number() - 1

    def delete_event(
        self, 
        current_block: int,
        block_to_delete: int,
        auto_commit: bool = True
    ) -> None:
        """Delete any data since this block was scanned.

        Args:
            current_block (int): The current block on chain
            block_to_delete (int): The number of blocks to delete
            auto_commit (bool, optional): Commit state to data store. Defaults to True.
        """
        try:
            self.evt_store.delete_event(
                current_block=current_block,
                block_to_delete=block_to_delete,
                auto_commit=auto_commit,
            )
        except EventDataStoreNoBlockToDelete as e:
            self.logger.info(
                f"{self.Emoji.info.value}chain_id={self.chain_id} {e}"
            )

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

    def run_scan_with_progress_bar_render(
        self, 
        start_block:int,
        end_block: int,
        start_chunk_size: int,
    ) -> EventDatasScanDTO:
        """Scan and render a progress bar in the console

        Args:
            Args:
            start_block (int): start_block: The first block included in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch \
                over JSON-RPC on the first attempt. Defaults to 20.

        Returns:
            EventDatasScanDTO: All processed events, number of chunks used
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
                    formatted_time = current_block_timestamp.strftime("%d-%m-%Y")
                else:
                    formatted_time = "no block time available"

                progress_bar.set_description(
                    f"{self.Emoji.blockFinality.value}chain_id={self.chain_id} "
                    f"Current block: {current_block} ({formatted_time}), "
                    f"blocks in a scan batch: {chunk_size}, events "
                    f"processed in a batch {events_count}")
                progress_bar.update(chunk_size)

            # Run the scan
            return self.scan(
                start_block=start_block, 
                end_block=end_block,
                start_chunk_size=start_chunk_size,
                progress_callback=_update_progress
            )

    def scan(
        self, 
        start_block: int, 
        end_block: int, 
        start_chunk_size: int = 20, 
        progress_callback: Optional[Callable] = None,
    ) -> EventDatasScanDTO:
        """Scan events from blockchain (rpc node).

        Args:
            start_block (int): start_block: The first block included in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch \
                over JSON-RPC on the first attempt. Defaults to 20.
            progress_callback (Optional[Callable], optional): If this is an \
                UI application, update the progress of the scan. \
                    Defaults to None.

        Returns:
            EventDatasScanDTO:  All processed events, number of chunks used
        """
        if start_block >= end_block:
            msg = "Failed scan! Start block is greater than end block."
            raise RelayerEventScanFailed(msg)

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        all_event_datas: List[EventDataDTO] = []
        current_block = start_block
        end_block_timestamp: Optional[datetime] = None

        while current_block <= end_block:
            estimated_end_block = current_block + chunk_size
            event_datas_dto: EventDatasDTO = self.rb_provider.scan(
                start_block=current_block, 
                end_block=estimated_end_block,
            )
            
            current_end = event_datas_dto.end_block
            all_event_datas += event_datas_dto.event_datas
            end_block_timestamp = self.rb_provider.get_block_timestamp(end_block)

            if progress_callback is not None:
                progress_callback(
                    start_block=start_block, 
                    end_block=end_block, 
                    current_block=current_block, 
                    current_block_timestamp=end_block_timestamp, 
                    chunk_size=chunk_size, 
                    events_count=len(event_datas_dto.event_datas)
                )

            # Try to guess how many blocks to fetch over `eth_getLogs` 
            # API next time
            chunk_size: int = self.estimate_next_chunk_size(
                current_chuck_size=chunk_size, 
                event_found_count=len(event_datas_dto.event_datas)
            )

            # Set where the next chunk starts
            current_block = current_end + 1
            total_chunks_scanned += 1

        return EventDatasScanDTO(
            event_datas=all_event_datas,
            chunks_scanned=total_chunks_scanned
        )
