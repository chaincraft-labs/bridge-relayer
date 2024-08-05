"""Application for the bridge relayer."""
import asyncio
from typing import Any, Dict

from src.relayer.application import BaseApp
from src.relayer.application.execute_contract import ExecuteContractTask
from src.relayer.domain.exception import (
    BlockFinalityTimeExceededError,
    BridgeRelayerConfigBlockchainDataMissing,
    EventConverterTypeError
)
from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.utils.converter import from_bytes
from src.relayer.interface.relayer import (
    IRelayerBlockchain,
    IRelayerRegister,
)
from src.relayer.domain.relayer import (
    BlockFinalityResult,
    CalculateBlockFinalityResult,
    DefineChainBlockFinalityResult,
    BridgeTaskDTO,
    EventDTO,
)
from src.relayer.config.config import get_blockchain_config


class ConsumeEventTask(BaseApp):
    """Bridge relayer consumer event task."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_consumer_provider: IRelayerRegister,
        verbose: bool = True,
        sleep: int = 1,
        allocated_time: int = 1200,
    ) -> None:
        """Init the relayer consumer.

        Args:
            relayer_blockchain_provider (IRelayerBlockchain:
                The blockchain provider
            relayer_consumer_provider (IRelayerRegister): The consumer provider
            verbose (bool, optional): Enable verbose. Default to True
            sleep (int, optional): Sleep in second. Defaults to 1.
            allocated_time (int, optional): Time in second allocated \
                to wait for block finality
        """
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_consumer_provider
        self.verbose: bool = verbose
        self.operation_hash_events = {}
        self.sleep = sleep
        self.allocated_time = allocated_time

    def __call__(self) -> None:
        """Consumer worker."""
        self.print_log("main", "Waiting for events. To exit press CTRL+C'")
        self.rr_provider.read_events(callback=self._callback)

    def store_operation_hash(
        self,
        operation_hash: str,
        chain_id: int,
        block_step: int,
    ) -> bool:
        """Store the operation hash and the current event name if missing.

        Args:
            operation_hash (str): The operation hash
            chain_id (int): The chain id
            block_step (int): The current block

        Returns:
            bool: The status of storing data
        """
        if self.operation_hash_events.get(operation_hash) is None:
            self.operation_hash_events[operation_hash] = {
                'chain_id': chain_id,
                'block_step': block_step,
            }

            return True
        return False

    def define_chain_for_block_finality(
        self,
        event_dto: EventDTO
    ) -> DefineChainBlockFinalityResult:
        """Define the chain id to validate the block finality.

            Read the `wait_block_validation` defined in
            src.relayer.config.bridge_relayer_config.toml
            `wait_block_validation` means how long it takes for a block to \
                be finalized

            It must be the slowest blockchain.

        Args:
            event_dto (EventDTO): The chain id

        Returns:
            DefineChainBlockFinalityResult:
                ok: The chain id defined to validate block finality
                err: An error
        """
        result = DefineChainBlockFinalityResult()

        chain_a = event_dto.data['params']['chainIdFrom']
        chain_b = event_dto.data['params']['chainIdTo']

        try:
            result.ok = chain_a
            chain_a_config = get_blockchain_config(chain_id=chain_a)
            chain_b_config = get_blockchain_config(chain_id=chain_b)

            if chain_b_config.wait_block_validation \
                    > chain_a_config.wait_block_validation:
                result.ok = chain_b

        except BridgeRelayerConfigBlockchainDataMissing as e:
            result.err = (
                f"Invalid chain ID {[chain_a, chain_b]}. Check "
                f"src.relayer.config.bridge_relayer_config.toml to identify "
                f"available chain IDs. "
                f"Error={e}"
            )

        return result

    def define_block_step_for_block_finality(
        self,
        chain_id: int,
        current_block_step: int,
        saved_chain_id: int,
        saved_block_step: int,
    ) -> int:
        """Define the block step according to the chain id.

        The chain id provided is defined to validate block finality.
        Block step may be the one already saved or the one comming from event

        Args:
            chain_id (int): The chain id defined for validate block finality
            current_block_step (int): The current block number received with event
            saved_chain_id (int): The saved chain id from a previous event
            saved_block_step (int): The saved block step from a previous event

        Returns:
            int: The block step to use for validate the block finality
        """
        if chain_id == saved_chain_id:
            return saved_block_step
        return current_block_step

    def calculate_block_finality(
        self,
        chain_id: int,
        block_step: int
    ) -> CalculateBlockFinalityResult:
        """Calculate the block finality.

        Args:
            chain_id (int): The chain id
            block_step (int): The current block

        Returns:
            CalculateBlockFinalityResult:
                ok: The result with block finality
                err: An errir
        """
        result = CalculateBlockFinalityResult()

        try:
            blockchain_config: RelayerBlockchainConfigDTO = \
                get_blockchain_config(chain_id=chain_id)
            wait_block_validation = blockchain_config.wait_block_validation
            result.ok = block_step + wait_block_validation

        except BridgeRelayerConfigBlockchainDataMissing as e:
            result.err = (
                f"Invalid chain ID {[chain_id]}. Check "
                f"src.relayer.config.bridge_relayer_config.toml to identify "
                f"available chain IDs. "
                f"Error={e}"
            )

        return result

    async def validate_block_finality(
        self,
        chain_id: int,
        block_finality: int,
    ) -> None:
        """Validate the block finality

        Args:
            chain_id (int): The chain id
            block_finality (int): The block number target

        """
        self.rb_provider.set_chain_id(chain_id=chain_id)
        elapsed_time = 0

        while True:
            if elapsed_time >= self.allocated_time:
                raise BlockFinalityTimeExceededError(
                    "Block finality validation has exceeded the allocated"
                    "time for processing."
                )

            block_number = await self.rb_provider.get_block_number()

            if block_number >= block_finality:
                return block_number

            message = (
                f"wait for block finality {block_number}/{block_finality} "
                f"chain_id={chain_id} "
                f"allocated_time={self.allocated_time} (sec) "
                f"sleep={self.sleep} (sec)"
            )
            self.print_log("wait", message)
            await asyncio.sleep(self.sleep)
            elapsed_time += 1

    def manage_validate_block_finality(
        self,
        event_dto: EventDTO,
        saved_chain_id: int,
        saved_block_step: int,
    ) -> BlockFinalityResult:
        """Manage the block finality validation.

            1. define the chain id the block finality is process to
            2. define the current block number
            3. calculate the block number target
            4. validate the block finality

        Args:
            event_dto (EventDTO): The event dto
            saved_chain_id (int): The saved chain id from a previous event
            saved_block_step (int): The saved block step from a previous event

        Returns:
            BlockFinalityResult: The result
        """
        self.print_log("blockFinality", "Validating block finality ...")
        result = BlockFinalityResult()
        block_step: int = event_dto.data['blockStep']

        chain_id_result = self.define_chain_for_block_finality(
            event_dto=event_dto,
        )
        if chain_id_result.err:
            return chain_id_result

        current_block_step = self.define_block_step_for_block_finality(
            chain_id=chain_id_result.ok,
            current_block_step=block_step,
            saved_chain_id=saved_chain_id,
            saved_block_step=saved_block_step,
        )

        block_finality_result = self.calculate_block_finality(
            chain_id=chain_id_result.ok,
            block_step=current_block_step,
        )
        if block_finality_result.err:
            return block_finality_result

        try:
            block_number = asyncio.run(self.validate_block_finality(
                chain_id=chain_id_result.ok,
                block_finality=block_finality_result.ok,
            ))
            result.ok = ("Success", block_number)
        except BlockFinalityTimeExceededError as e:
            result.err = str(e)

        return result

    def execute_smart_contract_function(
        self,
        chain_id: int,
        func_name: str,
        params: Dict[str, Any],
    ):
        """Execute the smart contract function.

        Args:
            chain_id (int): The chain id
            func_name (str): The function name
            params (dict): Parameters
        """
        bridge_task_dto = BridgeTaskDTO(
            func_name=func_name,
            params=params
        )
        self.rb_provider.set_chain_id(chain_id=chain_id)
        app = ExecuteContractTask(
            relayer_blockchain_provider=self.rb_provider,
            verbose=self.verbose
        )
        app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)

    def _convert_data_from_bytes(self, event: bytes) -> EventDTO:
        """Convert attribut data from bytes.

        Args:
            event (bytes): The event

        Returns:
            EventDTO: The event DTO
        """
        try:
            return EventDTO(**from_bytes(event))
        except TypeError as e:
            raise EventConverterTypeError(
                f"Unable to create an EventDTO. Event={from_bytes(event)}. "
                f"Error={e}"
            )

    def _callback(self, event: bytes) -> None:
        """Handle the consumed events

        Event                           | finality  | condition
        --------------------------------+-----------+----------------------
        OperationCreated                |   Yes     |   FeesLockedConfirmed
        FeesLockedConfirmed             |   Yes     |   OperationCreated
        FeesLockedAndDepositConfirmed   |   No      |   NA
        FeesDeposited                   |   Yes     |   NA
        FeesDepositConfirmed            |   No      |   NA
        OperationFinalized              |   No      |   NA

        Args:
            event (bytes): The Event
        """
        try:
            event_dto: EventDTO = self._convert_data_from_bytes(event=event)
        except EventConverterTypeError as e:
            self.print_log("fail", f"Error={e}")
            return

        params: int = event_dto.data['params']
        chain_id_from: int = event_dto.data['params']['chainIdFrom']
        chain_id_to: int = event_dto.data['params']['chainIdTo']
        block_step: int = event_dto.data['blockStep']
        operation_hash: str = event_dto.data['operationHash']
        event_name: str = event_dto.name

        self.print_log("receiveEvent", f"Received event={event_dto.as_dict()}")

        if event_name in ['OperationCreated', 'FeesLockedConfirmed']:
            # Store event data
            if self.store_operation_hash(
                operation_hash=operation_hash,
                chain_id=chain_id_from,
                block_step=block_step,
            ):
                return

            # Validate block finality
            saved_data = self.operation_hash_events[operation_hash]
            saved_chain_id = saved_data['chain_id']
            saved_block_step = saved_data['block_step']

            result = self.manage_validate_block_finality(
                event_dto=event_dto,
                saved_chain_id=saved_chain_id,
                saved_block_step=saved_block_step,
            )
            if result.err:
                return result

            self.execute_smart_contract_function(
                chain_id=chain_id_from,
                func_name="confirmFeesLockedAndDepositConfirmed",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    "blockStep": block_step,
                }
            )

            del self.operation_hash_events[operation_hash]

        elif event_name == "FeesLockedAndDepositConfirmed":
            self.execute_smart_contract_function(
                chain_id=chain_id_to,
                func_name="completeOperation",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    "blockStep": block_step,
                }
            )

        elif event_name == "FeesDeposited":
            result = self.manage_validate_block_finality(
                event_dto=event_dto,
                saved_chain_id=chain_id_to,
                saved_block_step=block_step,
            )
            if result.err:
                return result

            # Execute task
            self.execute_smart_contract_function(
                chain_id=chain_id_to,
                func_name="sendFeesLockConfirmation",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    "blockStep": block_step,
                }
            )

        elif event_name == "FeesDepositConfirmed":
            self.execute_smart_contract_function(
                chain_id=chain_id_from,
                func_name="receiveFeesLockConfirmation",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    # "blockStep": block_step,
                    # "operator": event_dto.data.params.operator,
                    "operator": "0x0000000000000000000000000000000000000000",
                }
            )

        elif event_name == "OperationFinalized":
            self.execute_smart_contract_function(
                chain_id=chain_id_from,
                func_name="receivedFinalizedOperation",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    "blockStep": block_step,
                }
            )

        else:
            self.print_log("alert", f"Ignore event={event_dto.as_dict()}")
