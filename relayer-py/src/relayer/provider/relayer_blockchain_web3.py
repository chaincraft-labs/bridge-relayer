"""
Provider that aims to listen events from blockchain and execute smart contracts.

The library used is web3.py

https://web3py.readthedocs.io/
"""
import asyncio
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

from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.interface.relayer import IRelayerBlockchain
from src.relayer.domain.exception import (
    BridgeRelayerBlockchainNotConnected, 
    BridgeRelayerListenEventFailed,
    BridgeRelayerEventsFilterTypeError
)
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    BridgeTaskResult,
    BridgeTaskTxResult,
    EventDTO,
)
from src.relayer.config.config import get_blockchain_config, get_abi
from src.relayer.application.base_logging import RelayerLogging


class RelayerBlockchainProvider(RelayerLogging, IRelayerBlockchain):
    """Relayer blockchain provider."""

    def __init__(self) -> None:
        """Init RelayerBlockchainProvider.

        Args:
            debug (bool, optional): Enable/disable logging. Defaults to False.
        """
        super().__init__()
        self.chain_id: int
        self.relay_blockchain_config: RelayerBlockchainConfigDTO
        self.w3: AsyncWeb3
        self.w3_contract: AsyncContract
        self.event_filter: List[str] = []

    # -------------------------------------------------------------
    # Implemented functions
    # -------------------------------------------------------------
    def set_chain_id(self, chain_id: int) -> None:
        """Set the blockchain id.

        Args:
            chain_id (int): The chain id
        """
        self.logger.info("Set chain id")

        self.chain_id = chain_id
        self.logger.debug(f"chain_id={chain_id}")

        self.relay_blockchain_config = get_blockchain_config(self.chain_id)
        self.logger.debug(
            f"relay_blockchain_config={self.relay_blockchain_config}")

        self._connect()

    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.
        """
        self.logger.info("Set event filter")

        if not isinstance(events, list):
            raise BridgeRelayerEventsFilterTypeError(
                "'events' not a list!"
            )
        
        self.event_filter = events


    async def get_block_number(self) -> int:
        """Get the block number.

        Returns:
            (int): The block number
        """
        self.logger.info('Get block number')
        
        block_data: BlockData = await self._get_block_data()
        self.logger.debug(f'block_data.number={block_data.number}')

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
        self.logger.info('Listens events')

        try:
            loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
            self.logger.debug(f"loop={loop}")
        
            event_filter: List[AsyncLogFilter] = self._execute_event_filters()
            self.logger.debug(f"event_filter={event_filter}")

            loop_events: List[Coroutine[Any, Any, NoReturn]] = [
                self._log_loop(event, poll_interval, callback)
                for event in event_filter
            ]
            self.logger.debug(f"loop_events={loop_events}")

            # loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
            # self.logger.debug(f"loop={loop}")

            asyncio.set_event_loop(loop)
            loop.run_until_complete(asyncio.gather(*loop_events))

        except Exception as e:
            self.logger.error(f"Fail listen event! Error={e}")
            raise BridgeRelayerListenEventFailed(e)

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
        result = BridgeTaskResult()

        try:
            self.logger.info(f"Call smart contract's function {bridge_task_dto}!")
            self.logger.info(f"Client version : {await self.client_version()}!")

            pk: str = self.relay_blockchain_config.pk
            
            account: LocalAccount = self.w3.eth.account.from_key(pk)
            self.logger.debug(f"account={account}")

            nonce: Nonce = await self._get_nonce(account=account)
            self.logger.debug(f"nonce={nonce}")

            func: Callable = self._get_function_by_name(
                bridge_task_dto=bridge_task_dto)
            self.logger.debug(f"func={func}")

            built_tx: Dict[str, Any] = await self._build_tx(
                func=func,
                bridge_task_dto=bridge_task_dto,
                account=account,
                nonce=nonce
            )
            self.logger.debug(f"built_tx={built_tx}")

            signed_tx: SignedTransaction = self._sign_tx(built_tx, account=account)
            self.logger.debug(f"signed_tx={signed_tx}")

            tx_hash: HexBytes = await self._send_raw_tx(signed_tx=signed_tx)
            self.logger.debug(f"tx_hash={tx_hash}")

            tx_receipt: TxReceipt = await self._wait_for_transaction_receipt(tx_hash)
            self.logger.debug(f"tx_receipt={tx_receipt}")

            result.ok = BridgeTaskTxResult(
                tx_hash=tx_receipt.transactionHash.hex(), # type: ignore
                block_hash=tx_receipt.blockHash.hex(), # type: ignore
                block_number=tx_receipt.blockNumber, # type: ignore
                gas_used=tx_receipt.gasUsed, # type: ignore
            )
            self.logger.debug(f"result={result.ok }")
        except Exception as e:
            self.logger.error(
                f"Fail calling smart contract's function {bridge_task_dto}!"
                f"Error={e}"
            )
            result.err = e

        return result

    # -----------------------------------------------------------------
    # Internal functions
    # -----------------------------------------------------------------
    async def _estimate_gas(self, bridge_task_dto: BridgeTaskDTO):
        func = self._get_function_by_name(bridge_task_dto)
        return await func(**bridge_task_dto.params).estimate_gas()

    def _connect(self) -> None:
        """Connect to client provider.

        Returns:
            None
        """
        self.logger.info("Connect to client provider")

        self.w3 = self._set_provider()
        self.w3_contract = self._set_contract()

    async def client_version(self) -> str:
        """Get the client version

        Returns:
            str: the client version
        """
        self.logger.info("Get the client version")

        try:
            client_version = await self.w3.client_version
            self.logger.debug(f"client_version={client_version}")
            return client_version
        except Exception as e:
            self.logger.error(f"Fail getting client version! Error={e}")
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
        self.logger.info('Set the w3 provider instance')

        w3 = AsyncWeb3(AsyncHTTPProvider(
            f"{self.relay_blockchain_config.rpc_url}"\
            f"{self.relay_blockchain_config.project_id}"
        ))

        if self.relay_blockchain_config.client == "middleware":
            w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
        self.logger.debug(f'w3={w3}')

        return w3

    def _set_contract(self) -> AsyncContract:
        """Set the web3 contrat instance.

        Returns:
            AsyncContract: A contract instance.
        """
        self.logger.info('Set the w3 contract instance')

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
        self.logger.info('Create the event filters list')

        return [
            event.create_filter(fromBlock="latest")
            for event in self.w3_contract.events # type: ignore
            if event.event_name in self.event_filter
        ]

    def _execute_event_filters(self) -> List[AsyncLogFilter]:
        """Execute the coroutine event filters.

        Returns:
            List[AsyncLogFilter]: A list of event filter log
        """
        self.logger.info('Execute the event filters')

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
        self.logger.info('Create event DTO')

        return EventDTO(name=event.event, data=event.args)

    def _handle_event(self, event: AttributeDict, callback: Callable) -> None:
        """Handle the event.

        The event must be handled by the callback function that is defined\
            in the application layer

        Args:
            event (AttributeDict): The event received from blockchain
            callback (Callable): A callback function
        """
        self.logger.info('Handle the event')
        self.logger.debug(f'event={event}')

        event_dto: EventDTO = self.create_event_dto(event)
        self.logger.debug(f'event_dto={event_dto}')

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
        self.logger.info(f"Listen to event {event_filter}!")

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
        self.logger.info("Get nonce for address")
        self.logger.debug(f"address={account.address}!")

        nonce = await self.w3.eth.get_transaction_count(account.address)
        self.logger.debug(f"result: nonce={nonce}!")

        return nonce

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
        self.logger.info("Get smart contract's function")
        self.logger.debug(f"func_name={bridge_task_dto.func_name}")

        func =  self.w3_contract.get_function_by_name(bridge_task_dto.func_name)
        self.logger.debug(f"result: func={func}")
        return func

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
        self.logger.info("Build transaction")
        self.logger.debug(f"func_name={bridge_task_dto.func_name}")
        self.logger.debug(f"params={bridge_task_dto.params}")
        self.logger.debug(f"address={account.address}")

        try:
            built_tx = await func(**bridge_task_dto.params) \
                .build_transaction(transaction={
                    "from": account.address,
                    "nonce": nonce,
                })
            self.logger.debug(f"result: built_tx={built_tx}")
            return built_tx
        except Exception as e:
            print(e)
            self.logger.error(f"Fail building transaction! Error={e}")
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
        self.logger.info("Sign transaction")
        self.logger.debug(f"built_tx={built_tx}")

        try:
            signed_tx = self.w3.eth.account.sign_transaction(
                built_tx, private_key=account.key
            )
            self.logger.debug(f"result: signed_tx={signed_tx}!")
            return signed_tx
        except Exception as e:
            self.logger.error(f"Fail signing transaction! Error={e}")
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
        self.logger.info("Send the raw transaction signed_tx")
        self.logger.debug(f"signed_tx={signed_tx}")

        tx_hash = await self.w3.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        self.logger.debug(f"result: tx_hash={tx_hash}")

        return tx_hash

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
        self.logger.info("Wait for transaction receipt for tx_hash")
        self.logger.debug(f"tx_hash={tx_hash.hex()}")
        
        tx_receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.logger.debug(f"result: tx_hash={tx_hash.hex()}")

        return tx_receipt
