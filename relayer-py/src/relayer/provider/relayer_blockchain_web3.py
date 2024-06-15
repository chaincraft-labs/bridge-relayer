"""
Provider that aims to listen events from blockchain and execute smart contracts.

The library used is web3.py

https://web3py.readthedocs.io/
"""
import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, NoReturn

from attributedict.collections import AttributeDict
from eth_account.signers.local import LocalAccount
from eth_account.datastructures import SignedTransaction
from hexbytes import HexBytes
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.contract.async_contract import AsyncContract
from web3.middleware.geth_poa import async_geth_poa_middleware
from web3._utils.filters import AsyncLogFilter
from web3.types import (
    BlockData,
    TxReceipt,
    Nonce,
)

from src.relayer.interface.relayer import IRelayerBlockchain
from src.relayer.domain.exception import BridgeRelayerBlockchainNotConnected
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    BridgeTaskResult,
    BridgeTaskTxResult,
    EventDTO,
)
from src.relayer.config import get_blockchain_config, get_abi


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER: logging.Logger = logging.getLogger(__name__)


class RelayerBlockchainProvider(IRelayerBlockchain):
    """Relayer blockchain provider."""
    
    def __init__(self, debug: bool = False) -> None:
        """Init RelayerBlockchainProvider.

        Args:
            debug (bool, optional): Enable/disable logging. Defaults to False.
        """
        self._debug: bool = debug
        # 
        self.chain_id: int
        self.relay_blockchain_config: Any
        self.w3: AsyncWeb3
        self.w3_contract: AsyncContract
        
        # Set Logging
        self._set_logging(debug)
        
    @property
    def debug(self) -> bool:
        """Get the debug value.

        Returns:
            bool: The debug value
        """
        return self._debug
    
    @debug.setter
    def debug(self, value: bool) -> None:
        """Set the debug value and enable disable the logging.

        Args:
            value (bool): The debug value
        """
        self._debug = value
        self._set_logging(value)
        
    # -------------------------------------------------------------
    # Implemented functions
    # -------------------------------------------------------------
    def set_chain_id(self, chain_id: int) -> None:
        """Set the blockchain id.

        Args:
            chain_id (int): The chain id
        """
        self.chain_id = chain_id
        self.relay_blockchain_config = get_blockchain_config(self.chain_id)
        self._connect()
            
    async def get_block_number(self) -> int:
        """Get the block number.

        Returns:
            (int): The block number
        """
        block_data: BlockData = await self._get_block_data()
        return block_data.number # type: ignore
    
    def listen_events(
        self, 
        callback: Callable,
        poll_interval: int = 2,
    ) -> None:
        """The main blockchain event listener.

        Args:
            poll_interval int: The loop poll interval in second 
                Default is 2
        """        
        LOGGER.info('Listens events (main)')
        
        event_filter: List[AsyncLogFilter] = self._execute_event_filters()
        loop_events: List[Coroutine[Any, Any, NoReturn]] = [
            self._log_loop(event, poll_interval, callback) 
            for event in event_filter
        ]
        
        loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(asyncio.gather(*loop_events))
        finally:
            loop.close()
    
    async def call_contract_func(
        self, 
        bridge_task_dto: BridgeTaskDTO
    ) -> BridgeTaskResult:
        """Call a contract's function.
        
        Args:
            bridge_task_dto (BridgeTaskDTO): The bridge task DTO

        Returns:
            BridgeTaskResult: The bridge task execution result
        """
        LOGGER.info(f"Call smart contract's function {bridge_task_dto}!")
        LOGGER.info(f"Client version : {await self.client_version()}!")
        
        result = BridgeTaskResult()
        pk: str = self.relay_blockchain_config.pk
        account: LocalAccount = self.w3.eth.account.from_key(pk)
        nonce: Nonce = await self._get_nonce(account=account)
        # estimated_gas = await self._estimate_gas(
        #     func_name=bridge_task_dto.func_name)
        # LOGGER.info(f"estimated gas for '{bridge_task_dto.func_name}' {estimated_gas}!")

        try:
            func: Callable = self._get_function_by_name(
                bridge_task_dto=bridge_task_dto)
            
            unsent_built_tx: Dict[str, Any] = await self._build_tx(
                func=func,
                bridge_task_dto=bridge_task_dto,
                account=account,
                nonce=nonce
            )

            signed_tx: SignedTransaction = self._sign_tx(unsent_built_tx, account=account)
            tx_hash: HexBytes = await self._send_raw_tx(signed_tx=signed_tx)
            tx_receipt: TxReceipt = await self._wait_for_transaction_receipt(tx_hash)

            result.ok = BridgeTaskTxResult(
                tx_hash=tx_receipt.transactionHash.hex(), # type: ignore
                block_hash=tx_receipt.blockHash.hex(), # type: ignore
                block_number=tx_receipt.blockNumber, # type: ignore
                gas_used=tx_receipt.gasUsed, # type: ignore
            )
        except Exception as e:
            LOGGER.error(
                f"Call smart contract's function {bridge_task_dto} "
                f"failed with error : {e}"
            )
            result.err = e
            
        return result
    
    # -----------------------------------------------------------------
    # Internal functions
    # -----------------------------------------------------------------
    async def _estimate_gas(self, bridge_task_dto: BridgeTaskDTO):
        func = self._get_function_by_name(bridge_task_dto)
        return await func(**bridge_task_dto.params).estimate_gas()
    
    
    def _set_logging(self, value: bool) -> None:
        """Enable or disable the logging.

        Args:
            value (bool): A value indicating the logging on/off
        """        
        if value is True:
            logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
            LOGGER.propagate = True
        else:
            LOGGER.propagate = False
    
    def _connect(self) -> None:
        """Connect to client provider.

        Returns:
            None
        """
        self.w3 = self._set_provider()
        self.w3_contract = self._set_contract()
    
    async def client_version(self) -> str:
        """Get the client version

        Returns:
            str: the client version
        """
        try:
            return await self.w3.client_version
        except Exception as e:
            raise BridgeRelayerBlockchainNotConnected(e)
    
    async def _get_block_data(self) -> BlockData:
        """Get the block data.

        Returns:
            (BlockData): The block data
        """
        return await self.w3.eth.get_block("latest")       
            
    def _set_provider(self) -> AsyncWeb3:
        """Set the web3 provider.

        Returns:
            AsyncWeb3: A provider instance
        """
        LOGGER.info('Setting the w3 provider instance!')
        
        w3 = AsyncWeb3(AsyncHTTPProvider(
            f"{self.relay_blockchain_config.rpc_url}"\
            f"{self.relay_blockchain_config.project_id}"
        ))
        
        if self.relay_blockchain_config.client == "middleware":
            w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
            
        return w3
    
    def _set_contract(self) -> AsyncContract:
        """Set the web3 contrat instance.

        Returns:
            AsyncContract: A contract instance.
        """
        LOGGER.info('Setting the w3 contract instance!')
        
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(
                self.relay_blockchain_config.smart_contract_address),
            abi=get_abi(self.chain_id)
        )
    
    def _create_event_filters(self) -> List[Coroutine]:
        """Create a list of event filters.

        The event filter list can be created like this if we suppose 
        these two events 'OwnerSet and OwnerGet' are defined in the abi.
        
        .. code-block:: python
        >>> [
        >>>    self.w3_contract.events.OwnerSet().create_filter(fromBlock='latest')
        >>>    self.w3_contract.events.OwnerGet().create_filter(fromBlock='latest')
        >>> ]

        Returns:
            List[Coroutine]: The list of event filter
        """
        LOGGER.info('Create the event filters list!')
        
        return [
            event.create_filter(fromBlock='latest') 
            for event in self.w3_contract.events # type: ignore
        ]
            
    def _execute_event_filters(self) -> List[AsyncLogFilter]:
        """Execute the coroutine event filters.

        Returns:
            List[AsyncLogFilter]: A list of event filter log
        """
        LOGGER.info('Execute the event filters!')
        
        return [
            asyncio.run(event_filter) 
            for event_filter in self._create_event_filters()
        ]
    
    def create_event_dto(self, event: AttributeDict) -> EventDTO:
        """Create a Event DTO from the event.

        Args:
            event (AttributeDict): The event received from blockchain

        Returns:
            EventDTO: The event DTO
        """
        LOGGER.info('Create event DTO from the event!')
        
        return EventDTO(name=event.event, data=event.args)
    
    def _handle_event(self, event: AttributeDict, callback: Callable) -> None:
        """Handle the event. 
        
        The event must be handled by the callback function that is defined\
            in the application layer

        Args:
            event (AttributeDict): The event received from blockchain
            callback (Callable): A callback function
        """
        LOGGER.info(f'Handle the event : {event}')
        
        event_dto: EventDTO = self.create_event_dto(event)
        callback(event_dto)
    
    async def _loop_handle_event(
        self,
        event_filter: AsyncLogFilter,
        poll_interval: int,
        callback: Callable,
    ):
        """Handle an event filter.

        Args:
            event_filter (AsyncLogFilter): The web3 event filter
            poll_interval (int): The loop poll interval in second
            callback (Callable): A callback function to handle event

        Returns:
            NoReturn
        """
        for event in await event_filter.get_new_entries():
            self._handle_event(event, callback) # type: ignore

            await asyncio.sleep(poll_interval)   
    
    async def _log_loop(
        self, 
        event_filter: AsyncLogFilter,
        poll_interval: int,
        callback: Callable,
    ) -> NoReturn:
        """Listen to event filter.

        Args:
            event_filter (AsyncLogFilter): The web3 event filter
            poll_interval (int): The loop poll interval in second
            callback (Callable): A callback function to handle event

        Returns:
            NoReturn
        """
        LOGGER.info(f"Listen to event {event_filter}!")
        
        while True:
            await self._loop_handle_event(
                event_filter=event_filter,
                poll_interval=poll_interval,
                callback=callback,
            )
            await asyncio.sleep(poll_interval)

    # -------------------------------------------------------------
    # Send Tx to chain
    # -------------------------------------------------------------
    async def _get_nonce(self, account: LocalAccount) -> Nonce:
        """Get the nonce.

        Args:
            account (LocalAccount):  A collection of convenience methods to \
                sign and encrypt, with an embedded private key.

        Returns:
            Nonce: A nonce (int)
        """
        LOGGER.info(f"Get nonce for address : {account.address}!")
        
        return await self.w3.eth.get_transaction_count(account.address)
        
    def _get_function_by_name(
        self, 
        bridge_task_dto: BridgeTaskDTO,
    ) -> Callable:
        """Get the smart contract's function.

        Args:
            bridge_task_dto (BridgeTaskDTO): A bridge task DTO

        Returns:
            Callable: A smart contract's function.
        """
        LOGGER.info(
            f"Get smart contract's function {bridge_task_dto.func_name}!")
        
        return self.w3_contract.get_function_by_name(bridge_task_dto.func_name)
    
    async def _build_tx(
        self, 
        func: Callable, 
        bridge_task_dto: BridgeTaskDTO,
        account: LocalAccount,
        nonce: Nonce,
    ) -> Dict[str, Any]:
        """Build a transaction.

        Args:
            func (Callable): A smart contarct's function
            bridge_task_dto (BridgeTaskDTO): A bridge task DTO
            account (LocalAccount):  A collection of convenience methods to \
                sign and encrypt, with an embedded private key.
            nonce (Nonce): A nonce (int)

        Returns:
            Dict[str, Any]: The built transaction
        """
        LOGGER.info(
            f"Build a transaction with "
            f"func name : {bridge_task_dto.func_name} "
            f"params    : {bridge_task_dto.params} "
            f"address: {account.address}!")
        
        try:
            return await func(**bridge_task_dto.params) \
                .build_transaction(transaction={
                    "from": account.address,
                    "nonce": nonce,
                    # "maxFeePerGas": 20000000000, 
                    # "maxPriorityFeePerGas": 1000000000
                })
        except Exception as e:
            print("******************************************")
            print(e)
            print("******************************************")
            raise

    def _sign_tx(
        self, 
        built_tx: Dict[str, Any], 
        account: LocalAccount
    ) -> SignedTransaction:
        """Sign the transaction.

        Args:
            built_tx (Dict[str, Any]): The built transaction
            account (LocalAccount): A collection of convenience methods to \
                sign and encrypt, with an embedded private key.

        Returns:
            SignedTransaction: The signed transaction
        """
        LOGGER.info(f"Sign the transaction : {built_tx}!")
        
        try:
            return self.w3.eth.account.sign_transaction(
                built_tx, private_key=account.key)
        except Exception as e:
            raise
    
    async def _send_raw_tx(
        self, 
        signed_tx: SignedTransaction
    ) -> HexBytes:
        """Send the raw transaction.

        Args:
            signed_tx (SignedTransaction): A signed transaction

        Returns:
            HexBytes: The transaction hash
        """
        LOGGER.info(f"Send the raw transaction signed_tx : {signed_tx}!")
        
        return await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
    async def _wait_for_transaction_receipt(
        self, 
        tx_hash: HexBytes
    ) -> TxReceipt:
        """Wait for the transaction receipt.

        Args:
            tx_hash (HexBytes): The transaction hash

        Returns:
            TxReceipt: The transaction receipt
        """
        LOGGER.info(
            f"Wait for the transaction receipt for tx_hash : {tx_hash.hex()}!")
        
        return await self.w3.eth.wait_for_transaction_receipt(tx_hash)


