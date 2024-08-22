from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from src.relayer.domain.base import BaseResult


@dataclass
class RelayerParamsDTO:
    """Relayer params DTO."""

    from_: str               # "0x0000000000000000000000000000000000000000"
    to: str                     # "0x0000000000000000000000000000000000000000"
    chain_id_from: int            # 1337
    chain_id_to: int              # 440
    token_name: str              # "ethereum"
    amount: int                 # 1000000000000000
    nonce: int                  # 20
    signature_str: str          # 0x0000000000000000000000000000000000000000
    signature_bytes: bytes      # b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    operation_hash_str: str     # "0x0000000000000000000000000000000000000000"
    operation_hash_bytes: bytes # b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    block_step: int             # 14836

    def raw_params(self) -> Dict[str, Any]:
        """Get the raw params

        Returns:
            Dict[str, Any]: The raw params
        """
        return {
            "from": self.from_,
            "to": self.to,
            "chainIdFrom": self.chain_id_from,
            "chainIdTo": self.chain_id_to,
            "tokenName": self.token_name,
            "amount": self.amount,
            "nonce": self.nonce,
            "signature": self.signature_bytes,
        }
    
    def params(self) -> Dict[str, Any]:

        return {
            "from": self.from_,
            "to": self.to,
            "chainIdFrom": self.chain_id_from,
            "chainIdTo": self.chain_id_to,
            "tokenName": self.token_name,
            "amount": self.amount,
            "nonce": self.nonce,
            "signature": self.signature_str,
        }


@dataclass
class EventDataDTO:
    """Event data DTO."""
    
    chain_id: int
    event_name: str
    block_number: int
    tx_hash: int
    log_index: int
    block_datetime: datetime
    data: RelayerParamsDTO

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
    # end_block_timestamp: datetime


@dataclass
class EventDatasScanDTO:
    """Result of event data scanned."""

    event_datas: List[EventDataDTO]
    # end_block_timestamp: datetime
    chunks_scanned: int



@dataclass
class BridgeTaskResult(BaseResult):
    """Result DTO for bridge task."""


@dataclass
class BridgeTaskTxResult:
    """Result DTO for bridge task Transaction."""

    tx_hash: str
    block_hash: str
    block_number: int
    gas_used: int


#  Relayer blockchain Task

@dataclass
class BridgeTaskDTO:
    """DTO for blockchain bridge relayer contract's function."""

    operation_hash: str
    func_name: str
    params: Dict[str, Any]

