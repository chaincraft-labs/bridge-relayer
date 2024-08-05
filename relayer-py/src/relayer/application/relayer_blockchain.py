# """Application for the bridge relayer."""
# import asyncio
# from enum import Enum
# import sys
# import time
# from typing import Any, Dict, List

# from src.relayer.domain.exception import BlockFinalityTimeExceededError, BridgeRelayerConfigBlockchainDataMissing, BridgeRelayerRegisterEventFailed, EventConverterTypeError
# from src.relayer.domain.config import (
#     RelayerRegisterConfigDTO,
#     RelayerBlockchainConfigDTO,
# )
# from src.utils.converter import (
#     to_bytes,
#     from_bytes,
# )
# from src.relayer.interface.relayer import (
#     IRelayerBlockchain,
#     IRelayerRegister,
# )
# from src.relayer.domain.relayer import (
#     BlockFinalityResult,
#     BridgeTaskResult,
#     BridgeTaskTxResult,
#     CalculateBlockFinalityResult,
#     DefineChainBlockFinalityResult,
#     RegisterEventResult,
#     BridgeTaskDTO,
#     EventDTO,
# )
# from src.relayer.config import (
#     get_blockchain_config,
#     get_register_config,
# )


# class Emoji(Enum):
#     """"""
#     main = "💠"
#     receive = "📩"
#     fail = "💔"
#     info = "🟡"
#     alert = "🟤"
#     wait = "⏳"






# class App:
#     """Blockchain Bridge Relayer application."""

#     def __init__(
#         self,
#         relayer_blockchain_provider: IRelayerBlockchain,
#         relayer_register_provider: IRelayerRegister,
#         verbose: bool = True,
#     ) -> None:
#         """Init Blockchain Bridge Relayer instance.

#         Args:
#             relayer_blockchain_config (IRelayerBLockchainConfig):
#                 The relayer blockchain provider
#             relayer_blockchain_event (IRelayerBlockchainEvent):
#                 The relayer blockchain configuration
#             verbose (bool, optional): Verbose mode. Defaults to True.
#         """
#         self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
#         self.rr_provider: IRelayerRegister = relayer_register_provider
#         self.verbose: bool = verbose

#     def __call__(self, chain_id: int, event_filters: List[str]) -> None:
#         """Listen event main function.

#         Args:
#             chain_id (int): The blockchain id
#             event_filters (list): The events to listen
#         """
#         # The blockchain event listener
#         app = ManageEventFromBlockchain(
#             relayer_blockchain_provider=self.rb_provider,
#             relayer_register_provider=self.rr_provider,
#             chain_id=chain_id,
#             event_filters=event_filters,
#             verbose=self.verbose,
#         )

#         # Start the listener
#         app()


# class ManageEventFromBlockchain:
#     """Manage blockchain event listener."""

#     def __init__(
#         self,
#         relayer_blockchain_provider: IRelayerBlockchain,
#         relayer_register_provider: IRelayerRegister,
#         chain_id: int,
#         event_filters: List[str],
#         verbose: bool = True
#     ) -> None:
#         """Init blockchain event listener instance.

#         Args:
#             relayer_blockchain_event (IRelayerBlockchainEvent):
#                 The relayer blockchain provider
#             relayer_blockchain_config (RelayerBlockchainConfigDTO):
#                 The relayer blockchain configuration
#             chain_id (int): The chain id
#             event_filters (List): The list of event to manage
#             verbose (bool, optional): Verbose mode. Defaults to True.
#         """
#         self.register_config: RelayerRegisterConfigDTO = get_register_config()
#         self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
#         self.rr_provider: IRelayerRegister = relayer_register_provider
#         self.chain_id: int = chain_id
#         self.event_filters: List[str] = event_filters
#         self.verbose: bool = verbose

#     def __call__(self) -> None:
#         """Listen event main function."""
#         try:
#             self.listen_events()
#         except KeyboardInterrupt:
#             print("Keyboard Interrupt")
#             sys.exit()
#         except Exception as e:
#             print(f"error : {e}")
#             self()

