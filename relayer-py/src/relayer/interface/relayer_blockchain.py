"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from src.relayer.domain.event_db import (
    BridgeTaskActionDTO, 
    BridgeTaskTxResult, 
    EventDTO
)


class IRelayerBlockchain(ABC):
    """Relayer Interface for blockchain events."""
    
    @abstractmethod
    def connect_client(self, chain_id: int):
        """Connect to the web3 client.

        Args:
            chain_id (int): The chain id.
        """

    @abstractmethod
    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.

        Raises:
            RelayerEventsNotFound
        """

    @abstractmethod
    def get_current_block_number(self) -> int:
        """Get the current block number on chain.

        Returns:
            (int): The current block number.
        """

    @abstractmethod
    def client_version(self) -> str:
        """Get the client version.

        Returns:
            str: the client version.

        Raises:
            RelayerClientVersionError
        """

    @abstractmethod
    def get_account_address(self) -> str:
        """Get the account address.

        Returns:
            str: The account address.
        """

    @abstractmethod
    def get_block_timestamp(self, block_num: int) -> Optional[datetime]:
        """Get Ethereum block timestamp.

        Args:
            block_num (int): The block number.

        Returns:
            Optional[datetime]: The block timestamp
        """

    @abstractmethod
    def scan(
        self, 
        start_block: int, 
        end_block: int,
    ) -> Tuple[List[EventDTO], int]:
        """Read and process events between two block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC 
        server pukes out.

        Args:
            start_block (int): The first block to scan
            end_block (int): The last block to scan

        Returns:
            Tuple[List[EventDTO], int]: Events, end block
        """

    @abstractmethod
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