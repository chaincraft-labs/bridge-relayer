"""Bridge relayer event manager application."""
import asyncio
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional, Tuple

from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.application.execute_contracts import ExecuteContracts
from src.relayer.config.config import (
    get_blockchain_config,
    get_relayer_event_rule,
)
from src.relayer.domain.config import (
    EventRuleConfig, 
    RelayerBlockchainConfigDTO
)
from src.relayer.domain.event import EventDataDTO
from src.relayer.domain.exception import (
    RelayerBlockFinalityTimeExceededError,
    RelayerConfigBlockchainDataMissing,
    RelayerConfigEventRuleKeyError,
    RelayerRegisterEventFailed,
    EventDataStoreSaveEventOperationError,
    EventConverterTypeError,
    RelayerBlockValidationFailed,
    RelayerBlockValidityError,
    RelayerBlockchainFailedExecuteSmartContract,
    RelayerCalculateBLockFinalityError
)
from src.relayer.domain.event import BridgeTaskDTO
from src.relayer.interface.event_storage import IEventDataStore
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain
from src.relayer.interface.relayer_register import IRelayerRegister
from src.utils.converter import from_bytes, to_bytes


class EventStatus(Enum):
    """Event status."""

    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class ConsumeEvents(RelayerLogging, BaseApp):
    """Consume events application."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_consumer_provider: IRelayerRegister,
        event_datastore_provider: IEventDataStore,
        sleep: int = 1,
        allocated_time: int = 1200,
        log_level: str = "INFO",
        auto_commit: bool = True,
    ) -> None:
        """Init the relayer consumer.

        Args:
            relayer_blockchain_provider (IRelayerBlockchain:
                The blockchain provider
            relayer_consumer_provider (IRelayerRegister): The consumer provider
            event_datastore_provider (IEventDataStore): The event datastore
            sleep (int, optional): Sleep in second. Defaults to 1.
            allocated_time (int, optional): Time in second allocated \
                to wait for block finality
            log_level (str, optional): Log level. Defaults to "INFO".
            auto_commit (bool, optional): Auto commit. Defaults to True.
        """
        super().__init__(level=log_level)
        self.log_level = log_level
        self.operation_hash_events = {}
        self.sleep = sleep
        self.allocated_time = allocated_time
        self.auto_commit = auto_commit
        self.providers = {}
        # providers
        # blockchain will be instantiated for each chain id
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_consumer_provider(log_level=self.log_level)
        self.evt_store: IEventDataStore = event_datastore_provider(log_level=self.log_level)
        # Event task
        self.evt_store.read_event_tasks()

    async def __call__(self) -> None:
        """Consumer worker."""
        self.print_log('main', "Waiting for events. To exit press CTRL+C")

        await self.rr_provider.read_events(callback=self.callback)

    def chain_connector(self, chain_id: int) -> IRelayerBlockchain:
        """Connect the chain provider.

        Args:
            chain_id (int): The chain id

        Returns:
            IRelayerBlockchain: The chain provider
        """
        if chain_id in self.providers:
            return self.providers[chain_id]
        
        self.providers[chain_id] = self.rb_provider(log_level=self.log_level)
        self.providers[chain_id].connect_client(chain_id=chain_id)

        return self.providers[chain_id]

    async def resume_incomplete_event_tasks(self, chain_id: int) -> None:
        """Resume incomplete event tasks.

        Args:
            chain_id (int): The chain id
        """
        # ----------------------------------------------------------------
        # Read incomplete event tasks
        event_keys = self.get_incomplete_event_tasks(chain_id)

        # ----------------------------------------------------------------
        # Read event data from state
        for event_key in event_keys:
            event_data_dto: EventDataDTO = self.evt_store.get_event(
                chain_id=chain_id,
                event_key=event_key
            )
            
            if not event_data_dto:
                continue

            msg = (
                f"chain_id={chain_id} event_key={event_key}"
                f"Resume register_event={event_key}"
            )
            self.logger.info(f"{self.Emoji.info.value}{msg}")
            self.print_log("info", f"{msg}")

            try:
                await self.rr_provider.register_event(event=to_bytes(event_data_dto))
            except RelayerRegisterEventFailed as e:
                self.logger.warning(
                    f"{self.Emoji.alert.value}"
                    f"chain_id={chain_id} event_key={event_key} {e}"
                )
                continue


    def get_incomplete_event_tasks(self, chain_id: int) -> List[str]:
        """Get incomplete event tasks

        Args:
            chain_id (int): The chain id

        Returns:
            List[str]: The list of incomplete event tasks
        """
        self.evt_store.set_chain_id(chain_id)
        self.evt_store.read_event_tasks()
        
        incomplete_event_tasks = {}
        for events in self.evt_store.state_task.values():
            for data in events.values():
                if data['status'] != EventStatus.FAILED.value:
                    continue
                
                if incomplete_event_tasks.get(data['chain_id']) is None:
                    incomplete_event_tasks[data['chain_id']] = []

                incomplete_event_tasks[data['chain_id']].append(
                    data['block_key'])

        return incomplete_event_tasks.get(chain_id, [])


    async def resume_event_task(self, chain_id: int, event_key: str) -> None:
        """Resume event task

        Args:
            chain_id (int): The chain id
            event_key (str): The event key
        """
        try:
            self.evt_store.set_chain_id(chain_id)

            event_data_dto: EventDataDTO = self.evt_store.get_event(
                chain_id=chain_id, 
                event_key=event_key
            )

            if not event_data_dto:
                return

            msg = (
                f"chain_id={chain_id} event_key={event_key}"
                f"Resume register_event={event_key}"
            )
            self.logger.info(f"{self.Emoji.info.value}{msg}")
            self.print_log("info", f"{msg}")
            await self.rr_provider.register_event(event=to_bytes(event_data_dto))
            self.evt_store.set_event_as_registered(event_key, self.auto_commit)

        except RelayerRegisterEventFailed as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}"
                f"chain_id={chain_id} event_key={event_key} {e}"
            )
            return

    def save_event_operation(
        self,
        event: EventDataDTO,
        status: str,
        auto_commit: bool = True,
    ) -> None:
        """Save event operation

        Args:
            event (EventDataDTO): The event DTO
            status (Optional[str], optional): The status. Defaults to None.
            auto_commit (bool, optional): Auto commit. Defaults to True.

        Raises:
            EventDataStoreSaveEventOperationError: 
        """
        self.evt_store.set_chain_id(chain_id=event.chain_id)

        if status not in EventStatus:
            id_msg = (
                f"chain_id{event.chain_id} "
                f"operation_hash={event.data.operation_hash_str} "
                f"event={event.event_name} "
            )
            msg = f"Invalid status {status}."
            self.logger.error(f"{self.Emoji.fail.value}{id_msg}{msg}")
            raise EventDataStoreSaveEventOperationError(msg)
        
        try:
            self.evt_store.save_event_task(
                chain_id=event.chain_id,
                block_key=event.as_key(),
                operation_hash=event.data.operation_hash_str,
                event_name=event.event_name,
                auto_commit=auto_commit,
                status=status,
            )

        except Exception as e:
            msg = f"Failed to save event operation. error={e}"
            self.logger.error(f"{self.Emoji.fail.value}{id_msg}{msg}")
            raise EventDataStoreSaveEventOperationError(msg)

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

    def calculate_block_finality(
        self,
        event: EventDataDTO,
    ) -> Tuple[int, int]:
        """Calculate the block finality.

        Args:
            event (EventDataDTO): The event data

        Returns:
            Tuple[int, int]: The block finality and the block finality in second

        Raises:
            RelayerCalculateBLockFinalityError: 
                Raise when calculate block finality failed.
        """
        try:
            cfg: RelayerBlockchainConfigDTO = get_blockchain_config(
                event.chain_id
            )
            wait_block_validation = cfg.wait_block_validation
            second_per_block = cfg.block_validation_second_per_block
            block_finality_in_sec = wait_block_validation * second_per_block
            block_finality = event.data.block_step + wait_block_validation

            return block_finality, block_finality_in_sec

        except RelayerConfigBlockchainDataMissing as e:
            msg = (
                f"Invalid chain ID {[event.chain_id]}. Check "
                f"src.relayer.config.bridge_relayer_config.toml to identify "
                f"available chain IDs. error={e}"
            )
            self.logger.error(
                f"{self.Emoji.fail.value}chain_id={event.chain_id} {msg}"
            )
            raise RelayerCalculateBLockFinalityError(msg)
            

    async def validate_block_finality(
        self,
        event: EventDataDTO,
        block_finality: int,
        block_finality_in_sec: int,
    ) -> None:
        """Validate the block finality

        Args:
            event (EventDataDTO): The event data
            block_finality (int): The block number finality target
            block_finality_in_sec (int): The block finality in second

        Raises:
            RelayerBlockFinalityTimeExceededError: 
                Raise when block finality validation has exceeded the allocated
                time for processing.
        """
        block_number = self.chain_connector(event.chain_id)\
            .get_current_block_number()
        id_msg = (
            f"chain_id={event.chain_id} "
            f"operation_hash={event.data.operation_hash_str} "
            f"event={event.event_name} "
        )
        self.logger.info(
            f"{self.Emoji.blockFinality.value}{id_msg}"
            f"block_number={block_number} "
            f"block_finality={block_finality}"
        )
        
        elapsed_time = 0
        while True:
            if elapsed_time == 0 and block_number <= block_finality:
                message = (
                    f"Wait for block finality {block_number}/{block_finality} "
                    f"block_finality_in_sec={block_finality_in_sec}"
                )
                self.logger.info(f"{self.Emoji.wait.value}{id_msg}{message}")
                await asyncio.sleep(block_finality_in_sec)
                elapsed_time = block_finality_in_sec
            else:
                elapsed_time = block_finality_in_sec

            if elapsed_time >= self.allocated_time:
                raise RelayerBlockFinalityTimeExceededError(
                    "Block finality validation has exceeded the allocated"
                    "time for processing."
                )

            block_number = self.chain_connector(event.chain_id).\
                get_current_block_number()

            if block_number >= block_finality:
                message = (
                    f"Block finality validated! block_number={block_number} "
                    f">= block_finality={block_finality}"
                )
                self.logger.info(f"{self.Emoji.success.value}{id_msg}{message}")
                return block_number
            
            # await asyncio.sleep(self.sleep)
            await asyncio.sleep(self.sleep)
            elapsed_time += 1

    async def manage_validate_block_finality(self, event: EventDataDTO) -> int:
        """Manage validate block finality

        Args:
            event (EventDataDTO): The event data

        Raises:
            RelayerBlockValidationFailed: 

        Returns:
            int: The block number
        """
        try:
            (
                block_finality,
                block_finality_in_sec
            ) =  self.calculate_block_finality(event)

            return await self.validate_block_finality(
                event=event,
                block_finality=block_finality,
                block_finality_in_sec=block_finality_in_sec
            )
        
        except (
            RelayerBlockFinalityTimeExceededError,
            RelayerConfigBlockchainDataMissing
        ) as e:
            raise RelayerBlockValidationFailed(e)

    def execute_smart_contract_function(
        self,
        chain_id: int,
        operation_hash: str,
        func_name: str,
        params: Dict[str, Any],
    ):
        """Execute the smart contract function.

        Args:
            chain_id (int): The chain id
            operation_hash (str): The operation hash
            func_name (str): The function name
            params (dict): Parameters

        Raises:
            RelayerBlockchainFailedExecuteSmartContract: Raise if the smart
                contract function failed
        """
        bridge_task_dto = BridgeTaskDTO(
            operation_hash=operation_hash,
            func_name=func_name, 
            params=params
        )

        app = ExecuteContracts(
            relayer_blockchain_provider=self.rb_provider,
            log_level=self.log_level
        )

        try:
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)

        except RelayerBlockchainFailedExecuteSmartContract as e:
            self.logger.error(
                f"{self.Emoji.fail.value}chain_id={chain_id} "
                f"operation_hash={operation_hash} {e}"
            )
            raise

    def depend_on_event(self, event_name: str) -> Optional[str]:
        """Get the rule name based on the event

        Args:
            event_name (str): The event name

        Returns:
            Optional[str]: The event rule name. None if not found
        """
        try:
            cfg: EventRuleConfig = get_relayer_event_rule(event_name=event_name)

            if cfg.depends_on is not None:
                return cfg.depends_on
        except Exception as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}"
                f"Unable to get event rule for event={event_name}. {e}"
            )

        return None

    async def manage_event_with_rules(self, event: EventDataDTO) -> None:
        """Manage event based on rules

        Args:
            event (EventDataDTO): The event DTO
        """
        try:
            cfg: EventRuleConfig = get_relayer_event_rule(event.event_name)
        except RelayerConfigEventRuleKeyError as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}Unknown event={event.event_name}. {e}"
            )
            return

        try:
            id_msg = (
                f"chain_id={event.chain_id} "
                f"operation_hash={event.data.operation_hash_str} "
                f"event={event.event_name} "
            )
            self.print_log('info', f"received event {id_msg}")
            self.logger.info(f"{self.Emoji.info.value}{id_msg}Receive event.")
            self.save_event_operation(
                event=event, 
                status=EventStatus.PROCESSING.value, 
                auto_commit=self.auto_commit
            )

            # ----------------------------------------------------------------
            # Validate block finality if needed
            if cfg.has_block_finality:
                try:
                    await self.manage_validate_block_finality(event)
                except RelayerBlockValidationFailed:
                    raise 

            # ----------------------------------------------------------------
            # Depends on event
            if cfg.depends_on is not None:
                depends_on_status =  self.evt_store.get_event_task_status(
                    operation_hash=event.data.operation_hash_str,
                    event_name=cfg.depends_on
                )

                self.logger.info(
                    f"{self.Emoji.yellow.value}{id_msg}"
                    f"depends_on={cfg.depends_on} "
                    f"status={depends_on_status}"
                )

                if depends_on_status == EventStatus.FAILED.value:
                    raise RelayerBlockValidityError(
                        f"{id_msg}event {cfg.depends_on} has failed!"
                    )
                elif depends_on_status != EventStatus.SUCCESS.value:
                    self.save_event_operation(
                        event=event,
                        status=EventStatus.SUCCESS.value,
                        auto_commit=self.auto_commit,
                    )
                    return

            # ----------------------------------------------------------------
            # Execute a smart contract function if needed
            if cfg.func_name is not None and cfg.chain_func_name is not None:
                self.execute_smart_contract_function(
                    chain_id=event.data.raw_params()[cfg.chain_func_name],
                    operation_hash=event.data.operation_hash_str,
                    func_name=cfg.func_name,
                    params={
                        "operationHash": event.data.operation_hash_bytes,
                        "params": event.data.raw_params(),
                        "blockStep": event.data.block_step,
                    }
                )
            self.save_event_operation(
                event=event,
                status=EventStatus.SUCCESS.value,
                auto_commit=self.auto_commit,
            )

        except (
            RelayerBlockchainFailedExecuteSmartContract,
            RelayerBlockValidityError,
        ) as e:
            self.save_event_operation(
                event=event,
                status=EventStatus.FAILED.value,
                auto_commit=self.auto_commit,
            )
            self.logger.error(
                f"{self.Emoji.fail.value}{id_msg}"
                f"Failed to manage event."
                f"{e}"
            )
            return

    async def callback(self, event: bytes):
        """The callback function used to manage the event received.

        Args:
            event (bytes): An event
        """
        try:
            return await self.manage_event_with_rules(from_bytes(event))
        
        except (
            EventDataStoreSaveEventOperationError,
            EventConverterTypeError,
        ) as e:
            self.logger.error(f"{self.Emoji.fail.value} {e}")
            return
