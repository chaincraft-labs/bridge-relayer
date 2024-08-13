from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from src.relayer.domain.base import BaseResult

@dataclass
class EventDataDTO:
    """Event data DTO."""
    
    block_number: int
    tx_hash: int
    log_index: int
    event: Dict[str, Any]
    block_datetime: datetime

    def __str__(self) -> str:
        """Get the event name.

        Returns:
            str: The event name
        """
        return self.event['event']
    
    def as_key(self) -> str:
        """Get the event key that is a concatenation of 
          
          - block number
          - tx hash
          - log index

        Returns:
            str: The event key
        """
        return f"{self.block_number}-{self.tx_hash}-{self.log_index}"


@dataclass
class EventDatasDTO:
    """Aggregate of Event data."""

    event_datas: List[EventDataDTO]
    end_block: int
    end_block_timestamp: datetime


@dataclass
class EventDatasScanDTO:
    """Result of event data scanned."""

    event_datas: List[EventDataDTO]
    end_block_timestamp: datetime
    chunks_scanned: int


@dataclass
class EventDatasScanResult(BaseResult):
    """Result of scan process."""
    