#     def listen_events(self, poll_interval: int = 2) -> None:
#         """The blockchain event listener.

#         Args:
#             poll_interval int: The loop poll interval in second. Default is 2
#         """
#         self.rb_provider.set_chain_id(self.chain_id)
#         self.rb_provider.set_event_filter(self.event_filters)

#         config: RelayerBlockchainConfigDTO = get_blockchain_config(self.chain_id)

#         if self.verbose:
#             print("[ 💠 ] Running the event listener ...")
#             print(f"[ ❕ ] chain_id          : {self.chain_id}")
#             print(f"[ ❕ ] contract address  : {config.smart_contract_address}")
#             print(f"[ ❕ ] listen to events  : {self.event_filters}")

#         self.rb_provider.listen_events(
#             callback=self._handle_event,
#             poll_interval=poll_interval,
#         )

#     def _handle_event(self, event_dto: EventDTO) -> RegisterEventResult:
#         """Handle the event received from blockchain.

#         Args:
#             event_dto (EventDTO): The event DTO

#         Return:
#             RegisterEventResult: The event registered result
#         """
#         event_dto_to_byte: bytes = self._convert_data_to_bytes(event=event_dto)
#         app = RegisterEvent(
#             relayer_register_provider=self.rr_provider,
#             verbose=self.verbose
#         )
#         return app(event=event_dto_to_byte)
        
#     def _convert_data_to_bytes(self, event: EventDTO) -> bytes:
#         """Convert attribut data to bytes.

#         Args:
#             event (EventDTO): The event DTO

#         Returns:
#             bytes: The event DTO as bytes format
#         """
#         return to_bytes(data=event)


# class RegisterEvent:
#     """Bridge relayer register event."""
    
#     def __init__(
#         self,
#         relayer_register_provider: IRelayerRegister,
#         verbose: bool = True,
#     ) -> None:
#         """Init the relayer register.

#         Args:
#             relayer_register_provider (IRelayerRegister): The register provider
#         """
#         self.rr_provider: IRelayerRegister = relayer_register_provider
#         self.verbose: bool = verbose
    
#     def __call__(self, event: bytes) -> RegisterEventResult:
#         """Register an event.

#         Args:
#             event (EventDTO): An eventDTO instance

#         Return:
#             RegisterEventResult: The event registered result
#         """
#         result = RegisterEventResult()

#         if self.verbose:
#             print(f"[ 🟣 ] Registering event : {event}")

#         try:
#             self.rr_provider.register_event(event=event)
#             result.ok = True
#         except BridgeRelayerRegisterEventFailed as e:
#             result.err = str(e)
#         return result
            

# class ConsumeEventTask:
#     """Bridge relayer consumer event task."""
    
#     def __init__(
#         self,
#         relayer_blockchain_provider: IRelayerBlockchain,
#         relayer_consumer_provider: IRelayerRegister,
#         verbose: bool = True,
#     ) -> None:
#         """Init the relayer consumer.

#         Args:
#             relayer_consumer_provider (IRelayerRegister): The consumer provider
#         """
#         self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
#         self.rr_provider: IRelayerRegister = relayer_consumer_provider
#         self.verbose: bool = verbose
#         self.operation_hash_events = {}
    
#     def __call__(self) -> None:
#         """Consumer worker."""
#         self.print_log("main", " Waiting for events. To exit press CTRL+C'")            
#         self.rr_provider.read_events(callback=self._callback)

#     def print_log(self, status, message):
#         """Print a log."""
#         _status = {
#             "main": "💠",
#             "receive": "📩",
#             "fail": "💔",
#             "info": "🟡",
#             "alert": "🟤",
#             "wait": "⏳",
#         }

#         if self.verbose:
#             print(f"{_status[status]} {message}")

#     def store_operation_hash(
#         self,
#         operation_hash: str,
#         chain_id: int,
#         block_step: int,
#     ) -> bool:
#         """Store the operation hash and the current event name if missing.

