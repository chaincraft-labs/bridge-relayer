"""Application for the bridge relayer."""
import asyncio
from typing import Any, Dict

from src.relayer.application import BaseApp
from src.relayer.application.execute_contract import ExecuteContractTask
from src.relayer.domain.exception import (
    BlockFinalityTimeExceededError,
    BridgeRelayerConfigBlockchainDataMissing,
    BridgeRelayerConfigEventRuleKeyError,
    EventConverterTypeError
)
from src.relayer.domain.config import (
    EventRuleConfig, 
    RelayerBlockchainConfigDTO
)
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
from src.relayer.config.config import (
    get_blockchain_config,
    get_relayer_event_rule,
)
from src.relayer.application.base_logging import RelayerLogging

class ConsumeEventTask(RelayerLogging, BaseApp):
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
        super().__init__()
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_consumer_provider
        self.verbose: bool = verbose
        self.operation_hash_events = {}
        self.sleep = sleep
        self.allocated_time = allocated_time

    def __call__(self) -> None:
        """Consumer worker."""
        # self.print_log("main", "Waiting for events. To exit press CTRL+C'")
        self.logger.info(f"{self.Emoji.main.value}Waiting for events. To exit press CTRL+C'")
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
            be finalized. It must be the slowest blockchain.

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
        block_step may be the one already saved or the one comming from event

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
            cfg: RelayerBlockchainConfigDTO = get_blockchain_config(
                chain_id=chain_id
            )
            wait_block_validation = cfg.wait_block_validation
            second_per_block = cfg.block_validation_second_per_block
            block_finality_in_sec = wait_block_validation * second_per_block
            block_finality = block_step + wait_block_validation

            result.ok = (
                block_finality,
                block_finality_in_sec,
            )

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
        block_finality_in_sec: int,
    ) -> None:
        """Validate the block finality

        Args:
            chain_id (int): The chain id
            block_finality (int): The block number finality target
            block_finality_in_sec (int): The block finality in second

        """
        self.rb_provider.set_chain_id(chain_id=chain_id)
        block_number = await self.rb_provider.get_block_number()
        self.logger.info(
            f"{self.Emoji.blockFinality.value}block_number={block_number} "
            f"block_finality={block_finality}"
        )
        
        elapsed_time = 0
        while True:
            if elapsed_time == 0 and block_number <= block_finality:
                message = (
                    f"Wait for block finality {block_number}/{block_finality} "
                    f"chain_id={chain_id} block_finality_in_sec={block_finality_in_sec}"
                )
                self.logger.info(f"{self.Emoji.wait.value}{message}")
                await asyncio.sleep(block_finality_in_sec)
                elapsed_time = block_finality_in_sec
            else:
                elapsed_time = block_finality_in_sec

            if elapsed_time >= self.allocated_time:
                raise BlockFinalityTimeExceededError(
                    "Block finality validation has exceeded the allocated"
                    "time for processing."
                )

            block_number = await self.rb_provider.get_block_number()

            if block_number >= block_finality:
                message = (
                    f"Block finality validated! block_number={block_number} "
                    f">= block_finality={block_finality} chain_id={chain_id}"
                )
                self.logger.info(f"{self.Emoji.success.value}{message}")
                return block_number
            
            await asyncio.sleep(self.sleep)
            elapsed_time += 1

    def manage_validate_block_finality(
        self,
        chain_id: int,
        block_step: int,
    ) -> BlockFinalityResult:
        """Manage the block finality validation.

        Args:
            chain_id (int): The chain id 
            block_step (int): The block step

        Returns:
            BlockFinalityResult: The result
        """
        # self.print_log("blockFinality", "Validating block finality ...")
        # self.logger.info(f"{self.Emoji.blockFinality.value}Validating block finality ...")
        
        result = BlockFinalityResult()

        block_finality_result = self.calculate_block_finality(
            chain_id=chain_id,
            block_step=block_step,
        )

        if block_finality_result.err:
            return block_finality_result

        (
            block_finality,
            block_finality_in_sec
        ) = block_finality_result.ok

        try:
            block_number = asyncio.run(self.validate_block_finality(
                chain_id=chain_id,
                block_finality=block_finality,
                block_finality_in_sec=block_finality_in_sec
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
        bridge_task_dto = BridgeTaskDTO(func_name=func_name, params=params)
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

    def manage_event_with_rules_v2(self, event: EventDTO) -> None:
        """Manage event based on rules

        Args:
            event (EventDTO): The event DTO

        Returns:
            _type_: _description_
        """
        try:
            cfg: EventRuleConfig = get_relayer_event_rule(event.name)

            # Validate block finality
            if cfg.has_block_finality:
                result: BlockFinalityResult = self.manage_validate_block_finality(
                    chain_id=event.data['params'][cfg.origin],
                    block_step=event.data['blockStep'],
                )
                if result.err:
                    return result

            # Execute a smart contract function
            if cfg.func_name is not None and cfg.chain_func_name is not None:
                self.execute_smart_contract_function(
                    chain_id=event.data['params'][cfg.chain_func_name],
                    func_name=cfg.func_name,
                    params={
                        "operationHash": event.data['operationHash'],
                        "params": event.data['params'],
                        "blockStep": event.data['blockStep'],
                    }
                )

        except BridgeRelayerConfigEventRuleKeyError as e:
            self.logger.error(f"{self.Emoji.fail.value}Unknown event {event.name}, Error={e}")
            return

    def manage_event_with_rules_v1(self, event: EventDTO) -> None:
        """Manage event based on rules

        Args:
            event (EventDTO): The event DTO

        Returns:
            _type_: _description_
        """
        params: int = event.data['params']
        chain_id_from: int = event.data['params']['chainIdFrom']
        chain_id_to: int = event.data['params']['chainIdTo']
        block_step: int = event.data['blockStep']
        operation_hash: str = event.data['operationHash']
        event_name: str = event.name

        self.logger.info(f"{self.Emoji.receiveEvent.value}Consume event={event.as_dict()}")

        if event_name == 'OperationCreated':
            result: BlockFinalityResult = self.manage_validate_block_finality(
                chain_id=event.data['params']['chainIdFrom'],
                block_step=event.data['blockStep'],
            )
            if result.err:
                return result


        elif event_name == 'FeesLockedConfirmed':
            # # Store event data
            # store_status = self.store_operation_hash(
            #     operation_hash=operation_hash,
            #     chain_id=chain_id_from,
            #     block_step=block_step,
            # )
            # if store_status:
            #     return

            # Validate block finality
            # saved_data = self.operation_hash_events[operation_hash]
            # saved_chain_id = saved_data['chain_id']
            # saved_block_step = saved_data['block_step']

            # result: BlockFinalityResult = self.manage_validate_block_finality(
            #     chain_id=saved_chain_id,
            #     block_step=saved_block_step,
            # )
            # if result.err:
            #     return result

            self.execute_smart_contract_function(
                chain_id=chain_id_from,
                func_name="confirmFeesLockedAndDepositConfirmed",
                params={
                    "operationHash": operation_hash,
                    "params": params,
                    "blockStep": block_step,
                }
            )

            # del self.operation_hash_events[operation_hash]

        elif event_name == "FeesLockedAndDepositConfirmed":
            self.execute_smart_contract_function(
                chain_id=chain_id_to,
                func_name="completeOperation",
                params={
                    "_operationHash": operation_hash, # bad param name _operationHash vs operationHash
                    "params": params,
                    "blockStep": block_step,
                }
            )

        elif event_name == "FeesDeposited":
            result: BlockFinalityResult = self.manage_validate_block_finality(
                chain_id=event.data['params']['chainIdTo'],
                block_step=event.data['blockStep'],
            )
            if result.err:
                return result
            
            # result = self.manage_validate_block_finality(
            #     chain_id=chain_id_to,
            #     block_step=block_step,
            # )
            # if result.err:
            #     return result

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
                    # "operator": event.data.params.operator,
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
            self.logger.warning(
                f"{self.Emoji.alert.value}Ignore event={event.as_dict()}"
            )

    def _callback(self, event: bytes) -> None:
        """Handle the consumed events

        Event                           | finality  | condition
        --------------------------------+-----------+----------------------
        OperationCreated                |   Yes     | FeesLockedConfirmed
        FeesLockedConfirmed             |   Yes     | OperationCreated
        FeesLockedAndDepositConfirmed   |   No      | NA
        FeesDeposited                   |   Yes     | NA
        FeesDepositConfirmed            |   No      | NA
        OperationFinalized              |   No      | NA

        Args:
            event (bytes): The Event
        """
        try:
            event_dto: EventDTO = self._convert_data_from_bytes(event=event)
        except EventConverterTypeError as e:
            self.logger.error(f"{self.Emoji.fail.value}Error={e}")
            return

        # self.manage_event_with_rules_v2(event=event_dto)
        # Delete v1 after SM cleanup and enable v2
        return self.manage_event_with_rules_v1(event=event_dto)
