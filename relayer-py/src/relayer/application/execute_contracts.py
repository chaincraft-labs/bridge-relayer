"""Execute smart contract function."""
from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.domain.exception import (
    RelayerBlockchainFailedExecuteSmartContract
)
from src.relayer.domain.event_db import BridgeTaskActionDTO, BridgeTaskTxResult
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain


class ExecuteContracts(RelayerLogging, BaseApp):
    """Execute smart contract function."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        log_level: str = 'info',

    ) -> None:
        """Init the execute contract task.

        Args:
            relayer_blockchain_provider (IRelayerBlockchain): The blockchain \
                provider
            log_level (str, optional): Log level. Defaults to 'info'.
        """
        super().__init__(level=log_level)
        self.log_level = log_level
        self.providers = {}
        self.blockchain_provider: IRelayerBlockchain = \
            relayer_blockchain_provider

    def __call__(
        self,
        chain_id: int,
        bridge_task_action_dto: BridgeTaskActionDTO
    ) -> None:
        """Execute the smart contract function.

        Args:
            chain_id (int): The chain id
            bridge_task_action_dto (BridgeTaskActionDTO): The bridge task DTO
        """
        self.call_contract_func(
            chain_id=chain_id,
            bridge_task_action_dto=bridge_task_action_dto,
        )

    def chain_connector(self, chain_id: int) -> IRelayerBlockchain:
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

    def call_contract_func(
        self,
        chain_id: int,
        bridge_task_action_dto: BridgeTaskActionDTO,
    ) -> BridgeTaskTxResult:
        """Call the smart contract's function.

        Args:
            chain_id (int): The chain id
            bridge_task_action_dto (BridgeTaskDTO): The bridge task DTO

        Returns:
            BridgeTaskTxResult: The transaction result

        Raises:
            RelayerBlockchainFailedExecuteSmartContract: Raise error if
                failed to execute smart contract
        """
        id_msg = (
            f"chain_id={chain_id} "
            f"operation_hash={bridge_task_action_dto.operation_hash} "
            f"func_name={bridge_task_action_dto.func_name} "
            f"params={bridge_task_action_dto.params} "
        )
        self.logger.info(
            f"{self.Emoji.sendTx.value}{id_msg}"
            f"Execute smart contract's function."
        )

        try:
            tx: BridgeTaskTxResult = self.chain_connector(chain_id) \
                .call_contract_func(bridge_task_action_dto)

            self.logger.info(
                f"{self.Emoji.success.value}{id_msg}"
                f"Transaction success "
                f"Transaction_hash={tx.tx_hash}"
            )
            return tx
        except RelayerBlockchainFailedExecuteSmartContract as e:
            self.logger.error(
                f"{self.Emoji.fail.value}{id_msg}"
                f"Transaction failed! "
                f"{e}"
            )
            raise