#         Args:
#             operation_hash (str): The operation hash
#             chain_id (int): The chain id
#             block_step (int): The current block

#         Returns:
#             bool: The status of storing data
#         """
#         if self.operation_hash_events.get(operation_hash) is None:
#             self.operation_hash_events[operation_hash] = {
#                 'chain_id': chain_id,
#                 'block_step': block_step,
#             }

#             return True
#         return False    

#     def define_chain_for_block_finality(
#         self, 
#         event_dto: EventDTO
#     ) -> DefineChainBlockFinalityResult:
#         """Define the chain id to validate the block finality.

#             Read the `wait_block_validation` defined in 
#             src.relayer.config.bridge_relayer_config.toml
#             `wait_block_validation` means how long it takes for a block to \
#                 be finalized 

#             It must be the slowest blockchain.

#         Args:
#             event_dto (EventDTO): The chain id

#         Returns:
#             DefineChainBlockFinalityResult: 
#                 ok: The chain id defined to validate block finality
#                 err: An error
#         """
#         result = DefineChainBlockFinalityResult()

#         chain_a = event_dto.data['params']['chainIdFrom']
#         chain_b = event_dto.data['params']['chainIdTo']
        
#         try:
#             result.ok = chain_a
#             chain_a_config = get_blockchain_config(chain_id=chain_a)
#             chain_b_config = get_blockchain_config(chain_id=chain_b)
#             if chain_b_config.wait_block_validation \
#                     > chain_a_config.wait_block_validation:
#                 result.ok = chain_b
            
#         except BridgeRelayerConfigBlockchainDataMissing as e:
#             result.err = (
#                 f"Invalid chain ID {[chain_a, chain_b]}. Check "
#                 f"src.relayer.config.bridge_relayer_config.toml to identify "
#                 f"available chain IDs. "
#                 f"Error: {e}"
#             )

#         return result

#     def define_block_step_for_block_finality(
#         self, 
#         chain_id: int,
#         current_block_step: int,
#         saved_chain_id: int,
#         saved_block_step: int,
#     ) -> int:
#         """Define the block step according to the chain id.

#         The chain id provided is defined to validate block finality.
#         Block step may be the one already saved or the one comming from event
        
#         Args:
#             chain_id (int): The chain id defined for validate block finality
#             current_block_step (int): The current block number received with event
#             saved_chain_id (int): The saved chain id from a previous event
#             saved_block_step (int): The saved block step from a previous event

#         Returns:
#             int: The block step to use for validate the block finality
#         """
#         if chain_id == saved_chain_id:
#             return saved_block_step
#         return current_block_step

#     def calculate_block_finality(
#         self, 
#         chain_id: int, 
#         block_step: int
#     ) -> CalculateBlockFinalityResult:
#         """Calculate the block finality.

#         Args:
#             chain_id (int): The chain id
#             block_step (int): The current block

#         Returns:
#             CalculateBlockFinalityResult: 
#                 ok: The result with block finality
#                 err: An errir
#         """
#         result = CalculateBlockFinalityResult()

#         try:
#             blockchain_config: RelayerBlockchainConfigDTO = \
#                 get_blockchain_config(chain_id=chain_id)
#             wait_block_validation = blockchain_config.wait_block_validation
#             result.ok = block_step + wait_block_validation
            
#         except BridgeRelayerConfigBlockchainDataMissing as e:
#             result.err = (
#                 f"Invalid chain ID {[chain_id]}. Check "
#                 f"src.relayer.config.bridge_relayer_config.toml to identify "
#                 f"available chain IDs. "
#                 f"Error: {e}"
#             )

#         return result

#     async def validate_block_finality(
#         self,
#         chain_id: int,
#         block_finality: int,
#         sleep: int = 1,
#         allocated_time: int = 1200
#     ) -> None:
#         """Validate the block finality

