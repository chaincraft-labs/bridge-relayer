# """Application for the bridge relayer."""
# import sys
# from typing import List
# from time import time
# from datetime import datetime

# from src.relayer.application import BaseApp
# from src.relayer.application.register_event import RegisterEvent
# from src.relayer.domain.config import (
#     RelayerRegisterConfigDTO,
#     RelayerBlockchainConfigDTO,
# )
# from src.utils.converter import to_bytes
# from src.relayer.interface.relayer import (
#     IRelayerBlockchain,
#     IRelayerRegister,
# )
# from src.relayer.domain.relayer import (
#     RegisterEventResult,
#     EventDTO,
# )
# from src.relayer.config.config import (
#     get_blockchain_config,
#     get_register_config,
# )


# class ManageEventFromBlockchain(BaseApp):
#     """Manage blockchain event listener."""

#     def __init__(
#         self,
#         relayer_blockchain_provider: IRelayerBlockchain,
#         relayer_register_provider: IRelayerRegister,
#         chain_id: int,
#         event_filters: List[str],
#         verbose: bool = True
#     ) -> None:
#         """Init blockchain event listener instance.

#         Args:
#             relayer_blockchain_event (IRelayerBlockchainEvent):
#                 The relayer blockchain provider
#             relayer_blockchain_config (RelayerBlockchainConfigDTO):
#                 The relayer blockchain configuration
#             chain_id (int): The chain id
#             event_filters (List): The list of event to manage
#             verbose (bool, optional): Verbose mode. Defaults to True.
#         """
#         self.register_config: RelayerRegisterConfigDTO = get_register_config()
#         self.blockchain_config: RelayerBlockchainConfigDTO = get_blockchain_config(chain_id)
#         self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
#         self.rr_provider: IRelayerRegister = relayer_register_provider
#         self.chain_id: int = chain_id
#         self.event_filters: List[str] = event_filters
#         self.verbose: bool = verbose

#     def __call__(self) -> None:
#         """Listen event main function."""

#         try:
#             self.listen_events()
#         except KeyboardInterrupt:
#             self.print_log("emark", "Keyboard Interrupt")
#             sys.exit()
#         except Exception as e:
#             self.print_log("fail", f"Error={e}")
#             self()

#     def listen_events(self, poll_interval: int = 2) -> None:
#         """The blockchain event listener.

#         Args:
#             poll_interval int: The loop poll interval in second. Default is 2
#         """
#         self.rb_provider.set_chain_id(self.chain_id)
#         self.rb_provider.set_event_filter(self.event_filters)
#         # config: RelayerBlockchainConfigDTO = get_blockchain_config(self.chain_id)

#         self.print_log("main", "Running the event listener ...")
#         self.print_log("emark", f"chain_id        : {self.chain_id}")
#         # self.print_log("emark", f"contract address: {config.smart_contract_address}")
#         self.print_log("emark", f"contract address: {self.blockchain_config.smart_contract_address}")
#         self.print_log("emark", f"listen to events: {self.event_filters}")

#         self.rb_provider.listen_events(
#             callback=self._handle_event,
#             poll_interval=poll_interval,
#         )

#     def _handle_event(self, event_dto: EventDTO) -> RegisterEventResult:
#         """Handle the event received from blockchain.

#         Args:
#             event_dto (EventDTO): The event DTO

#         Return:
#             RegisterEventResult: The event registered result
#         """
#         event_dto_to_byte: bytes = self._convert_data_to_bytes(event=event_dto)
#         self.print_log("receiveEvent", f"Received event: {event_dto}")
#         app = RegisterEvent(
#             relayer_register_provider=self.rr_provider,
#             verbose=self.verbose
#         )
#         return app(event=event_dto_to_byte)

#     def _convert_data_to_bytes(self, event: EventDTO) -> bytes:
#         """Convert attribut data to bytes.

#         Args:
#             event (EventDTO): The event DTO

#         Returns:
#             bytes: The event DTO as bytes format
#         """
#         return to_bytes(data=event)


#     # def scan(
#     #     self, 
#     #     start_block: int, 
#     #     end_block: int, 
#     #     handle_event: Callable,
#     #     start_chunk_size: int = 20, 
#     #     progress_callback: Optional[Callable] = None,
#     # ) -> Tuple[list, int]:
#     #     """Perform a token balances scan.

#     #     Assumes all balances in the database are valid before start_block 
#     #         (no forks sneaked in).

#     #     Args:
#     #         start_block (int): start_block: The first block included in the scan
#     #         end_block (int): The last block included in the scan
#     #         handle_event (callable): Handle the event (storage)
#     #         start_chunk_size (int, optional): How many blocks we try to fetch 
#     #             over JSON-RPC on the first attempt. Defaults to 20.
#     #         progress_callback (Optional[Callable], optional): If this is an 
#     #             UI application, update the progress of the scan. Defaults to None.

#     #     Returns:
#     #         Tuple[list, int]: All processed events, number of chunks used
#     #     """
#     #     if start_block >= end_block:
#     #         raise BridgeRelayerInvalidStartBlock(
#     #             "Failed scan! Start block is greater than end block."
#     #         )

#     #     # Scan in chunks, commit between
#     #     chunk_size = start_chunk_size
#     #     last_scan_duration = last_logs_found = 0
#     #     total_chunks_scanned = 0

#     #     # All processed entries we got on this scan cycle
#     #     all_processed: List[str] = []
        
#     #     current_block = start_block

#     #     while current_block <= end_block:
#     #         estimated_end_block = current_block + chunk_size

#     #         self.logger.debug(
#     #             f"Scanning token transfers for blocks: "
#     #             f"{current_block} - {estimated_end_block}, chunk size "
#     #             f"{chunk_size}, last chunk scan took {last_scan_duration}, "
#     #             f"last logs found {last_logs_found}"
#     #         )

#     #         start = time()
            
#     #         actual_end_block: int
#     #         end_block_timestamp: datetime 
#     #         new_entries: List[str]

#     #         (
#     #             actual_end_block, 
#     #             end_block_timestamp, 
#     #             new_entries
#     #         ) = self.scan_chunk(
#     #             start_block=current_block, 
#     #             end_block=estimated_end_block,
#     #             handle_event=handle_event,
#     #         )

#     #         # Where does our current chunk scan ends - are we out of chain yet?
#     #         current_end = actual_end_block
#     #         last_scan_duration = time() - start
#     #         all_processed += new_entries

#     #         # Print progress bar
#     #         if progress_callback is not None:
#     #             progress_callback(
#     #                 start_block=start_block, 
#     #                 end_block=end_block, 
#     #                 current_block=current_block, 
#     #                 end_block_timestamp=end_block_timestamp, 
#     #                 chunk_size=chunk_size, 
#     #                 events_count=len(new_entries)
#     #             )

#     #         # Try to guess how many blocks to fetch over `eth_getLogs` 
#     #         # API next time
#     #         chunk_size: int = self.estimate_next_chunk_size(
#     #             current_chuck_size=chunk_size, 
#     #             event_found_count=len(new_entries)
#     #         )

#     #         # Set where the next chunk starts
#     #         current_block = current_end + 1
#     #         total_chunks_scanned += 1
            
#     #         # 
#     #         # STORAGE HERE
#     #         # self.state.end_chunk(current_end, end_block)

#     #     return all_processed, total_chunks_scanned

