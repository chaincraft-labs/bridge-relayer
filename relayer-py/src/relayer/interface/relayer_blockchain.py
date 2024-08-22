"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.relayer.domain.event import (
    BridgeTaskResult,
    BridgeTaskDTO,
    EventDatasDTO
)


class IRelayerBlockchain(ABC):
    """Relayer Interface for blockchain events."""
    
    @abstractmethod
    def connect_client(self, chain_id: int):
        """Connect to the web3 client.

        Args:
            chain_id (int): The chain id
        """

    @abstractmethod
    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.

        Raises:
            RelayerEventsNotFound: Raise error if failed to set events
        """
    
    @abstractmethod
    async def call_contract_func(
        self, 
        bridge_task_dto: BridgeTaskDTO
    ) -> BridgeTaskResult:
        """Call a contract's function.

        Args:
            bridge_task_dto (BridgeTaskDTO): The bridge task DTO

        Returns:
            BridgeTaskTxResult: The bridge transaction result

        Raises:
            RelayerBlockchainFailedExecuteSmartContract: Raise error if failed \
                to execute smart contract
        """

    @abstractmethod
    def get_current_block_number(self) -> int:
        """Get the current block number on chain.

        Returns:
            (int): The current block number
        """

    @abstractmethod
    def scan(
        self, 
        start_block: int, 
        end_block: int,
    ) -> EventDatasDTO:
        """Read and process events between two block numbers.

        Args:
            start_block (int): The first block to scan
            end_block (int): The last block to scan

        Returns:
            EventDatasDTO: Events, end block
        """

    @abstractmethod
    def client_version(self) -> str:
        """Get the client version

        Returns:
            str: the client version
        Raises:
            RelayerClientVersionError: Failed to get client version
        """

    @abstractmethod
    def get_account_address(self) -> str:
        """Get the account address

        Returns:
            str: The account address
        """

    @abstractmethod
    def get_block_timestamp(self, block_num: int) -> Optional[datetime]:
        """Get Ethereum block timestamp.

        Args:
            block_num (int): The block number

        Returns:
            Optional[datetime]: The block timestamp
        """