#         Args:
#             chain_id (int): The chain id
#             block_finality (int): The block number target
#             sleep (int, optional): Sleep in second. Defaults to 1.
#             allocated_time (int, optional): Time in second allocated \
#                 to wait for block finality
#         """
#         self.rb_provider.set_chain_id(chain_id=chain_id)
#         elapsed_time = 0

#         while True:
#             if elapsed_time >= allocated_time:
#                 raise BlockFinalityTimeExceededError(
#                     "Block finality validation has exceeded the allocated"
#                     "time for processing."
#                 )

#             block_number = await self.rb_provider.get_block_number()
            
#             if block_number >= block_finality:
#                 break

#             message = (
#                 f"wait for block finality {block_number}/{block_finality} "
#                 f"chain_id = {chain_id} (allocated time={allocated_time})"
#             )            
#             self.print_log("wait", message)
#             await asyncio.sleep(sleep)
#             elapsed_time += 1

#     def manage_validate_block_finality(
#         self,
#         event_dto: EventDTO,
#         saved_chain_id: int,
#         saved_block_step: int,
#         sleep: int = 1,
#         allocated_time: int = 1200
#     ) -> BlockFinalityResult:
#         """Manage the block finality validation.

#             1. define the chain id the block finality is process to
#             2. define the current block number
#             3. calculate the block number target
#             4. validate the block finality

#         Args:
#             event_dto (EventDTO): The event dto
#             saved_chain_id (int): The saved chain id from a previous event
#             saved_block_step (int): The saved block step from a previous event
#             sleep (int, optional): Sleep in second. Defaults to 1.
#             allocated_time (int, optional): Time in second allocated \
#                 to wait for block finality

#         Returns:
#             BlockFinalityResult: The result
#         """
#         result = BlockFinalityResult()
#         block_step: int = event_dto.data['blockStep']

#         chain_id_result = self.define_chain_for_block_finality(
#             event_dto=event_dto,
#         )
#         if chain_id_result.err:
#             return chain_id_result
        
#         current_block_step = self.define_block_step_for_block_finality(
#             chain_id=chain_id_result.ok,
#             current_block_step=block_step,
#             saved_chain_id=saved_chain_id,
#             saved_block_step=saved_block_step,
#         )
        
#         block_finality_result = self.calculate_block_finality(
#             chain_id=chain_id_result.ok,
#             block_step=current_block_step,
#         )
#         if block_finality_result.err:
#             return block_finality_result
        
#         try:
#             asyncio.run(self.validate_block_finality(
#                 chain_id=chain_id_result.ok,
#                 block_finality=block_finality_result.ok,
#                 sleep=sleep,
#                 allocated_time=allocated_time,
#             ))
#             result.ok = "Success"
#         except BlockFinalityTimeExceededError as e:
#             result.err = str(e)

#         return result

#     def _callback(self, event: bytes) -> None:
#         """Handle the consumed events

#         Args:
#             event (bytes): The Event
#         """
#         try:
#             event_dto: EventDTO = self._convert_data_from_bytes(event=event)
#         except EventConverterTypeError as e:
#             self.print_log("fail", e)
#             return

#         params: int = event_dto.data['params']
#         chain_id_from: int = event_dto.data['params']['chainIdFrom']
#         chain_id_to: int = event_dto.data['params']['chainIdTo']
#         block_step: int = event_dto.data['blockStep']
#         operation_hash: str = event_dto.data['operationHash']
#         event_name: str = event_dto.name

#         self.print_log("receive", f"Received event: {event_dto.as_dict()}")

#         # Proxy rule to execute smart contract's function
#         if event_name in ['OperationCreated', 'FeesLockedConfirmed']:
#             self.print_log("info", f"Handle event : {event_dto.as_dict()}")

#             # Store event data
#             if self.store_operation_hash(
#                 operation_hash=operation_hash, 
#                 chain_id=chain_id_from,
#                 block_step=block_step,
#             ):
#                 return

