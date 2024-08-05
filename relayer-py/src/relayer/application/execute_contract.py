"""Application for the bridge relayer."""
import asyncio

from src.relayer.application import BaseApp
from src.relayer.interface.relayer import IRelayerBlockchain
from src.relayer.domain.relayer import (
    BridgeTaskResult,
    BridgeTaskDTO,
)


class ExecuteContractTask(BaseApp):
    """Blockchain Bridge Relayer contract executor."""
    
    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        verbose: bool = True
        
    ) -> None:
        """Init Blockchain Bridge Relayer instance.

        Args:
            relayer_blockchain_config (IRelayerBLockchainConfig): 
                The relayer blockchain provider
            relayer_blockchain_event (IRelayerBlockchainEvent): 
                The relayer blockchain configuration
            verbose (bool, optional): Verbose mode. Defaults to True.
        """
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.verbose: bool = verbose
        
    def __call__(
        self, 
        chain_id: int,
        bridge_task_dto: BridgeTaskDTO
    ) -> None:
        """Execute contract functions

        Args:
            chain_id (int): The blockchain id
            func (str): The contract function to execute
        """        
        self.rb_provider.set_chain_id(chain_id=chain_id)
        self.call_contract_func(
            chain_id=chain_id, 
            bridge_task_dto=bridge_task_dto,
        )

    def call_contract_func(
        self, 
        chain_id: int,
        bridge_task_dto: BridgeTaskDTO,
    ) -> None:
        """Call the smart contract's function.

        Args:
            chain_id (int): The chain id
            bridge_task_dto (BridgeTaskDTO): A BridgeTaskDTO instance
        """
        self.print_log("sendTx", (
            f"Sending transaction to chain_id={chain_id} "
            f"func_name={bridge_task_dto.func_name}"
        ))

        result: BridgeTaskResult = asyncio.run(
            self.rb_provider.call_contract_func(bridge_task_dto=bridge_task_dto)
        )
        
        if result.ok:
            self.print_log("success", (
                f"Transaction success func_name={bridge_task_dto.func_name} "
                f"Transaction_hash={result.ok.tx_hash}"
            ))
        else:
            self.print_log("fail", (
                f"Transaction failed func_name={bridge_task_dto.func_name}' "
                f"error={result.err}"
            ))
