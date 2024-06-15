"""Application for the bridge relayer."""
import asyncio
import time
from typing import Any, Dict

from src.relayer.domain.config import (
    RelayerRegisterConfigDTO,
    RelayerBlockchainConfigDTO,
)
from src.utils.converter import (
    to_bytes,
    from_bytes,
)

from src.relayer.interface.relayer import (
    IRelayerBlockchain,
    IRelayerRegister,
)
from src.relayer.domain.relayer import BridgeTaskResult, BridgeTaskTxResult
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    EventDTO,
)
from src.relayer.config import (
    get_blockchain_config,
    get_register_config,
)

class App:
    """Blockchain Bridge Relayer application."""
    
    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        verbose: bool = True,        
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
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.verbose: bool = verbose        
        
    def __call__(self, chain_id: int) -> None:
        """Listen event main function.

        Args:
            chain_id (int): The blockchain id
        """
        # The blockchain event listener
        app = ManageEventFromBlockchain(
            relayer_blockchain_provider=self.rb_provider,
            relayer_register_provider=self.rr_provider,
            chain_id=chain_id,
            verbose=self.verbose,
        )
        
        # Start the listener
        app()


class ManageEventFromBlockchain:
    """Manage blockchain event listener."""
    
    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        chain_id: int,
        verbose: bool = True
    ) -> None:
        """Init blockchain event listener instance.

        Args:
            relayer_blockchain_event (IRelayerBlockchainEvent): 
                The relayer blockchain provider
            relayer_blockchain_config (RelayerBlockchainConfigDTO): 
                The relayer blockchain configuration
            verbose (bool, optional): Verbose mode. Defaults to True.
        """
        self.register_config: RelayerRegisterConfigDTO = get_register_config()
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.chain_id: int = chain_id
        self.verbose: bool = verbose
    
    def __call__(self) -> None:
        """Listen event main function."""
        self.listen_events()
    
    # Listen events
    def listen_events(self, poll_interval: int = 2) -> None:
        """The blockchain event listener.

        Args:
            poll_interval int: The loop poll interval in second. Default is 2
        """
        self.rb_provider.set_chain_id(self.chain_id)
        config: RelayerBlockchainConfigDTO = \
            get_blockchain_config(self.chain_id)
        
        if self.verbose:
            print("[ 💠 ] Running the event listener ...")
            print(f"[ ❕ ] chain_id : {self.chain_id}")
            print(f"[ ❕ ] address  : {config.smart_contract_address}")
        
        self.rb_provider.listen_events(
            callback=self._handle_event,
            poll_interval=poll_interval,
        )
    
    def _handle_event(self, event_dto: EventDTO) -> None:
        """Handle the event received from blockchain.

        Args:
            event_dto (EventDTO): The event DTO
        """        
        # Ready to be register
        event_dto_to_byte: bytes = self._convert_data_to_bytes(event_dto)
        return self._register_event(event=event_dto_to_byte)
        
    def _convert_data_to_bytes(self, event: EventDTO) -> bytes:
        """Convert attribut data to bytes.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bytes: The event DTO as bytes format
        """
        return to_bytes(event)
        
    
    def _register_event(self, event: bytes) -> None:
        """Register an event in a queue.

        Args:
            event (EventDTO): The eventDTO instance
        """
        app = RegisterEvent(relayer_register_provider=self.rr_provider)
        app(event=event)
        

class RegisterEvent:
    """Bridge relayer register event."""
    
    def __init__(
        self,
        relayer_register_provider: IRelayerRegister,
        verbose: bool = True,
    ) -> None:
        """Init the relayer register.

        Args:
            relayer_register_provider (IRelayerRegister): The register provider
        """
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.verbose: bool = verbose
    
    def __call__(self, event: bytes) -> None:
        """Register an event.

        Args:
            event (EventDTO): An eventDTO instance
        """
        if self.verbose:
            print(f"[ 💠 ] Registering event : {event}")
        self.rr_provider.register_event(event=event)
            

