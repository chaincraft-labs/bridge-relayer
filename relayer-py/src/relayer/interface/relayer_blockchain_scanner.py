"""Interface for Bridge Relayer."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, List, Optional

from src.relayer.domain.relayer import (
    BridgeTaskResult,
)
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
)
from src.relayer.domain.event import (
    EventDatasDTO,
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
        """
    
    @abstractmethod
    def get_block_number(self) -> int:
        """Get the block number.

        Returns:
            (int): The block number
        """
   
    @abstractmethod
    def listen_events(self, callback: Callable, poll_interval: int) -> Any:
        """The blockchain event listener.

        Args:
            poll_interval int: The loop poll interval in second 
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
            BridgeTaskResult: The bridge task execution result
        """

    @abstractmethod
    def get_suggested_scan_end_block(self) -> int:
        """Get the last mined block on Ethereum chain we are following.

        Returns:
            int: The suggested block number
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
            EventDatasDTO: Events, end block, end block timestamp 
        """

    @abstractmethod
    async def client_version(self) -> str:
        """Get the client version

        Returns:
            str: the client version
        """

    @abstractmethod
    def get_account_address(self) -> str:
        """Get the account address

        Returns:
            str: The account address
        """
