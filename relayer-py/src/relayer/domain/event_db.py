from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional


class EventTxDataDTO(BaseModel):
    """Relayer Tx data DTO."""

    event_name: str
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
    block_datetime: datetime
    handled: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    def as_key(self) -> str:
        """Get the event key that is a concatenation of"""
        return f"{self.operation_hash_str}-{self.event_name}"

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


class EventTxDTO(BaseModel):
    """Event Tx DTO."""

    chain_id: int
    block_number: int
    tx_hash: str
    log_index: int
    data: EventTxDataDTO
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    def as_key(self) -> str:
        """Get the event key that is a concatenation of 
          
          - chain id
          - block number
          - tx hash
          - log index

        Returns:
            str: The event key
        """
        return (
            f"{self.chain_id}-{self.block_number}-{self.tx_hash}-"
            f"{self.log_index}"
        )


class EventDataDTO(BaseModel):
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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

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


class EventDTO(BaseModel):
    """Event."""
    
    chain_id: int
    event_name: str
    block_number: int
    tx_hash: str
    log_index: int
    block_datetime: datetime
    handled: Optional[str] = None
    data: EventDataDTO
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    def as_key(self) -> str:
        """Get the event key that is a concatenation of 
          
          - block number
          - tx hash
          - log index

        Returns:
            str: The event key
        """
        return f"{self.block_number}-{self.tx_hash}-{self.log_index}"


class EventsDTO(BaseModel):
    """Aggregate of Event data."""

    event_datas: List[EventDTO]
    end_block: int


class EventScanDTO(BaseModel):
    """Result of event data scanned."""

    events: List[EventDTO]
    chunks_scanned: int


class BridgeTaskDTO(BaseModel):
    """Bridge Task."""
    
    chain_id: int
    block_number: int
    tx_hash: str
    log_index: int
    operation_hash: str
    event_name: str
    status: str
    datetime: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    def as_key(self) -> str:
        return f"{self.operation_hash}-{self.event_name}"
    
    def as_id(self) -> str: 
        return f"{self.block_number}-{self.tx_hash}-{self.log_index}"

class BridgeTaskActionDTO(BaseModel):
    """DTO for blockchain bridge relayer contract's function."""

    operation_hash: str
    func_name: str
    params: Dict[str, Any]


class BridgeTaskTxResult(BaseModel):
    """Result DTO for bridge task Transaction."""

    tx_hash: str
    block_hash: str
    block_number: int
    gas_used: int
    status: int