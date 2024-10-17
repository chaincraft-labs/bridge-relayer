"""Provider to connect to RPC node.

- scan events
- execute smart contracts

The library used is web3.py

https://web3py.readthedocs.io/
"""
from datetime import datetime
from typing import List


from src.relayer.domain.event_db import (
    BridgeTaskActionDTO,
    BridgeTaskTxResult,
    EventDTO,
)
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain


class RelayerBlockchainProvider(IRelayerBlockchain):
    """Relayer blockchain provider."""

    def __init__(
        self,
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000,
        max_request_retries: int = 30,
        request_retry_seconds: float = 3.0,
        num_blocks_rescan_for_forks: int = 10,
        chunk_size_decrease: float = 0.5,
        chunk_size_increase: float = 2.0,
    ) -> None:
        """Relayer blockchain provider.

        Args:
            min_scan_chunk_size (int, optional): Minimum chunk size.
                Defaults to 10.
            max_scan_chunk_size (int, optional): Maximum chunk size.
                Defaults to 10000.
            max_request_retries (int, optional): Maximum number of retries.
                Defaults to 30.
            request_retry_seconds (float, optional): Request retry seconds.
                Defaults to 3.0.
            num_blocks_rescan_for_forks (int, optional): Number of blocks to
                rescan for forks. Defaults to 10.
            chunk_size_decrease (float, optional): Chunk size decrease.
                Defaults to 0.5.
            chunk_size_increase (float, optional): Chunk size increase.
                Defaults to 2.0.
        """

    def connect_client(self, chain_id: int):
        """Connect to the web3 client.

        Args:
            chain_id (int): The chain id.
        """
        raise NotImplementedError

    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.

        Raises:
            RelayerEventsNotFound
        """
        raise NotImplementedError

    def call_contract_func(
        self,
        bridge_task_action_dto: BridgeTaskActionDTO
    ) -> BridgeTaskTxResult:
        """Call a contract's function.

        Args:
            bridge_task_action_dto (BridgeTaskActionDTO): The bridge task DTO.

        Returns:
            BridgeTaskTxResult: The bridge transaction result.

        Raises:
            RelayerBlockchainFailedExecuteSmartContract
        """
        raise NotImplementedError

    def get_current_block_number(self) -> int:
        """Get the current block number on chain.

        Returns:
            (int): The current block number.
        """
        raise NotImplementedError

    def scan(self, start_block: int, end_block: int) -> EventDTO:
        """Read and process events between two block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC
        server pukes out.

        Args:
            start_block (int): The first block to scan
            end_block (int): The last block to scan

        Returns:
            Tuple[List[EventDTO], int]: Events, end block
        """
        raise NotImplementedError

    def client_version(self) -> str:
        """Get the client version.

        Returns:
            str: the client version.

        Raises:
            RelayerClientVersionError
        """
        raise NotImplementedError

    def get_account_address(self) -> str:
        """Get the account address.

        Returns:
            str: The account address.
        """
        raise NotImplementedError

    def get_block_timestamp(self, block_num: int) -> datetime | None:
        """Get Ethereum block timestamp.

        Args:
            block_num (int): The block number.

        Returns:
            Optional[datetime]: The block timestamp
        """
        raise NotImplementedError