class ConsumeEventTask:
    """Bridge relayer consumer event task."""
    
    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_consumer_provider: IRelayerRegister,
        verbose: bool = True,
    ) -> None:
        """Init the relayer consumer.

        Args:
            relayer_consumer_provider (IRelayerRegister): The consumer provider
        """
        self.rr_provider: IRelayerRegister = relayer_consumer_provider
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.verbose: bool = verbose
        self.confirm_fees_locked_deposit_event = {}
    
    def __call__(self) -> None:
        """Consumer worker."""
        if self.verbose:
            print('[ 💠 ] Waiting for events. To exit press CTRL+C')
            
        self.rr_provider.read_events(callback=self._callback)

    def _callback(self, event: bytes) -> None:
        """"""
        if self.verbose:
            print(f"[ 📩 ] Received event : {event}")
        
        # print(f"\n {event}\n")
        event_dto: EventDTO = self._convert_data_from_bytes(event=event)
        chain_id_from: int = event_dto.data.params.chainIdFrom
        chain_id_to: int = event_dto.data.params.chainIdTo
        block_step: int = event_dto.data.blockStep

        # print("\n")
        # print(f"chain_id_from : {chain_id_from}")
        # print(f"chain_id_to : {chain_id_to}")
        # print(f"block_step : {block_step}")
        # print("\n")
              

        # Proxy rule to execute smart contract's function
        if event_dto.name == "OperationCreated" or event_dto.name == "FeesLockedConfirmed":
            print(f"[ 🟡 ] Handle event : {event_dto.name}\n")
            func_name = "confirmFeesLockedAndDepositConfirmed"
            chain_id = chain_id_from
            
            self.rb_provider.set_chain_id(chain_id=chain_id)
            app = ExecuteContractTask(
                relayer_blockchain_provider=self.rb_provider)
            
            params = {
                "operationHash": event_dto.data.operationHash,
                "params": event_dto.data.params,
                "blockStep": event_dto.data.blockStep,
            }
                        
            bridge_task_dto = BridgeTaskDTO(
                func_name=func_name,
                params=params
            )
            
            # Check event order 
            id = event_dto.data.operationHash
            if self.confirm_fees_locked_deposit_event.get(id) is None:
                self.confirm_fees_locked_deposit_event[id] = True
                return
            
            # cleanup mapping 
            del self.confirm_fees_locked_deposit_event[id]
                        
            # Block validation
            blockchain_config: RelayerBlockchainConfigDTO = \
                get_blockchain_config(chain_id=chain_id)
            wait_block_validation = blockchain_config.wait_block_validation
            block_validated = block_step + wait_block_validation
            
            while  asyncio.run(
                self.rb_provider.get_block_number()) < block_validated:
                
                latest_block: int = asyncio.run(
                    self.rb_provider.get_block_number())
                
                print(
                    f"[ ⏳ ] wait for block validation "
                    f"{latest_block} -> {block_validated}"
                )
                
                if latest_block >= block_validated:
                    break
                time.sleep(1)
            
            # Execute task
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
        elif event_dto.name == "FeesLockedAndDepositConfirmed":
            print(f"[ 🟡 ] Handle event : {event_dto.name}\n")
            func_name = "completeOperation"
            chain_id = chain_id_to
            
            self.rb_provider.set_chain_id(chain_id=chain_id)
            app = ExecuteContractTask(
                relayer_blockchain_provider=self.rb_provider)
            
            params: Dict[str, Any] = {
                "_operationHash": event_dto.data.operationHash,
                "params": event_dto.data.params,
                "blockStep": event_dto.data.blockStep,
            }
                        
            bridge_task_dto = BridgeTaskDTO(
                func_name=func_name,
                params=params
            )
            
            # Execute task
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
        elif event_dto.name == "FeesDeposited":
            print(f"[ 🟡 ] Handle event : {event_dto.name}\n")
            func_name = "sendFeesLockConfirmation"
            chain_id = chain_id_to
            
            self.rb_provider.set_chain_id(chain_id=chain_id)

            app = ExecuteContractTask(
                relayer_blockchain_provider=self.rb_provider)
            
            params: Dict[str, Any] = {
                "operationHash": event_dto.data.operationHash,
                "params": event_dto.data.params,
                "blockStep": event_dto.data.blockStep,
            }

            bridge_task_dto = BridgeTaskDTO(
                func_name=func_name,
                params=params
            )
            
            # Block validation
            blockchain_config = get_blockchain_config(chain_id=chain_id)
            wait_block_validation: int = blockchain_config.wait_block_validation
            block_validated: int = block_step + wait_block_validation
            
            while  asyncio.run(
                self.rb_provider.get_block_number()) < block_validated:
                
                latest_block = asyncio.run(self.rb_provider.get_block_number())
                print(
                    f"[ ⏳ ] wait for block validation "
                    f"{latest_block} -> {block_validated}"
                )
                
                if latest_block >= block_validated:
                    break
                time.sleep(1)
            
            # Execute task
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
        elif event_dto.name == "FeesDepositConfirmed":
            print(f"[ 🟡 ] Handle event : {event_dto.name}\n")
            func_name = "receiveFeesLockConfirmation"
            chain_id = chain_id_from
            
            self.rb_provider.set_chain_id(chain_id=chain_id)

            app = ExecuteContractTask(
                relayer_blockchain_provider=self.rb_provider)
                      
            params: Dict[str, Any] = {
                "operationHash": event_dto.data.operationHash,
                "params": event_dto.data.params,
                # "operator": event_dto.data.params.operator,
                "operator": "0x0000000000000000000000000000000000000000",
            }
                        
            bridge_task_dto = BridgeTaskDTO(
                func_name=func_name,
                params=params
            )
            
            # Execute task
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
            
        elif event_dto.name == "OperationFinalized":
            print(f"[ 🟡 ] Handle event : {event_dto.name}\n")
            func_name = "receivedFinalizedOperation"
            chain_id = chain_id_from
            
            self.rb_provider.set_chain_id(chain_id=chain_id)

            app = ExecuteContractTask(
                relayer_blockchain_provider=self.rb_provider)
            
            params: Dict[str, Any] = {
                "operationHash": event_dto.data.operationHash,
                "params": event_dto.data.params,
                "blockStep": event_dto.data.blockStep,
            }
                        
            bridge_task_dto = BridgeTaskDTO(
                func_name=func_name,
                params=params
            )           
            
            # Execute task
            app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
        else:
            print(f"[ 🟤 ] Ignore event : {event_dto.name}")

        if self.verbose:
            print(f"{50*'- '}")
        
    def _convert_data_from_bytes(self, event: bytes) -> EventDTO:
        """Convert attribut data from bytes.

        Args:
            event (bytes): The event

        Returns:
            EventDTO: The event DTO
        """
        return from_bytes(event)
                      
    
class ExecuteContractTask:
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
        print(
            f"[ 💠 ] Sending transaction to chain id {chain_id}, "
            f"function {bridge_task_dto.func_name} ..."
        )
        result: BridgeTaskResult = asyncio.run(
            self.rb_provider.call_contract_func(
                bridge_task_dto=bridge_task_dto
            )
        )
        
        if result.ok:
            bridge_task_tx_result: BridgeTaskTxResult = result.ok

            print(
                f"[ 💚 ] Transaction done with contract's function "
                f"'{bridge_task_dto.func_name}'. "
                f"Transaction hash : {bridge_task_tx_result.tx_hash}"
            )
        else:
            print(
                f"[ 💔 ] Transaction failed '{bridge_task_dto.func_name}'. "
                f"{result.err}"
            )         