#             # Validate block finality
#             saved_data = self.operation_hash_events[operation_hash]
#             saved_chain_id = saved_data['chain_id']
#             saved_block_step = saved_data['block_step']

#             result = self.manage_validate_block_finality(
#                 event_dto=event_dto,
#                 saved_chain_id=saved_chain_id,
#                 saved_block_step=saved_block_step,
#             )
#             if result.err:
#                 return result

#             # Execute task
#             func_name = "confirmFeesLockedAndDepositConfirmed"
#             bridge_task_dto = BridgeTaskDTO(
#                 func_name=func_name,
#                 params={
#                     "operationHash": operation_hash,
#                     "params": params,
#                     "blockStep": block_step,
#                 }
#             )

#             chain_id = chain_id_from
#             self.rb_provider.set_chain_id(chain_id=chain_id)
            
#             app = ExecuteContractTask(
#                 relayer_blockchain_provider=self.rb_provider)
#             app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)

#             # The second event has been emitted
#             # Clean the dict and continue the process
#             # del self.confirm_fees_locked_deposit_event[operation_hash]
#             del self.operation_hash_events[operation_hash]
            
#         elif event_name == "FeesLockedAndDepositConfirmed":
#             self.print_log("info", f"Handle event : {event_dto.as_dict()}")
            
#             func_name = "completeOperation"
#             chain_id = chain_id_to
            
#             self.rb_provider.set_chain_id(chain_id=chain_id)
#             app = ExecuteContractTask(
#                 relayer_blockchain_provider=self.rb_provider)
            
#             # params: Dict[str, Any] = {
#             #     "_operationHash": event_dto.data.operationHash,
#             #     "params": event_dto.data.params,
#             #     "blockStep": event_dto.data.blockStep,
#             # }
                        
#             bridge_task_dto = BridgeTaskDTO(
#                 func_name=func_name,
#                 params={
#                     "operationHash": operation_hash,
#                     "params": params,
#                     "blockStep": block_step,
#                 }
#             )
            
#             # Execute task
#             app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
#         elif event_name == "FeesDeposited":
#             self.print_log("info", f"Handle event : {event_dto.as_dict()}")
#             func_name = "sendFeesLockConfirmation"
#             chain_id = chain_id_to
            
#             self.rb_provider.set_chain_id(chain_id=chain_id)

#             app = ExecuteContractTask(
#                 relayer_blockchain_provider=self.rb_provider)
            
#             params: Dict[str, Any] = {
#                 "operationHash": event_dto.data.operationHash,
#                 "params": event_dto.data.params,
#                 "blockStep": event_dto.data.blockStep,
#             }

#             bridge_task_dto = BridgeTaskDTO(
#                 func_name=func_name,
#                 params=params
#             )
            
#             # Block validation
#             blockchain_config = get_blockchain_config(chain_id=chain_id)
#             wait_block_validation: int = blockchain_config.wait_block_validation
#             block_validated: int = block_step + wait_block_validation
            
#             while  asyncio.run(
#                 self.rb_provider.get_block_number()) < block_validated:
                
#                 latest_block = asyncio.run(self.rb_provider.get_block_number())
#                 print(
#                     f"[ ⏳ ] wait for block validation "
#                     f"{latest_block} -> {block_validated}"
#                 )
                
#                 if latest_block >= block_validated:
#                     break
#                 time.sleep(1)
            
#             # Execute task
#             app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
#         elif event_name == "FeesDepositConfirmed":
#             self.print_log("info", f"Handle event : {event_dto.as_dict()}")
#             func_name = "receiveFeesLockConfirmation"
#             chain_id = chain_id_from
            
#             self.rb_provider.set_chain_id(chain_id=chain_id)

#             app = ExecuteContractTask(
#                 relayer_blockchain_provider=self.rb_provider)
                      
#             params: Dict[str, Any] = {
#                 "operationHash": event_dto.data.operationHash,
#                 "params": event_dto.data.params,
#                 # "operator": event_dto.data.params.operator,
#                 "operator": "0x0000000000000000000000000000000000000000",
#             }
                        
