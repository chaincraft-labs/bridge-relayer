"""Relayer blockchain provider mocked."""
import asyncio
import random
import secrets
from typing import Any, Callable, List


from src.relayer.domain.event import EventDatasDTO
from src.relayer.domain.exception import BridgeRelayerListenEventFailed
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    BridgeTaskResult,
    BridgeTaskTxResult
)
from src.relayer.interface.relayer_blockchain_scanner import IRelayerBlockchain
from src.relayer.domain.config import (
    RelayerBlockchainConfigDTO,
)

def get_blockchain_config(chain_id):
    config = RelayerBlockchainConfigDTO(
        chain_id=123, 
        rpc_url='https://fake.rpc_url.org', 
        project_id='JMFW2926FNFKRMFJF1FNNKFNKNKHENFL', 
        pk='abcdef12345678890abcdef12345678890abcdef12345678890abcdef1234567', 
        wait_block_validation=6, 
        block_validation_second_per_block=0,
        smart_contract_address='0x1234567890abcdef1234567890abcdef12345678', 
        genesis_block=123456789, 
        abi=[{}], 
        client='middleware'
    )
    return config


class MockRelayerBlockchainProvider(IRelayerBlockchain):
    """Mock RelayerBlockchainProvider provider"""

    def __init__(self, debug: bool = False, exception = None):
        self.exception = exception
        self._debug: bool = debug
        self.chain_id: int
        self.relay_blockchain_config: Any
        self.event_filter: List[str] = []
        self.block_number = 0
        self.sleep = 0
        self.tx_hash = None

    async def get_block_number(self):
        self.block_number += 1
        await asyncio.sleep(self.sleep)
        return self.block_number
        
    def set_chain_id(self, chain_id: int):
        self.chain_id = chain_id
        self.relay_blockchain_config = get_blockchain_config(self.chain_id)

    def set_event_filter(self, events: List[str]):
        assert isinstance(events, list)
        self.event_filter = events

    def listen_events(self, callback: Callable[..., Any], poll_interval: int) -> Any:
        try:
            if self.exception:
                raise self.exception

        except Exception as e:
            raise BridgeRelayerListenEventFailed(e)

    async def call_contract_func(
        self, 
        bridge_task_dto: BridgeTaskDTO
    ) -> BridgeTaskResult:
        result = BridgeTaskResult()

        try:
            if self.exception:
                raise self.exception
            
            await asyncio.sleep(self.sleep)

            tx_hash = f"0x{secrets.token_bytes(32).hex()}"
            if self.tx_hash:
                tx_hash = self.tx_hash

            result.ok = BridgeTaskTxResult(
                tx_hash=tx_hash,
                block_hash=f"0x{secrets.token_bytes(32).hex()}",
                block_number=random.randint(10, 100),
                gas_used=123
            )
        except Exception as e:
            result.err = e

        return result

    def connect_client(self, chain_id: int):
        pass

    def get_suggested_scan_end_block(self):
        return 15123

    def scan(self, start_block: int, end_block: int) -> EventDatasDTO:
        pass

    async def client_version(self) -> str:
        pass

    def get_account_address(self) -> str:
        pass



