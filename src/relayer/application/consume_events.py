"""Bridge relayer event manager application."""
import asyncio
from datetime import datetime, timezone
from enum import Enum
import functools
from typing import Callable, List, Optional, Tuple

from src.relayer.application.repository import Repository
from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.application.execute_contracts import ExecuteContracts
from src.relayer.config.config import Config
from src.relayer.domain.config import (
    EventRuleConfig,
    RelayerBlockchainConfigDTO,
)
from src.relayer.domain.event_db import (
    BridgeTaskActionDTO,
    BridgeTaskDTO,
    EventDTO,
)
from src.relayer.domain.exception import (
    RelayerBlockFinalityTimeExceededError,
    RelayerBridgeTaskInvalidStatus,
    RelayerConfigBlockchainDataMissing,
    RelayerConfigEventRuleKeyError,
    RelayerRegisterEventFailed,
    RepositoryErrorOnGet,
    RepositoryErrorOnSave,
    EventConverterTypeError,
    RelayerBlockValidationFailed,
    RelayerBlockValidityError,
    RelayerBlockchainFailedExecuteSmartContract,
    RelayerCalculateBLockFinalityError
)
from src.relayer.interface.relayer_repository import IRelayerRepository
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain
from src.relayer.interface.relayer_register import IRelayerRegister
from src.utils.converter import from_bytes, to_bytes


class EventStatus(Enum):
    """Event status."""

    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


def async_repository_setup(method: Callable) -> Callable:
    """
    Decorate a method to ensure asynchronous setup is performed before \
        execution.

    This decorator wraps a method to ensure that an asynchronous setup
    method is called prior to the execution of the original method.
    This is useful for initializing resources or configurations required
    by the repository.

    Args:
        method (Callable): The asynchronous method to be wrapped.

    Returns:
        Callable: A wrapper function that executes the setup and then
        calls the original method.

    Raises:
        Any exceptions raised by the setup or the wrapped method will
        propagate as-is.

    Example:
        @async_repository_setup
        async def fetch_data(self, query):
            # Your method implementation
    """
    @functools.wraps(method)
    async def wrapper(self, *args, **kwargs):
        await self._async_setup()
        return await method(self, *args, **kwargs)
    return wrapper


