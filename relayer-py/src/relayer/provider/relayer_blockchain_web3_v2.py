"""
Provider that aims to listen events from blockchain and execute smart contracts.

The library used is web3.py

https://web3py.readthedocs.io/
"""
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional

from eth_account.signers.local import LocalAccount
from eth_abi.codec import ABICodec
from web3 import HTTPProvider, Web3
from web3.contract.base_contract import BaseContractEvent
from web3.contract.contract import Contract
from web3.exceptions import BlockNotFound, ABIEventFunctionNotFound
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3.types import (
    BlockData,
    ABIEvent,
    EventData,
    LogReceipt,
    Timestamp,
)

from src.relayer.interface.relayer_blockchain_scanner import IRelayerBlockchain
from src.relayer.domain.exception import (
    BridgeRelayerErrorBlockPending,
    BridgeRelayerEventsNotFound,
    BridgeRelayerFetchEventOutOfRetries,
)
from src.relayer.domain.relayer import (
    BridgeTaskDTO,
    BridgeTaskResult,
)
from src.relayer.domain.event import (
    EventDataDTO,
    EventDatasDTO,
)
from src.relayer.config.config import get_blockchain_config, get_abi
from src.relayer.application.base_logging import RelayerLogging



class RelayerBlockchainProvider(RelayerLogging, IRelayerBlockchain):
    """Relayer blockchain provider."""

    def __init__(
        self,
        min_scan_chunk_size: int = 10,
        max_scan_chunk_size: int = 10000, 
        max_request_retries: int = 30, 
        request_retry_seconds: float = 3.0,
        num_blocks_rescan_for_forks = 10,
        chunk_size_decrease: float = 0.5,
        chunk_size_increase: float = 2.0,

    ) -> None:
        """Init RelayerBlockchainProvider.

        Args:
            debug (bool, optional): Enable/disable logging. Defaults to False.
        """
        super().__init__()
        self.chain_id: int
        self.events: List[type[BaseContractEvent]] = []
        self.filters: Dict[str, Any] = {}
        self.relay_blockchain_config: Dict[str, Any] = {}
        self.w3: Web3
        self.w3_contract: Contract

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = min_scan_chunk_size  # 12 s/block = 120 seconds period
        self.max_scan_chunk_size = max_scan_chunk_size
        self.max_request_retries = max_request_retries
        self.request_retry_seconds = request_retry_seconds
        self.num_blocks_rescan_for_forks = num_blocks_rescan_for_forks

        # Factor how fast we increase the chunk size if results are found
        # (slow down scan after starting to get hits)
        self.chunk_size_decrease = chunk_size_decrease

        # Factor how fast we increase chunk size if no results found
        self.chunk_size_increase = chunk_size_increase
        
    # -------------------------------------------------------------
    # Implemented functions
    # -------------------------------------------------------------
    def connect_client(self, chain_id: int) -> None:
        """Connect to the web3 client.

        Args:
            chain_id (int): The chain id
        """
        self.chain_id = chain_id
        self.logger.debug(f"chain_id={chain_id}")

        self.relay_blockchain_config = get_blockchain_config(self.chain_id)
        self.logger.debug(f"config={self.relay_blockchain_config}")
        
        self.w3: Web3 = self._set_provider()
        self.w3_contract: Contract = self._set_contract()

    def set_event_filter(self, events: List[str]):
        """Set the event filter.

        Args:
            events (List[str]): The events list to filter.
        """
        try:
            self.logger.debug(f"Set events={events}")
            
            self.events = [self.w3_contract.events[event] for event in events]
            self.event_filter = events
            self.logger.debug(f"events={self.events}")

        except ABIEventFunctionNotFound as e:
            msg = f"Fail set events! Error={e}"
            self.logger.error(msg)
            raise BridgeRelayerEventsNotFound(msg)

    def get_block_number(self) -> int:
        raise NotImplementedError

    def listen_events(self, callback: Callable[..., Any], poll_interval: int) -> Any:
        raise NotImplementedError

    async def call_contract_func(self, bridge_task_dto: BridgeTaskDTO) -> BridgeTaskResult:
        raise NotImplementedError
    
    def client_version(self) -> str:
        """Get the client version

        Returns:
            str: the client version
        """
        try:
            client_version = self.w3.client_version
            self.logger.debug(f"Get client_version={client_version}")
            return client_version
        except Exception as e:
            self.logger.error(f"Fail getting client version! Error={e}")
            # raise BridgeRelayerBlockchainNotConnected(e)
            raise

    def get_account_address(self) -> str:
        """Get the account address

        Returns:
            str: The account address
        """
        pk = self.relay_blockchain_config.pk
        account: LocalAccount = self.w3.eth.account.from_key(pk)
        return account.address
        

    # -----------------------------------------------------------------
    # Internal functions
    # -----------------------------------------------------------------
    def _set_provider(self) -> Web3:
        """Set the web3 provider.

        Returns:
            Web3: A provider instance
        """
        rpc_url = (
            f"{self.relay_blockchain_config.rpc_url}"
            f"{self.relay_blockchain_config.project_id}"
        )
        self.logger.debug(f'rpc_url={rpc_url}')
        
        provider = HTTPProvider(endpoint_uri=rpc_url)
        provider.middlewares.clear() # type: ignore
        self.logger.debug(f'provider={provider}')
        
        w3 = Web3(provider)

        self.logger.debug("set web3 instance")
        
        return w3
    
    def _set_contract(self) -> Contract:
        """Set the web3 contrat instance.

        Returns:
            Contract: A contract instance.
        """
        w3_contract = self.w3.eth.contract(
            Web3.to_checksum_address(
                self.relay_blockchain_config.smart_contract_address
            ),
            abi=get_abi(self.chain_id)
        )
        self.logger.debug("set web3 contract instance")

        return w3_contract

    def get_suggested_scan_end_block(self) -> int:
        """Get the last mined block on Ethereum chain we are following.

            Do not scan all the way to the final block, as this
            block might not be mined yet before last block number

        Returns:
            int: The suggested block number
        """
        return self.w3.eth.block_number - 1

    def get_block_timestamp(self, block_num) -> Optional[datetime]:
        """Get Ethereum block timestamp

        Args:
            block_num (_type_): _description_

        Returns:
            Optional[datetime]: _description_
        """
        try:
            block_info: BlockData = self.w3.eth.get_block(
                block_identifier=block_num)
            last_time: Timestamp = block_info["timestamp"]

            return datetime.fromtimestamp(timestamp=last_time, tz=timezone.utc)
        
        except (BlockNotFound, ValueError):
            # Block was not mined yet,
            # minor chain reorganisation?
            return None

    def get_block_when(
        self, 
        block_num: int, 
        block_timestamps: Dict[int, Any]
    ) -> Optional[datetime]:
        """_summary_

        Args:
            block_num (int): _description_
            block_timestamps (Dict[int, Any]): _description_

        Returns:
            _type_: _description_
        """
        if block_num not in block_timestamps:
            block_timestamps[block_num] = self.get_block_timestamp(
                block_num=block_num)
            
        return block_timestamps[block_num]

    def estimate_next_chunk_size(
        self, 
        current_chuck_size: float, 
        event_found_count: int
    ) -> int:
        """Try to figure out optimal chunk size

        Our scanner might need to scan the whole blockchain for all events

        * We want to minimize API calls over empty blocks
        * We want to make sure that one scan chunk does not try to process too 
            many entries once, as we try to control commit buffer size and 
            potentially asynchronous busy loop
        * Do not overload node serving JSON-RPC API by asking data for too 
            many events at a time

        Currently Ethereum JSON-API does not have an API to tell when a first 
        event occurred in a blockchain and our heuristics try to accelerate 
        block fetching (chunk size) until we see the first event.

        These heuristics exponentially increase the scan chunk size depending 
        on if we are seeing events or not.
        When any transfers are encountered, we are back to scanning only a few 
        blocks at a time.
        It does not make sense to do a full chain scan starting from block 1, 
        doing one JSON-RPC call per 20 blocks.

        Args:
            current_chuck_size (float): _description_
            event_found_count (int): _description_

        Returns:
            _type_: _description_
        """

        if event_found_count > 0:
            # When we encounter first events, reset the chunk size window
            current_chuck_size = self.min_scan_chunk_size
        else:
            current_chuck_size *= self.chunk_size_increase

        current_chuck_size = max(self.min_scan_chunk_size, current_chuck_size)
        current_chuck_size = min(self.max_scan_chunk_size, current_chuck_size)
        return int(current_chuck_size)

    def fetch_event_logs(
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
        self.logger.debug(f"_get_event_abi: abi={abi}")

        # Depending on the Solidity version used to compile
        # the contract that uses the ABI,
        # it might have Solidity ABI encoding v1 or v2.
        # We just assume the default that you set on Web3 object here.
        # More information here https://eth-abi.readthedocs.io/en/latest/index.html
        codec: ABICodec = self.w3.codec

        # Here we need to poke a bit into Web3 internals, as this
        # functionality is not exposed by default.
        # Construct JSON-RPC raw filter presentation based on human readable Python descriptions
        # Namely, convert event names to their keccak signatures
        # More information here:
        # https://github.com/ethereum/web3.py/blob/e176ce0793dafdd0573acc8d4b76425b6eb604ca/web3/_utils/filters.py#L71
        
        # e.g: event_filter_params
        # {
        #   'topics': ['0x2089bed5ec297eb42b3bbdbff2a65a604959bd7c9799781313f1f6c62f8ae333'], 
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

        self.logger.debug(
            f"Querying eth_getLogs with the following parameters: "
            f"{event_filter_params}"
        )

        # Call JSON-RPC API on your Ethereum node.
        logs: List[LogReceipt] = self.w3.eth.get_logs(
            filter_params=event_filter_params)
        
        self.logger.debug(f"w3.eth.get_logs: logs={logs}")

        # Convert raw binary data to Python proxy objects as described by ABI
        event_datas: List[EventData] = []
        for log in logs:
            # Convert raw JSON-RPC log result to human readable event by using ABI data
            # More information how process_log works here
            # https://github.com/ethereum/web3.py/blob/fbaf1ad11b0c7fac09ba34baff2c256cffe0a148/web3/_utils/events.py#L200
            event_data: EventData = get_event_data(
                abi_codec=codec, 
                event_abi=abi, 
                log_entry=log
            )
            # Note: This was originally yield,
            # but deferring the timeout exception caused the throttle logic not to work
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
        """A custom retry loop to throttle down block range.

        If our JSON-RPC server cannot serve all incoming `eth_getLogs` 
        in a single request,
        we retry and throttle down block range for every retry.

        For example, Go Ethereum does not indicate what is an acceptable 
        response size.
        It just fails on the server-side with a "context was cancelled" warning.

        Args:
            fetch_event_logs (Callable): A callable that triggers Ethereum JSON-RPC, 
                as fetch_event_logs(event_type, start_block, end_block)
            start_block (int): The initial start block of the block range
            end_block (int): The initial end block of the block range
            retries (int): How many times we retry
            delay (float): Time to sleep between retries

        Returns:
            tuple[int, List[EventData]]: _description_
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
            
            except Exception as e:
                # Assume this is HTTPConnectionPool(host='localhost', port=8545): 
                # Read timed out. (read timeout=10)
                # from Go Ethereum. This translates to the error 
                # "context was cancelled" on the server side:
                # https://github.com/ethereum/go-ethereum/issues/20426
                if i < retries - 1:
                    # Give some more verbose info than the default middleware
                    self.logger.warning(
                        f"Retrying events for block range {start_block} "
                        f"- {end_block} ({end_block-start_block}) failed with "
                        f"{e} , retrying in {delay} seconds"
                    )

                    # Decrease the `eth_getBlocks` range
                    end_block = start_block + ((end_block - start_block) // 2)
                    # Let the JSON-RPC to recover e.g. from restart
                    time.sleep(delay)
                    continue
                else:
                    msg = "Fetch event error! Out of retries!"
                    self.logger.warning(msg)
                    raise BridgeRelayerFetchEventOutOfRetries(msg)

        return end_block, events

    def scan(
        self, 
        start_block: int, 
        end_block: int,
    ) -> EventDatasDTO:
        """Read and process events between two block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC 
        server pukes out.

        Args:
            start_block (int): The first block to scan
            end_block (int): The last block to scan

        Returns:
            EventDatasDTO: Events, end block, end block timestamp 
        """
        block_timestamps = {}
        # event_data_keys: List[str] = []
        event_datas_dto: List[EventDataDTO] = []
        new_end_block: int = end_block
        end_block_timestamp: Optional[datetime] = None

        for event_type in self.events:
            # Do `n` retries on `eth_getLogs`,
            # throttle down block range if needed
            # new_end_block: int
            # events: List[EventData]

            (
                new_end_block, 
                event_datas,
            ) = self._retry_web3_call(
                fetch_event_logs=self.fetch_event_logs,
                event_type=event_type,
                start_block=start_block,
                end_block=end_block,
                retries=self.max_request_retries,
                delay=self.request_retry_seconds,
            )

            for event in event_datas:
                if event is None:
                    continue

                # Integer of the log index position in the block, null when 
                # its pending
                idx = event["logIndex"]

                # We cannot avoid minor chain reorganisations, but
                # at least we must avoid blocks that are not mined yet
                if idx is None:
                    msg = "Somehow tried to scan a pending block"
                    raise BridgeRelayerErrorBlockPending(msg)

                block_number = event["blockNumber"]

                # Get UTC time when this event happened (block mined timestamp)
                # from our in-memory cache
                block_datetime: Optional[datetime] = self.get_block_when(
                    block_num=block_number, 
                    block_timestamps=block_timestamps,
                )

                if block_datetime is None:
                    continue

                self.logger.debug(
                    f"Processing event {event['event']}, "
                    f"block: {event['blockNumber']} count: {event['blockNumber']}"
                )

                # data_event_key = f"{event.blockNumber}-{event.transactionHash.hex()}-{event.logIndex}"
                # event_data_keys.append(data_event_key)

                event_data_dto = EventDataDTO(
                    block_number=event.blockNumber,
                    tx_hash=event.transactionHash.hex(),
                    log_index=event.logIndex,
                    event=event,
                    block_datetime=block_datetime,
                )
                event_datas_dto.append(event_data_dto)

        end_block_timestamp: Optional[datetime] = self.get_block_when(
            block_num=new_end_block,
            block_timestamps=block_timestamps
        )

        self.logger.debug(
            f"new_end_block={new_end_block} "
            f"end_block_timestamp={end_block_timestamp}"
        )

        return EventDatasDTO(
            event_datas=event_datas_dto,
            # event_data_keys=event_data_keys,
            end_block=new_end_block,
            end_block_timestamp=end_block_timestamp
        )
