"""Provider to connect to RPC node.

- scan events
- execute smart contracts

The library used is web3.py

https://web3py.readthedocs.io/
"""
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from hexbytes import HexBytes

from eth_account.datastructures import SignedTransaction
from eth_account.signers.local import LocalAccount
from eth_abi.codec import ABICodec
from web3 import HTTPProvider, Web3
from web3.contract.base_contract import BaseContractEvent
from web3.contract.contract import Contract
from web3.exceptions import BlockNotFound
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3.types import (
    BlockData,
    ABIEvent,
    EventData,
    LogReceipt,
    Nonce,
    TxReceipt,
)
from eth_typing import (
    Address,
)

from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.config.config import Config
from src.relayer.domain.event_db import (
    BridgeTaskActionDTO,
    BridgeTaskTxResult,
    EventDTO,
    EventDataDTO,
)
from src.relayer.domain.exception import (
    RelayerBlockchainBuildTxError,
    RelayerBlockchainSendRawTxError,
    RelayerBlockchainSignTxError,
    RelayerErrorBlockPending,
    RelayerEventsNotFound,
    RelayerFetchEventOutOfRetries,
    RelayerBlockchainFailedExecuteSmartContract,
    RelayerClientVersionError,
)
from src.relayer.interface.relayer_blockchain import IRelayerBlockchain
from src.utils.converter import bytes_to_hex


