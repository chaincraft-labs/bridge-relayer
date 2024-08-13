"""Application for the bridge relayer."""
import asyncio
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple
from time import sleep, time
from datetime import datetime
from tqdm import tqdm
from src.relayer.application import BaseApp
from src.relayer.application.register_event import RegisterEvent
from src.relayer.domain.config import (
    RelayerRegisterConfigDTO,
    RelayerBlockchainConfigDTO,
)
from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO,
    EventDatasScanDTO,
    EventDatasScanResult,
)
from src.utils.converter import to_bytes
from src.relayer.interface.relayer import (
    IRelayerRegister,
)
from src.relayer.interface.relayer_blockchain_scanner import (
    IRelayerBlockchain
)
from src.relayer.interface.event_storage import IEventDataStore
from src.relayer.domain.relayer import (
    RegisterEventResult,
    EventDTO,
)
from src.relayer.config.config import (
    get_blockchain_config,
    get_register_config,
)
from src.relayer.application.base_logging import RelayerLogging


class ManageEventFromBlockchain(RelayerLogging, BaseApp):
    """Manage blockchain event listener."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        event_datastore_provider: IEventDataStore,
        chain_id: int,
        event_filters: List[str],
        verbose: bool = True,
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
            chain_id (int): The chain id
            event_filters (List): The list of event to manage
            verbose (bool, optional): Verbose mode. Defaults to True.
        """
        super().__init__()
        self.chain_id: int = chain_id
        self.event_filters: List[str] = event_filters
        self.verbose: bool = verbose
        # configurations
        self.register_config: RelayerRegisterConfigDTO = get_register_config()
        self.blockchain_config: RelayerBlockchainConfigDTO = get_blockchain_config(chain_id)
        # providers
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.evt_store: IEventDataStore = event_datastore_provider

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = min_scan_chunk_size  # 12 s/block = 120 seconds period
        self.max_scan_chunk_size = max_scan_chunk_size
        self.chunk_size_increase = chunk_size_increase

    def __call__(
            self,
            start_chunk_size: int = 20,
            chain_reorg_safety_blocks: int = 10,
            progress_bar: bool = True,
            auto_commit: bool = True,
            as_service: bool = False,
            verbose: int = True,
        ) -> None:
        """Main Scan events from RPC node

        Assume we might have scanned the blocks all the way to the last 
        Ethereum block that mined a few seconds before the previous scan 
        run ended.
        Because there might have been a minor Ethereum chain reorganisations
        since the last scan ended, we need to discard the last few blocks 
        from the previous scan results.

        Args:
            start_chunk_size (int, optional): _description_. Defaults to 20.
            chain_reorg_safety_blocks (int, optional): _description_. Defaults to 10.
            progress_bar (bool, optional): _description_. Defaults to True.
            auto_commit (bool, optional): _description_. Defaults to True.
        """
        self.verbose = verbose
        # Load state from previous scan or init a new one
        self.evt_store.read_events()
        self.evt_store.delete_event(
            since_block=chain_reorg_safety_blocks,
            auto_commit=auto_commit
        )

        # Connect to blockchain
        self.rb_provider.connect_client(chain_id=self.chain_id)
        self.rb_provider.set_event_filter(events=self.event_filters)

        # Set start and end block
        last_scanned_block: int = self.evt_store.get_last_scanned_block()
        start_block: int = max(last_scanned_block - chain_reorg_safety_blocks,
            self.blockchain_config.genesis_block,
        )
        # The last block mined minus 1 block
        end_block: int = self.rb_provider.get_suggested_scan_end_block()
        blocks_to_scan = end_block - start_block

        # Render a progress bar in the console
        start = time()
        scan = self.run_scan_with_progress_bar_render if progress_bar else self.scan

        # -----------------------------------------------------------------
        title_length = 20
        self.print_log("none", f"{"rpc_url":<{title_length}} : {self.blockchain_config.rpc_url}")
        # self.print_log("none", f"{"client version":<{title_length}} : {asyncio.run(self.rb_provider.client_version())}")
        self.print_log("none", f"{"client version":<{title_length}} : {self.rb_provider.client_version()}")
        self.print_log("none", f"{"chain_id":<{title_length}} : {self.chain_id}")
        self.print_log("none", f"{"Account address":<{title_length}} : {self.rb_provider.get_account_address()}")
        self.print_log("none", f"{"Contract address":<{title_length}} : {self.blockchain_config.smart_contract_address}")
        self.print_log("none", f"{"genesis block":<{title_length}} : {self.blockchain_config.genesis_block}")
        self.print_log("none", f"{"start_block":<{title_length}} : {start_block}")
        self.print_log("none", f"{"end_block":<{title_length}} : {end_block}")
        self.print_log("none", f"{"blocks_to_scan":<{title_length}} : {blocks_to_scan}")

        scan_as_service = True

        while scan_as_service:
            # Scan events
            event_datas_dto_result: EventDatasScanResult = scan(
                start_block=start_block,
                end_block=end_block,
                start_chunk_size=start_chunk_size
            )

            if event_datas_dto_result.err:
                self.print_log(
                    "alert",
                    f"Error while scanning events for chain_id={self.chain_id}"
                )
                return

            event_datas_dto: EventDatasScanDTO = event_datas_dto_result.ok
            all_event_datas: List[EventDataDTO] = event_datas_dto.event_datas
            total_chunks_scanned: int = event_datas_dto.chunks_scanned
            event_datas_to_store: List[EventDataDTO] = []
            
            # Create event dto and register event (Message queuing)
            for event_data in all_event_datas:
                event_key = event_data.as_key()

                # Check if event has already been scanned and stored
                # Avoid duplicata
                if not self.evt_store.is_event_stored(event_key=event_key):
                    event_datas_to_store.append(event_data)
                    self.evt_store.save_event(
                        event=event_data, 
                        auto_commit=auto_commit
                    )

                # Check if event has already been registerd
                if not self.evt_store.is_event_registered(event_key=event_key):
                    event_dto = self.create_event_dto(event_data=event_data)
                    self.register_event(event_dto=event_dto)
                    self.evt_store.set_event_as_registered(event_key=event_key)

            if len(event_datas_to_store) > 0:
                duration = time() - start
                self.print_log(
                    "success",
                    f"Scanned total {len(all_event_datas)} events, "
                    f"in {duration} seconds, total {total_chunks_scanned} "
                    f"chunk scans performed"
                )

            # commit any changes
            self.evt_store.set_last_scanned_block(block_numer=end_block)
            self.evt_store.commit()

            if as_service is False:
                scan_as_service = False
            else:
                sleep(1)
                end_block: int = self.rb_provider.get_suggested_scan_end_block()
                start_block = end_block - chain_reorg_safety_blocks

    def register_event(self, event_dto: EventDTO) -> RegisterEventResult:
        """Register the event received from blockchain.

        Args:
            event_dto (EventDTO): The event DTO

        Return:
            RegisterEventResult: The event registered result
        """
        event_dto_to_byte: bytes = self._convert_data_to_bytes(event=event_dto)
        # self.print_log("receiveEvent", f"Received event: {event_dto}")
        app = RegisterEvent(
            relayer_register_provider=self.rr_provider,
            verbose=self.verbose
        )
        return app(event=event_dto_to_byte)

    def _convert_data_to_bytes(self, event: EventDTO) -> bytes:
        """Convert attribut data to bytes.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bytes: The event DTO as bytes format
        """
        return to_bytes(data=event)

    def create_event_dto(self, event_data: EventDataDTO) -> EventDTO:
        """Create an EventDTO from an EventDataDTO.

        Args:
            event_data (EventDataDTO): An Event data DTO

        Returns:
            EventDTO: The event DTO
        """
        return EventDTO(
            name=event_data.event['event'],
            data=event_data.event['args'],
            block_key=event_data.as_key()
        )

    def estimate_next_chunk_size(
        self, 
        current_chuck_size: float, 
        event_found_count: int
    ) -> int:
        """Try to figure out optimal chunk size

        Our scanner might need to scan the whole blockchain for all events

        * We want to minimize API calls over empty blocks
        * We want to make sure that one scan chunk does not try to process too 
            many entries once, as we try to control commit buffer size and 
            potentially asynchronous busy loop
        * Do not overload node serving JSON-RPC API by asking data for too 
            many events at a time

        Currently Ethereum JSON-API does not have an API to tell when a first 
        event occurred in a blockchain and our heuristics try to accelerate 
        block fetching (chunk size) until we see the first event.

        These heuristics exponentially increase the scan chunk size depending 
        on if we are seeing events or not.
        When any transfers are encountered, we are back to scanning only a few 
        blocks at a time.
        It does not make sense to do a full chain scan starting from block 1, 
        doing one JSON-RPC call per 20 blocks.

        Args:
            current_chuck_size (float): _description_
            event_found_count (int): _description_

        Returns:
            _type_: _description_
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
    ) -> EventDatasScanResult:
        """Scan and render a progress bar in the console

        Args:
            Args:
            start_block (int): start_block: The first block included in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch 
                over JSON-RPC on the first attempt. Defaults to 20.

        Returns:
            EventDatasScanResult: All processed events, number of chunks used
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
                    # f"{self.Emoji['blockFinality'].value} start: {start_block} end: {end_block}, "
                    f"{self.Emoji['blockFinality'].value} "
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
    ) -> EventDatasScanResult:
        """Scan events from blockchain (rpc node).

        Args:
            start_block (int): start_block: The first block included in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch 
                over JSON-RPC on the first attempt. Defaults to 20.
            progress_callback (Optional[Callable], optional): If this is an 
                UI application, update the progress of the scan. Defaults to None.

        Returns:
            EventDatasScanResult:  All processed events, number of chunks used
        """
        event_datas_scan_result = EventDatasScanResult()

        if start_block >= end_block:
            msg = "Failed scan! Start block is greater than end block."
            event_datas_scan_result.err = msg
            return event_datas_scan_result

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        last_scan_duration = last_logs_found = 0
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        all_event_datas: List[EventDataDTO] = []
        current_block = start_block
        end_block_timestamp: Optional[datetime] = None

        while current_block <= end_block:
            estimated_end_block = current_block + chunk_size

            self.logger.debug(
                f"Scanning token transfers for blocks: "
                f"{current_block} - {estimated_end_block}, chunk size "
                f"{chunk_size}, last chunk scan took {last_scan_duration}, "
                f"last logs found {last_logs_found}"
            )

            start = time()
            event_datas_dto: EventDatasDTO = self.rb_provider.scan(
                start_block=current_block, 
                end_block=estimated_end_block,
            )
            
            # Where does our current chunk scan ends - are we out of chain yet?
            # current_end = actual_end_block
            current_end = event_datas_dto.end_block
            last_scan_duration = time() - start
            all_event_datas += event_datas_dto.event_datas
            end_block_timestamp = event_datas_dto.end_block_timestamp

            # Print progress bar
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

        event_datas_scan_result.ok = EventDatasScanDTO(
            event_datas=all_event_datas,
            end_block_timestamp=end_block_timestamp,
            chunks_scanned=total_chunks_scanned
        )

        return event_datas_scan_result