class ConsumeEvents(RelayerLogging, BaseApp):
    """Consume events application."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        relayer_repository_provider: IRelayerRepository,
        sleep: int = 1,
        allocated_time: int = 1200,
        log_level: str = "INFO",
    ) -> None:
        """Init the relayer consumer.

        Args:
            relayer_blockchain_provider (IRelayerBlockchain:
                The blockchain provider
            relayer_register_provider (IRelayerRegister): The consumer provider
            relayer_repository_provider (IRelayerRepository): The relayer
                repository
            sleep (int, optional): Sleep in second. Defaults to 1.
            allocated_time (int, optional): Time in second allocated \
                to wait for block finality
            log_level (str, optional): Log level. Defaults to "INFO".
        """
        super().__init__(level=log_level)
        self.log_level = log_level
        self.operation_hash_events = {}
        self.sleep = sleep
        self.allocated_time = allocated_time
        self.providers = {}

        # providers
        self.blockchain_provider: IRelayerBlockchain = \
            relayer_blockchain_provider
        self.register_provider: IRelayerRegister = relayer_register_provider()

        # configurations (singleton)
        self.config = Config()

        # Applications
        self.repository = Repository(relayer_repository_provider())

    @async_repository_setup
    async def __call__(self) -> None:
        """Consumer worker."""
        self.print_log('main', "Waiting for events. To exit press CTRL+C")
        await self.register_provider.read_events(callback=self.callback)

    @async_repository_setup
    async def get_incomplete_bridge_tasks(self) -> List[BridgeTaskDTO]:
        """Get incomplete bridge tasks.

        Returns:
            List[str]: The list of incomplete event tasks
        """
        try:
            bridge_tasks: List[BridgeTaskDTO] = \
                await self.repository.get_bridge_tasks()
        except RepositoryErrorOnGet as e:
            self.logger.info(f"{self.Emoji.info.value}{e}")
            bridge_tasks = []

        incomplete_bridge_tasks = []
        for bridge_task in bridge_tasks:
            if bridge_task.status != EventStatus.FAILED.value:
                continue

            incomplete_bridge_tasks.append(bridge_task)

        return incomplete_bridge_tasks

    @async_repository_setup
    async def resume_incomplete_bridge_tasks(self, chain_id: int) -> None:
        """Resume incomplete bridge tasks.

        Args:
            chain_id (int): The chain id
        """
        bridge_tasks = await self.get_incomplete_bridge_tasks()

        for bridge_task in bridge_tasks:
            if bridge_task.chain_id != chain_id:
                continue

            try:
                event: EventDTO = await self.repository.get_event(
                    id=bridge_task.as_id()
                )

                msg = (
                    f"chain_id={chain_id} event_key={bridge_task} "
                    f"Resume register_event={bridge_task}"
                )
                self.logger.info(f"{self.Emoji.info.value}{msg}")
                self.print_log("info", f"{msg}")

                await self.register_provider.register_event(
                    event=to_bytes(event)
                )
            except (
                RepositoryErrorOnGet,
                RelayerRegisterEventFailed
             ) as e:
                self.logger.warning(
                    f"{self.Emoji.alert.value}"
                    f"chain_id={chain_id} "
                    f"event_key={bridge_task.as_key()} {e}"
                )
                continue

    @async_repository_setup
    async def resume_bridge_task(
        self,
        chain_id: int,
        block_number: int,
        tx_hash: str,
        log_index: int,
    ) -> None:
        """Resume bridge task.

        Args:
            chain_id (int): The chain id
            block_number (int): The block number
            tx_hash (str): The tx hash
            log_index (int): The log index
        """
        id = f"{block_number}-{tx_hash}-{log_index}"

        try:
            event: EventDTO = await self.repository.get_event(id=id)
        except RepositoryErrorOnGet as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}"
                f"chain_id={chain_id} "
                f"event_key={id} {e}"
            )
            return

        try:
            msg = (
                f"chain_id={chain_id} event_key={event.as_key()}"
                f"Resume register_event"
            )
            self.logger.info(f"{self.Emoji.info.value}{msg}")
            self.print_log("info", f"{msg}")

            await self.register_provider.register_event(event=to_bytes(event))

            try:
                event.handled = "registered"
                await self.repository.save_event(event=event)

            except RepositoryErrorOnSave as e:
                msg = (
                    f"chain_id={chain_id} "
                    f"unable to save event={event.as_key()} "
                    f"{e}"
                )
                self.logger.error(f"{self.Emoji.fail.value}{msg}")
                self.print_log("alert", msg)

        except RelayerRegisterEventFailed as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}"
                f"chain_id={chain_id} event_key={event.as_key()} {e}"
            )

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------
    async def _async_setup(self) -> None:
        """
        Set up the relayer consumer and initialize the repository.

        This asynchronous method prepares the relayer consumer by retrieving
        the necessary configuration details and setting up the repository
        with the specified repository name derived from the data path.

        The setup process involves:
        1. Getting the data path from the configuration.
        2. Retrieving the repository name.
        3. Constructing the full path for the repository.
        4. Calling the repository's setup method with the constructed
        repository name.

        """
        data_path = self.config.get_data_path()
        repo_name = self.config.get_repository_name()
        repository_name = data_path / f"tasks.{repo_name}"
        await self.repository.setup(repository_name=str(repository_name))

    def _chain_connector(self, chain_id: int) -> IRelayerBlockchain:
        """Connect the chain provider.

        Args:
            chain_id (int): The chain id

        Returns:
            IRelayerBlockchain: The chain provider
        """
        if chain_id in self.providers:
            return self.providers[chain_id]

        self.providers[chain_id] = self.blockchain_provider()
        self.providers[chain_id].connect_client(chain_id=chain_id)

        return self.providers[chain_id]

    @async_repository_setup
    async def _save_event_operation(
        self,
        event: EventDTO,
        status: str,
    ) -> None:
        """Save event operation.

        Args:
            event (EventDTO): The event DTO
            status (str): The status.

        Raises:
            RepositoryErrorOnSave
            RelayerBridgeTaskInvalidStatus
        """
        id_msg = (
            f"chain_id={event.chain_id} "
            f"operation_hash={event.data.operation_hash_str} "
            f"event={event.event_name} "
        )

        if status not in EventStatus:
            msg = f"Invalid status {status}."
            self.logger.error(f"{self.Emoji.fail.value}{id_msg}{msg}")
            raise RelayerBridgeTaskInvalidStatus(msg)

        try:
            bridge_task = BridgeTaskDTO(
                chain_id=event.chain_id,
                block_number=event.block_number,
                tx_hash=event.tx_hash,
                log_index=event.log_index,
                operation_hash=event.data.operation_hash_str,
                event_name=event.event_name,
                status=status,
                datetime=datetime.now(timezone.utc),
            )
            await self.repository.save_bridge_task(bridge_task)

        except RepositoryErrorOnSave as e:
            msg = f"Failed to save event operation. error={e}"
            self.logger.error(f"{self.Emoji.fail.value}{id_msg}{msg}")
            raise RepositoryErrorOnSave(msg)

    def calculate_block_finality(
        self,
        event: EventDTO,
    ) -> Tuple[int, int]:
        """Calculate the block finality.

        Args:
            event (EventDTO): The event data

        Returns:
            Tuple[int, int]: The block finality and the block finality
                in second

        Raises:
            RelayerCalculateBLockFinalityError:
                Raise when calculate block finality failed.
        """
        try:
            cfg: RelayerBlockchainConfigDTO = \
                self.config.get_blockchain_config(event.chain_id)

            wait_block_validation = cfg.wait_block_validation
            second_per_block = cfg.block_validation_second_per_block
            block_finality_in_sec = wait_block_validation * second_per_block
            block_finality = event.data.block_step + wait_block_validation

            return block_finality, block_finality_in_sec

        except RelayerConfigBlockchainDataMissing as e:
            msg = (
                f"Invalid chain ID {event.chain_id}. Check "
                f"toml configuration file to identify the "
                f"available chain IDs. error={e}"
            )
            self.logger.error(
                f"{self.Emoji.fail.value}chain_id={event.chain_id} {msg}"
            )
            raise RelayerCalculateBLockFinalityError(msg)

    def get_current_block_number(self, chain_id: int) -> int:
        """Get the current block number.

        Args:
            chain_id (int): The chain id

        Returns:
            int: The current block number
        """
        return self._chain_connector(chain_id).get_current_block_number()

    def calculate_wait_block_validation(
        self,
        event: EventDTO,
        block_finality: int,
    ) -> int:
        """Calculate the wait block validation.

        Args:
            event (EventDTO): The event data
            block_finality (int): The block finality

        Raises:
            RelayerCalculateBLockFinalityError

        Returns:
            int: The wait block validation in second
        """
        try:
            cfg: RelayerBlockchainConfigDTO = \
                self.config.get_blockchain_config(event.chain_id)
            
            current_block_number = self.get_current_block_number(event.chain_id)
            block_diff = block_finality - current_block_number

            if block_diff == cfg.wait_block_validation:
                return cfg.wait_block_validation * \
                    cfg.block_validation_second_per_block - \
                        cfg.block_validation_second_per_block
            elif block_diff > 1:
                return cfg.block_validation_second_per_block
            else:
                return int(cfg.block_validation_second_per_block / 2) or 1

        except RelayerConfigBlockchainDataMissing as e:
            msg = (
                f"Invalid chain ID {event.chain_id}. Check "
                f"toml configuration file to identify the "
                f"available chain IDs. error={e}"
            )
            self.logger.error(
                f"{self.Emoji.fail.value}chain_id={event.chain_id} {msg}"
            )
            raise RelayerCalculateBLockFinalityError(msg)


    async def validate_block_finality(
        self,
        event: EventDTO,
        block_finality: int,
    ) -> None:
        """Validate the block finality.

        Args:
            event (EventDTO): The event data
            block_finality (int): The block number finality target

        Raises:
            RelayerBlockFinalityTimeExceededError:
                Raise when block finality validation has exceeded the allocated
                time for processing.
        """
        block_number = self.get_current_block_number(event.chain_id)

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
            if elapsed_time >= self.allocated_time:
                raise RelayerBlockFinalityTimeExceededError(
                    f"Block finality validation has exceeded the allocated"
                    f"time for processing. Elapsed_time {elapsed_time} sec"
                )

            if block_number <= block_finality:
                # override block_finality_in_sec
                block_finality_in_sec = self.calculate_wait_block_validation(
                    event=event, 
                    block_finality=block_finality
                )

                msg = (
                    f"Wait for block finality {block_number}/{block_finality} "
                    f"block_finality_in_sec={block_finality_in_sec}"
                )
                self.logger.info(f"{self.Emoji.wait.value}{id_msg}{msg}")

                await asyncio.sleep(block_finality_in_sec)
                elapsed_time += block_finality_in_sec | 1
                block_number = self.get_current_block_number(event.chain_id)
            else:
                msg = (
                    f"Block finality validated! block_number={block_number} "
                    f">= block_finality={block_finality}"
                )
                self.logger.info(f"{self.Emoji.success.value}{id_msg}{msg}")
                return block_number

    async def manage_validate_block_finality(self, event: EventDTO) -> int:
        """Manage validate block finality.

        Args:
            event (EventDTO): The event data

        Raises:
            RelayerBlockValidationFailed:

        Returns:
            int: The block number
        """
        try:
            (
                block_finality,
                block_finality_in_sec
            ) = self.calculate_block_finality(event=event)

            return await self.validate_block_finality(
                event=event,
                block_finality=block_finality,
            )

        except (
            RelayerCalculateBLockFinalityError,
            RelayerBlockFinalityTimeExceededError,
        ) as e:
            raise RelayerBlockValidationFailed(e)

    def depend_on_event(self, event_name: str) -> Optional[str]:
        """Get the rule name based on the event.

        Args:
            event_name (str): The event name

        Returns:
            Optional[str]: The event rule name. None if not found
        """
        try:
            cfg: EventRuleConfig = self.config.get_relayer_event_rule(
                event_name=event_name,
            )

            if cfg.depends_on is not None:
                return cfg.depends_on
        except Exception as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}"
                f"Unable to get event rule for event={event_name}. {e}"
            )

        return None

    async def get_bridge_task_status(
        self,
        operation_hash: str,
        event_name: str,
    ) -> Optional[str]:
        """Get the bridge task status.

        Args:
            operation_hash (str): The operation hash
            event_name (str): The event name

        Returns:
            Optional[str]: The bridge task status.
        """
        id = f"{operation_hash}-{event_name}"
        try:
            bridge_task = await self.repository.get_bridge_task(id=id)
            return bridge_task.status
        except RepositoryErrorOnGet:
            return None

    def execute_smart_contract_function_for_event(
        self,
        chain_id: int,
        event: EventDTO,
        func_name: str,
    ):
        """Execute the smart contract function for the event.

        Args:
            chain_id (int): The chain id where the contract must be executed
            event (EventDTO): The event data
            func_name (str): The function name

        Raises:
            RelayerBlockchainFailedExecuteSmartContract: Raise if the smart
                contract function failed
        """
        bridge_task_action_dto = BridgeTaskActionDTO(
            operation_hash=event.data.operation_hash_str,
            func_name=func_name,
            params={
                "operationHash": event.data.operation_hash_bytes,
                "params": event.data.raw_params(),
                "blockStep": event.data.block_step,
            }
        )

        try:
            ExecuteContracts(
                relayer_blockchain_provider=self.blockchain_provider,
                log_level=self.log_level
            )(
                chain_id=chain_id,
                bridge_task_action_dto=bridge_task_action_dto
            )

        except RelayerBlockchainFailedExecuteSmartContract as e:
            self.logger.error(
                f"{self.Emoji.fail.value}chain_id={chain_id} "
                f"operation_hash={event.data.operation_hash_str} {e}"
            )
            raise

    async def callback(self, event: bytes):
        """
        Handle incoming events by managing them according to predefined rules.

        This asynchronous method is triggered when an event is received.
        It converts the event from bytes and processes it using the
        `manage_event_with_rules` method. If an error occurs during
        the event handling, it logs the error with a failure emoji.

        Args:
            event (bytes): The event data in bytes format that needs to be
                processed.

        Raises:
            RepositoryErrorOnSave
            EventConverterTypeError

        Example:
            await self.callback(event_data)
        """
        try:
            await self.manage_event_with_rules(event=from_bytes(event))
        except (
            RepositoryErrorOnSave,
            EventConverterTypeError,
        ) as e:
            self.logger.error(f"{self.Emoji.fail.value} {e}")

    async def manage_event_with_rules(self, event: EventDTO) -> None:
        """Manage event based on rules.

        Args:
            event (EventDTO): The event DTO

        Raises:
            RepositoryErrorOnSave
            EventConverterTypeError
        """
        try:
            id_msg = (
                f"chain_id={event.chain_id} "
                f"operation_hash={event.data.operation_hash_str} "
                f"event={event.event_name} "
            )

            self.print_log('info', f"received event {id_msg}")
            self.logger.info(f"{self.Emoji.info.value}{id_msg}Receive event.")

            cfg: EventRuleConfig = self.config.get_relayer_event_rule(
                event.event_name,
            )

            await self._save_event_operation(
                event=event,
                status=EventStatus.PROCESSING.value,
            )

            # ----------------------------------------------------------------
            # Validate block finality if needed
            if cfg.has_block_finality:
                try:
                    await self.manage_validate_block_finality(event=event)
                except RelayerBlockValidationFailed:
                    raise

            # ----------------------------------------------------------------
            # Depends on event
            if cfg.depends_on is not None:
                bridge_task_status: Optional[str] = \
                    await self.get_bridge_task_status(
                        operation_hash=event.data.operation_hash_str,
                        event_name=cfg.depends_on
                    )

                self.logger.info(
                    f"{self.Emoji.yellow.value}{id_msg}"
                    f"depends_on={cfg.depends_on} "
                    f"status={bridge_task_status}"
                )

                if bridge_task_status == EventStatus.FAILED.value:
                    raise RelayerBlockValidityError(
                        f"{id_msg}event {cfg.depends_on} has failed!"
                    )
                elif bridge_task_status != EventStatus.SUCCESS.value:
                    await self._save_event_operation(
                        event=event,
                        status=EventStatus.SUCCESS.value,
                    )
                    return

            # ----------------------------------------------------------------
            # Execute a smart contract function if needed
            if cfg.func_name is not None and cfg.chain_func_name is not None:
                self.execute_smart_contract_function_for_event(
                    chain_id=event.data.raw_params()[cfg.chain_func_name],
                    event=event,
                    func_name=cfg.func_name,
                )

            await self._save_event_operation(
                event=event,
                status=EventStatus.SUCCESS.value,
            )

        except RelayerConfigEventRuleKeyError as e:
            self.logger.warning(
                f"{self.Emoji.alert.value}Unknown event={event.event_name}."
                f" {e}"
            )

        except (
            RepositoryErrorOnSave,
            RelayerBridgeTaskInvalidStatus
        ):
            raise

        except (
            RelayerBlockchainFailedExecuteSmartContract,
            RelayerBlockValidityError,
        ) as e:
            await self._save_event_operation(
                event=event,
                status=EventStatus.FAILED.value,
            )
            self.logger.error(
                f"{self.Emoji.fail.value}{id_msg}"
                f"Failed to manage event. "
                f"{e}"
            )