class RelayerBlockchainProvider(IRelayerBlockchain):
    """Relayer blockchain provider."""

    def __init__(
        self,
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000,
        max_request_retries: int = 30,
        request_retry_seconds: float = 3.0,
        num_blocks_rescan_for_forks: int = 10,
        chunk_size_decrease: float = 0.5,
        chunk_size_increase: float = 2.0,
    ) -> None:
        """Relayer blockchain provider.

        Args:
            min_scan_chunk_size (int, optional): Minimum chunk size.
                Defaults to 10.
            max_scan_chunk_size (int, optional): Maximum chunk size.
                Defaults to 10000.
            max_request_retries (int, optional): Maximum number of retries.
                Defaults to 30.
            request_retry_seconds (float, optional): Request retry seconds.
                Defaults to 3.0.
            num_blocks_rescan_for_forks (int, optional): Number of blocks to
                rescan for forks. Defaults to 10.
            chunk_size_decrease (float, optional): Chunk size decrease.
                Defaults to 0.5.
            chunk_size_increase (float, optional): Chunk size increase.
                Defaults to 2.0.
            log_level (str): The log level. Defaults to 'info'.
        """
        self.chain_id: int = None
        self.events: List[type[BaseContractEvent]] = []
        self.filters: Dict[str, Any] = {}
        self.relay_blockchain_config: Dict[str, Any] = {}
        self.relay_blockchain_config: RelayerBlockchainConfigDTO
        self.block_timestamps: Dict[int, Any] = {}
        self.w3: Web3
        self.w3_contract: Contract

        # Our JSON-RPC throttling parameters
        # 12 s/block = 120 seconds period
        self.min_scan_chunk_size = min_scan_chunk_size
        self.max_scan_chunk_size = max_scan_chunk_size
        self.max_request_retries = max_request_retries
        self.request_retry_seconds = request_retry_seconds
        self.num_blocks_rescan_for_forks = num_blocks_rescan_for_forks

        # Factor how fast we increase the chunk size if results are found
        # (slow down scan after starting to get hits)
        self.chunk_size_decrease = chunk_size_decrease

        # Factor how fast we increase chunk size if no results found
        self.chunk_size_increase = chunk_size_increase

        # # Load config (singleton)
        self.config = Config()
        self.errors: Dict[str, str] = {}

    # -------------------------------------------------------------
    # Implemented functions
    # -------------------------------------------------------------
    def connect_client(self, chain_id: int):
        """Connect to the web3 client.

        Args:
            chain_id (int): The chain id.
        """
        self.chain_id = chain_id
        self.relay_blockchain_config = self.config.get_blockchain_config(
            self.chain_id,
        )
        self.errors = self.config.get_smart_contract_errors(chain_id)

        self.w3: Web3 = self._set_provider()
        self.w3_contract: Contract = self._set_contract()

    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.

        Raises:
            RelayerEventsNotFound
        """
        try:
            self.events = [self.w3_contract.events[event] for event in events]
            self.event_filter = events

        except KeyError as e:
            msg = (f"Failed to set events! error={e}")
            raise RelayerEventsNotFound(msg)

    def get_current_block_number(self) -> int:
        """Get the current block number on chain.

        Returns:
            (int): The current block number.
        """
        return self.w3.eth.block_number

    def client_version(self) -> str:
        """Get the client version.

        Returns:
            str: the client version.

        Raises:
            RelayerClientVersionError
        """
        try:
            return self.w3.client_version

        except Exception as e:
            msg = (f"Failed to get client version! error={e}")
            raise RelayerClientVersionError(msg)

    def get_account_address(self) -> str:
        """Get the account address.

        Returns:
            str: The account address.
        """
        pk = self.relay_blockchain_config.pk
        account: LocalAccount = self.w3.eth.account.from_key(pk)
        return account.address

    def get_block_timestamp(self, block_num: int) -> Optional[datetime]:
        """Get Ethereum block timestamp.

        Args:
            block_num (int): The block number.

        Returns:
            Optional[datetime]: The block timestamp
        """
        try:
            block_info: BlockData = self.w3.eth.get_block(block_num)

            if block_num not in self.block_timestamps:
                self.block_timestamps[block_num] = datetime.fromtimestamp(
                    timestamp=block_info["timestamp"],
                    tz=timezone.utc
                )

            return self.block_timestamps[block_num]

        except (BlockNotFound, TypeError, ValueError):
            return None

    def scan(
        self,
        start_block: int,
        end_block: int,
    ) -> Tuple[List[EventDTO], int]:
        """Read and process events between two block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC
        server pukes out.

        Args:
            start_block (int): The first block to scan
            end_block (int): The last block to scan

        Returns:
            Tuple[List[EventDTO], int]: Events, end block
        """
        events_dto: List[EventDTO] = []
        new_end_block: int = end_block

        for event_type in self.events:
            (
                new_end_block,
                event_datas,
            ) = self._retry_web3_call(
                fetch_event_logs=self._fetch_event_logs,
                event_type=event_type,
                start_block=start_block,
                end_block=end_block,
                retries=self.max_request_retries,
                delay=self.request_retry_seconds,
            )

            for event_data in event_datas:
                if event_data is None:
                    continue

                event_dto = self._create_event_data_dto(event=event_data)
                if event_dto is None:
                    continue

                events_dto.append(event_dto)

        return (events_dto, new_end_block)

    def call_contract_func(
        self,
        bridge_task_action_dto: BridgeTaskActionDTO
    ) -> BridgeTaskTxResult:
        """Call a contract's function.

        Args:
            bridge_task_action_dto (BridgeTaskActionDTO): The bridge task DTO.

        Returns:
            BridgeTaskTxResult: The bridge transaction result.

        Raises:
            RelayerBlockchainFailedExecuteSmartContract
        """
        try:
            pk: str = self.relay_blockchain_config.pk
            account: LocalAccount = self.w3.eth.account.from_key(pk)
            nonce: Nonce = self.w3.eth.get_transaction_count(
                account=account.address
            )
            func: Callable = self.w3_contract.get_function_by_name(
                bridge_task_action_dto.func_name
            )
            built_tx: Dict[str, Any] = self._build_tx(
                func=func,
                params=bridge_task_action_dto.params,
                account_address=account.address,
                nonce=nonce
            )
            signed_tx: SignedTransaction = self._sign_tx(
                built_tx=built_tx,
                account_key=account.key
            )
            tx_hash: HexBytes = self._send_raw_tx(signed_tx=signed_tx)
            tx_receipt: TxReceipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash
            )

            if tx_receipt.status == 0:
                raise RelayerBlockchainFailedExecuteSmartContract(tx_receipt)

            return BridgeTaskTxResult(
                tx_hash=tx_receipt.transactionHash.hex(),  # type: ignore
                block_hash=tx_receipt.blockHash.hex(),  # type: ignore
                block_number=tx_receipt.blockNumber,  # type: ignore
                gas_used=tx_receipt.gasUsed,  # type: ignore
                status=tx_receipt.status,  # type: ignore
            )

        except Exception as e:
            raise RelayerBlockchainFailedExecuteSmartContract(e)

    # -------------------------------------------------------------
    # Internal functions
    # -------------------------------------------------------------

    def get_error_name(self, error: Exception) -> Exception:
        """Get the error name.

        Args:
            error (Exception): The error

        Returns:
            Exception: The error name
        """
        if isinstance(error.args[0], tuple) and \
                self.errors.get(error.args[0][0]):
            error_name = self.errors[error.args[0][0]]
            return Exception(error.args[0][0], error_name)
        return error

    def _build_tx(
        self,
        func: Callable,
        params: Dict[str, Any],
        account_address: Address,
        nonce: Nonce,
    ) -> Dict[str, Any]:
        """Build a transaction.

        Args:
            func (Callable): The smart contarct's function
            params (Dict): The params
            account_address (Address):  The account address
            nonce (Nonce): The nonce (int)

        Returns:
            Dict[str, Any]: The built transaction

        Raises:
            RelayerBlockchainBuildTxError
        """
        try:
            return func(**params).build_transaction(
                transaction={
                    "from": account_address,
                    "nonce": nonce,
                }
            )

        except Exception as e:
            msg = f"Build transaction failed! error={self.get_error_name(e)}"
            raise RelayerBlockchainBuildTxError(msg)

    def _sign_tx(
        self,
        built_tx: Dict[str, Any],
        account_key: Any
    ) -> SignedTransaction:
        """Sign the transaction.

        Args:
            built_tx (Dict[str, Any]): The built transaction
            account_key (LocalAccount): The account key

        Returns:
            SignedTransaction: The signed transaction

        Raises:
            RelayerBlockchainSignTxError
        """
        try:
            return self.w3.eth.account.sign_transaction(
                built_tx,
                private_key=account_key
            )

        except Exception as e:
            msg = (
                f"Failed to sign transaction! error={self.get_error_name(e)}"
            )
            raise RelayerBlockchainSignTxError(msg)

    def _send_raw_tx(
        self,
        signed_tx: SignedTransaction
    ) -> HexBytes:
        """Send the raw transaction.

        Args:
            signed_tx (SignedTransaction): A signed transaction

        Returns:
            HexBytes: The transaction hash

        Raises:
            RelayerBlockchainSendRawTxError
        """
        try:
            return self.w3.eth.send_raw_transaction(
                signed_tx.rawTransaction
            )

        except Exception as e:
            msg = (
                f"Failed to send raw transaction! "
                f"error={self.get_error_name(e)}"
            )
            raise RelayerBlockchainSendRawTxError(msg)

    def _set_provider(self) -> Web3:
        """Set the web3 provider.

        Returns:
            Web3: A provider instance
        """
        rpc_url = (
            f"{self.relay_blockchain_config.rpc_url}"
            f"{self.relay_blockchain_config.project_id}"
        )
        provider = HTTPProvider(endpoint_uri=rpc_url)
        provider.middlewares.clear()  # type: ignore

        return Web3(provider)

    def _set_contract(self) -> Contract:
        """Set the web3 contrat instance.

        Returns:
            Contract: A contract instance.
        """
        return self.w3.eth.contract(
            Web3.to_checksum_address(
                self.relay_blockchain_config.smart_contract_address
            ),
            abi=self.config.get_abi(self.chain_id)
        )

    def _fetch_event_logs(
        self,
        event_type: type[BaseContractEvent],
        from_block: int,
        to_block: int
    ) -> List[EventData]:
        """Get event logs using eth_getLogs API.

        This method is detached from any contract instance.

        This is a stateless method, as opposed to create_filter.
        It can be safely called against nodes which do not provide
        `eth_newFilter` API, like Infura.

        Args:
            w3 (Web3): _description_
            event_type (type[BaseContractEvent]): _description_
            from_block (int): _description_
            to_block (int): _description_

        Raises:
            TypeError: _description_

        Returns:
            List[EventData]: _description_
        """
        # Currently no way to poke this using a public web3.py API.
        # This will return raw underlying ABI JSON object for the event
        abi: ABIEvent = event_type._get_event_abi()

        # Depending on the Solidity version used to compile
        # the contract that uses the ABI,
        # it might have Solidity ABI encoding v1 or v2.
        # We just assume the default that you set on Web3 object here.
        # More information here
        # https://eth-abi.readthedocs.io/en/latest/index.html
        codec: ABICodec = self.w3.codec

        # Here we need to poke a bit into Web3 internals, as this
        # functionality is not exposed by default.
        # Construct JSON-RPC raw filter presentation based on human readable
        # Python descriptions
        # Namely, convert event names to their keccak signatures
        # More information here:
        # https://github.com/ethereum/web3.py/blob/e176ce0793dafdd0573acc8d4b76425b6eb604ca/web3/_utils/filters.py#L71

        # e.g: event_filter_params
        # {
        #   'topics': ['0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333'],  # noqa
        #   'fromBlock': 6190119,
        #   'toBlock': 6190139
        # }
        (
            data_filter_set,
            event_filter_params,
        ) = construct_event_filter_params(
            event_abi=abi,
            abi_codec=codec,
            address=self.filters.get("address"),
            argument_filters=self.filters,
            fromBlock=from_block,
            toBlock=to_block
        )

        # Call JSON-RPC API on your Ethereum node.
        logs: List[LogReceipt] = self.w3.eth.get_logs(
            filter_params=event_filter_params
        )

        # Convert raw binary data to Python proxy objects as described by ABI
        event_datas: List[EventData] = []
        for log in logs:
            # Convert raw JSON-RPC log result to human readable event by
            # using ABI data
            # More information how process_log works here
            # https://github.com/ethereum/web3.py/blob/fbaf1ad11b0c7fac09ba34baff2c256cffe0a148/web3/_utils/events.py#L200  # noqa
            event_data: EventData = get_event_data(
                abi_codec=codec,
                event_abi=abi,
                log_entry=log
            )

            event_datas.append(event_data)
        return event_datas

    def _retry_web3_call(
        self,
        fetch_event_logs: Callable,
        event_type: type[BaseContractEvent],
        start_block: int,
        end_block: int,
        retries: int,
        delay: float
    ) -> tuple[int, List[EventData]]:
        """Retry loop to throttle down block range.

        If our JSON-RPC server cannot serve all incoming `eth_getLogs`
        in a single request,
        we retry and throttle down block range for every retry.

        For example, Go Ethereum does not indicate what is an acceptable
        response size.
        It just fails on the server-side with a "context was cancelled"
        warning.

        Args:
            fetch_event_logs (Callable): A callable that triggers Ethereum
            JSON-RPC, as fetch_event_logs(event_type, start_block, end_block)
            event_type (type[BaseContractEvent]): Event type
            start_block (int): The initial start block of the block range
            end_block (int): The initial end block of the block range
            retries (int): How many times we retry
            delay (float): Time to sleep between retries

        Returns:
            tuple[int, List[EventData]]: End block, events
        """
        events: List[EventData]
        for i in range(retries):
            try:
                events: List[EventData] = fetch_event_logs(
                    event_type=event_type,
                    from_block=start_block,
                    to_block=end_block,
                )

                break

            except Exception:
                # Assume this is HTTPConnectionPool(host='localhost', port=8545):  # noqa
                # Read timed out. (read timeout=10)
                # from Go Ethereum. This translates to the error
                # "context was cancelled" on the server side:
                # https://github.com/ethereum/go-ethereum/issues/20426
                if i < retries - 1:
                    if end_block < 0:
                        continue
                    # Decrease the `eth_getBlocks` range
                    end_block = start_block + ((end_block - start_block) // 2)
                    # Let the JSON-RPC to recover e.g. from restart
                    time.sleep(delay)
                    continue
                else:
                    msg = ("Fetch event error! Out of retries!")
                    raise RelayerFetchEventOutOfRetries(msg)

        return end_block, events

    def _create_event_data_dto(self, event: EventData) -> Optional[EventDTO]:
        """Create EventDataDTO.

        Args:
            event (EventData): The event

        Returns:
            Optional[EventDTO]: EventDTO

        Raises:
            RelayerErrorBlockPending:
        """
        # Integer of the log index position in the block, null when
        # its pending
        idx = event["logIndex"]

        # We cannot avoid minor chain reorganisations, but
        # at least we must avoid blocks that are not mined yet
        if idx is None:
            msg = "Somehow tried to scan a pending block"
            raise RelayerErrorBlockPending(msg)

        block_number = event["blockNumber"]

        # Get UTC time when this event happened (block mined timestamp)
        # from our in-memory cache
        block_datetime: Optional[datetime] = self.get_block_timestamp(
            block_num=block_number,
        )

        if block_datetime is None:
            return

        return EventDTO(
            chain_id=self.chain_id,
            event_name=event.event,
            block_number=event.blockNumber,
            tx_hash=event.transactionHash.hex(),
            log_index=event.logIndex,
            block_datetime=block_datetime,
            data=EventDataDTO(
                from_=event.args.params['from'],
                to=event.args.params.to,
                chain_id_from=event.args.params.chainIdFrom,
                chain_id_to=event.args.params.chainIdTo,
                token_name=event.args.params.tokenName,
                amount=event.args.params.amount,
                nonce=event.args.params.nonce,
                signature_str=bytes_to_hex(event.args.params.signature),
                signature_bytes=event.args.params.signature,
                operation_hash_str=bytes_to_hex(event.args.operationHash),
                operation_hash_bytes=event.args.operationHash,
                block_step=event.args.blockStep,
            ),
        )