#             bridge_task_dto = BridgeTaskDTO(
#                 func_name=func_name,
#                 params=params
#             )
            
#             # Execute task
#             app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)

#         elif event_name == "OperationFinalized":
#             self.print_log("info", f"Handle event : {event_dto.as_dict()}")
#             func_name = "receivedFinalizedOperation"
#             chain_id = chain_id_from
            
#             self.rb_provider.set_chain_id(chain_id=chain_id)

#             app = ExecuteContractTask(
#                 relayer_blockchain_provider=self.rb_provider)
            
#             params: Dict[str, Any] = {
#                 "operationHash": event_dto.data.operationHash,
#                 "params": event_dto.data.params,
#                 "blockStep": event_dto.data.blockStep,
#             }
                        
#             bridge_task_dto = BridgeTaskDTO(
#                 func_name=func_name,
#                 params=params
#             )           
            
#             # Execute task
#             app(chain_id=chain_id, bridge_task_dto=bridge_task_dto)
            
#         else:
#             self.print_log("alert", f"Ignore event : {event_dto.as_dict()}")

#         if self.verbose:
#             print(f"{50*'- '}")
        
#     def _convert_data_from_bytes(self, event: bytes) -> EventDTO:
#         """Convert attribut data from bytes.

#         Args:
#             event (bytes): The event

#         Returns:
#             EventDTO: The event DTO
#         """
#         try:
#             return EventDTO(**from_bytes(event))
#         except TypeError as e:
#             raise EventConverterTypeError(
#                 f"Unable to create an EventDTO. Event: {from_bytes(event)}. "
#                 f"Error: {e}"
#             )
                      
    
# class ExecuteContractTask:
#     """Blockchain Bridge Relayer contract executor."""
    
#     def __init__(
#         self,
#         relayer_blockchain_provider: IRelayerBlockchain,
#         verbose: bool = True
        
#     ) -> None:
#         """Init Blockchain Bridge Relayer instance.

#         Args:
#             relayer_blockchain_config (IRelayerBLockchainConfig): 
#                 The relayer blockchain provider
#             relayer_blockchain_event (IRelayerBlockchainEvent): 
#                 The relayer blockchain configuration
#             verbose (bool, optional): Verbose mode. Defaults to True.
#         """
#         self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
#         self.verbose: bool = verbose
        
#     def __call__(
#         self, 
#         chain_id: int,
#         bridge_task_dto: BridgeTaskDTO
#     ) -> None:
#         """Execute contract functions

#         Args:
#             chain_id (int): The blockchain id
#             func (str): The contract function to execute
#         """        
#         self.rb_provider.set_chain_id(chain_id=chain_id)
#         self.call_contract_func(
#             chain_id=chain_id, 
#             bridge_task_dto=bridge_task_dto,
#         )

#     def call_contract_func(
#         self, 
#         chain_id: int,
#         bridge_task_dto: BridgeTaskDTO,
#     ) -> None:
#         """Call the smart contract's function.

#         Args:
#             chain_id (int): The chain id
#             bridge_task_dto (BridgeTaskDTO): A BridgeTaskDTO instance
#         """
#         print(
#             f"[ 💠 ] Sending transaction to chain id {chain_id}, "
#             f"function {bridge_task_dto.func_name} ..."
#         )
#         result: BridgeTaskResult = asyncio.run(
#             self.rb_provider.call_contract_func(
#                 bridge_task_dto=bridge_task_dto
#             )
#         )
        
#         if result.ok:
#             bridge_task_tx_result: BridgeTaskTxResult = result.ok

#             print(
#                 f"[ 💚 ] Transaction done with contract's function "
#                 f"'{bridge_task_dto.func_name}'. "
#                 f"Transaction hash : {bridge_task_tx_result.tx_hash}"
#             )
#         else:
#             print(
#                 f"[ 💔 ] Transaction failed '{bridge_task_dto.func_name}'. "
#                 f"{result.err}"
#             )         
