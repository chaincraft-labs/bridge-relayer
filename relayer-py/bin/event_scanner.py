"""A stateful event scanner for Ethereum-based blockchains using web3.py.

With the stateful mechanism, you can do one batch scan or incremental scans,
where events are added wherever the scanner left off.
"""
import datetime
import os
import sys
import time
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Callable, List, Dict, Any
import json
from hexbytes import HexBytes

# We use tqdm library to render a nice progress bar in the console
# https://pypi.org/project/tqdm/
from tqdm import tqdm
from web3 import Web3
from web3.contract.base_contract import BaseContractEvent
from web3.contract.contract import Contract
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from web3.middleware.geth_poa import geth_poa_middleware
from web3.providers.rpc import HTTPProvider
from eth_abi.codec import ABICodec
# Currently this method is not exposed over official web3 API,
# but we need it to construct eth_getLogs parameters
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from web3.types import (
    ABIEvent,
    BlockData,
    EventData,
    LogReceipt,
    Timestamp,
)

current_dir: str = os.path.dirname(os.path.abspath(__file__))
parent_dir: str = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.config import get_blockchain_config, get_abi
from src.utils.converter import to_bytes

logger = logging.getLogger(__name__)


class EventScannerState(ABC):
    """Application state that remembers what blocks we have scanned in 
    the case of crash.
    """

    @abstractmethod
    def get_last_scanned_block(self) -> int:
        """Number of the last block we have scanned on the previous cycle.

        Returns:
            int: 0 if no blocks scanned yet
        """

    @abstractmethod
    def start_chunk(self, block_number: int, chunk_size: int):
        """Scanner is about to ask data of multiple blocks over JSON-RPC.

        Start a database session if needed.

        Args:
            block_number (int): _description_
            chunk_size (int): _description_
        """

    @abstractmethod
    def end_chunk(self, block_number: int):
        """Scanner finished a number of blocks.

        Persistent any data in your state now.

        Args:
            block_number (int): _description_
        """

    @abstractmethod
    def process_event(
        self, 
        block_when: datetime.datetime, 
        event: EventData
    ) -> object:
        """Process incoming events.

        This function takes raw events from Web3, transforms them to your 
        application internal format, then saves them in a database or some 
        other state.

        Args:
            block_when (datetime.datetime): When this block was mined
            event (EventData): Symbolic dictionary of the event data

        Returns:
            object: Internal state structure that is the result of event transformation.
        """

    @abstractmethod
    def delete_data(self, since_block: int) -> int:
        """Delete any data since this block was scanned.

        Purges any potential minor reorg data.

        Args:
            since_block (int): _description_

        Raises:
            TypeError: _description_

        Returns:
            int: _description_
        """


class EventScanner:
    """Scan blockchain for events and try not to abuse JSON-RPC API too much.

    Can be used for real-time scans, as it detects minor chain reorganisation 
    and rescans.
    Unlike the easy web3.contract.Contract, this scanner can scan events from 
    multiple contracts at once.
    For example, you can get all transfers from all tokens in the same scan.

    You *should* disable the default `http_retry_request_middleware` on 
    your provider for Web3,
    because it cannot correctly throttle and decrease the `eth_getLogs` 
    block number range.
    """

    NUM_BLOCKS_RESCAN_FOR_FORKS = 10

    def __init__(
        self,
        chain_id: int,
        w3: Web3, 
        contract: Contract, 
        state: EventScannerState, 
        events: List[type[BaseContractEvent]], 
        filters: Dict[str, Any],
        max_chunk_scan_size: int = 10000, 
        max_request_retries: int = 30, 
        request_retry_seconds: float = 3.0
    ):
        """_summary_

        Args:
            chain_id (int): _description_
            w3 (Web3): _description_
            contract (Contract): _description_
            state (EventScannerState): _description_
            events (List[type[BaseContractEvent]]): List of web3 Event we scan
            filters (Dict[str, Any]): Filters passed to get_logs
            max_chunk_scan_size (int, optional): JSON-RPC API limit in the 
                number of blocks we query. (Recommendation: 10,000 for mainnet, 
                500,000 for testnets). Defaults to 10000.
            max_request_retries (int, optional): How many times we try to 
                reattempt a failed JSON-RPC call. Defaults to 30.
            request_retry_seconds (float, optional): Delay between failed 
                requests to let JSON-RPC server to recover. Defaults to 3.0.
        """
        self.logger = logger
        self.contract = contract
        self.w3 = w3
        self.state = state
        self.events = events
        self.filters = filters

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = 10  # 12 s/block = 120 seconds period
        self.max_scan_chunk_size = max_chunk_scan_size
        self.max_request_retries = max_request_retries
        self.request_retry_seconds = request_retry_seconds

        # Factor how fast we increase the chunk size if results are found
        # # (slow down scan after starting to get hits)
        self.chunk_size_decrease = 0.5

        # Factor how fast we increase chunk size if no results found
        self.chunk_size_increase = 2.0
        
        self.config = get_blockchain_config(chain_id)
        self.account = self.w3.eth.account.from_key(self.config.pk)

    @property
    def address(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self.account.address

    def get_block_timestamp(self, block_num) -> Optional[datetime.datetime]:
        """Get Ethereum block timestamp

        Args:
            block_num (_type_): _description_

        Returns:
            Optional[datetime.datetime]: _description_
        """
        try:
            block_info: BlockData = self.w3.eth.get_block(block_num)
            last_time: Timestamp = block_info["timestamp"] # type: ignore
            # return datetime.datetime.utcfromtimestamp(last_time)
            return datetime.datetime.fromtimestamp(
                last_time, tz=datetime.timezone.utc)
        
        except (BlockNotFound, ValueError):
            # Block was not mined yet,
            # minor chain reorganisation?
            return None
        
    def get_suggested_scan_start_block(self):
        """Get where we should start to scan for new token events.

        If there are no prior scans, start from block 1.
        Otherwise, start from the last end block minus ten blocks.
            see: NUM_BLOCKS_RESCAN_FOR_FORKS with default is 10
        We rescan the last ten scanned blocks in the case there were forks to 
        avoid misaccounting due to minor single block works 
        (happens once in an hour in Ethereum).
        These heuristics could be made more robust, but this is for the sake 
        of simple reference implementation.

        Returns:
            _type_: _description_
        """
        end_block = self.get_last_scanned_block()
        if end_block:
            return max(1, end_block - self.NUM_BLOCKS_RESCAN_FOR_FORKS)
        return 1

    def get_suggested_scan_end_block(self):
        """Get the last mined block on Ethereum chain we are following.

        Returns:
            _type_: _description_
        """

        # Do not scan all the way to the final block, as this
        # block might not be mined yet
        # Before last block number
        return self.w3.eth.block_number - 1

    def get_last_scanned_block(self) -> int:
        """_summary_

        Returns:
            int: _description_
        """
        return self.state.get_last_scanned_block()

    def delete_potentially_forked_block_data(self, after_block: int):
        """Purge old data in the case of blockchain reorganisation.

        Args:
            after_block (int): _description_
        """
        self.state.delete_data(after_block)

    def get_block_when(
        self, 
        block_num: int, 
        block_timestamps: Dict[int, Any]
    ) -> Optional[datetime.datetime]:
        """_summary_

        Args:
            block_num (int): _description_
            block_timestamps (Dict[int, Any]): _description_

        Returns:
            _type_: _description_
        """
        if block_num not in block_timestamps:
            block_timestamps[block_num] = self.get_block_timestamp(block_num)
        return block_timestamps[block_num]

    def scan_chunk(
        self, 
        start_block, 
        end_block
    ) -> Tuple[int, datetime.datetime, list]:
        """Read and process events between two block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC 
        server pukes out.

        Args:
            start_block (_type_): _description_
            end_block (_type_): _description_

        Returns:
            Tuple[int, datetime.datetime, list]: actual end block number, 
            when this block was mined, processed events
        """
        block_timestamps = {}
        get_block_timestamp = self.get_block_timestamp

        # Cache block timestamps to reduce some RPC overhead
        # Real solution might include smarter models around block
        def get_block_when(block_num):
            if block_num not in block_timestamps:
                block_timestamps[block_num] = get_block_timestamp(block_num)
            return block_timestamps[block_num]

        all_processed = []

        for event_type in self.events:
            # Callable that takes care of the underlying web3 call
            def _fetch_events(_start_block, _end_block) -> List[EventData]:
                return _fetch_events_for_all_contracts(
                    self.w3,
                    event_type,
                    self.filters,
                    from_block=_start_block,
                    to_block=_end_block
                )

            # Do `n` retries on `eth_getLogs`,
            # throttle down block range if needed
            (
                end_block, 
                events,
            ) = _retry_web3_call(
                    _fetch_events,
                    start_block=start_block,
                    end_block=end_block,
                    retries=self.max_request_retries,
                    delay=self.request_retry_seconds,
                )

            for evt in events:
                # Integer of the log index position in the block, null when 
                # its pending
                idx = evt["logIndex"]

                # We cannot avoid minor chain reorganisations, but
                # at least we must avoid blocks that are not mined yet
                assert idx is not None, "Somehow tried to scan a pending block"

                block_number = evt["blockNumber"]

                # Get UTC time when this event happened (block mined timestamp)
                # from our in-memory cache
                block_when: Optional[datetime.datetime] = \
                    get_block_when(block_number)
                # print(f"block_when : {block_when}")

                logger.debug(
                    f"Processing event {evt['event']}, "
                    f"block: {evt['blockNumber']} count: {evt['blockNumber']}"
                )
                
                if block_when is not None and evt is not None:
                    processed = self.state.process_event(
                        block_when, evt)
                    
                    all_processed.append(processed)

        end_block_timestamp = get_block_when(end_block)
        return end_block, end_block_timestamp, all_processed

    def estimate_next_chunk_size(
        self, 
        current_chuck_size: float, 
        event_found_count: int
    ):
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

    def scan(
        self, 
        start_block: int, 
        end_block: int, 
        start_chunk_size: int = 20, 
        progress_callback: Optional[Callable] = None
    ) -> Tuple[list, int]:
        """Perform a token balances scan.

        Assumes all balances in the database are valid before start_block 
            (no forks sneaked in).

        Args:
            start_block (int): start_block: The first block included in the scan
            end_block (int): The last block included in the scan
            start_chunk_size (int, optional): How many blocks we try to fetch 
                over JSON-RPC on the first attempt. Defaults to 20.
            progress_callback (Optional[Callable], optional): If this is an 
                UI application, update the progress of the scan. Defaults to None.

        Returns:
            Tuple[list, int]: All processed events, number of chunks used
        """

        assert start_block <= end_block

        current_block = start_block

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        last_scan_duration = last_logs_found = 0
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        all_processed = []

        while current_block <= end_block:

            # self.state.start_chunk(current_block, chunk_size)

            # Print some diagnostics to logs to try to fiddle with real 
            # world JSON-RPC API performance
            estimated_end_block = current_block + chunk_size
            logger.debug(
                f"Scanning token transfers for blocks: "
                f"{current_block} - {estimated_end_block}, chunk size "
                f"{chunk_size}, last chunk scan took {last_scan_duration}, "
                f"last logs found {last_logs_found}"
            )

            start = time.time()
            (
                actual_end_block, 
                end_block_timestamp, 
                new_entries
            ) = self.scan_chunk(current_block, estimated_end_block)

            # Where does our current chunk scan ends - are we out of chain yet?
            current_end = actual_end_block
            last_scan_duration = time.time() - start
            all_processed += new_entries

            # Print progress bar
            if progress_callback is not None:
                progress_callback(
                    start_block, 
                    end_block, 
                    current_block, 
                    end_block_timestamp, 
                    chunk_size, 
                    len(new_entries)
                )

            # Try to guess how many blocks to fetch over `eth_getLogs` 
            # API next time
            chunk_size = self.estimate_next_chunk_size(
                chunk_size, len(new_entries))

            # Set where the next chunk starts
            current_block = current_end + 1
            total_chunks_scanned += 1
            self.state.end_chunk(current_end)

        return all_processed, total_chunks_scanned


def _retry_web3_call(
    func: Callable, 
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
        func (Callable): A callable that triggers Ethereum JSON-RPC, 
            as func(start_block, end_block)
        start_block (int): The initial start block of the block range
        end_block (int): The initial start block of the block range
        retries (int): How many times we retry
        delay (float): Time to sleep between retries

    Returns:
        tuple[int, List[EventData]]: _description_
    """
    
    events: List[EventData]
    
    for i in range(retries):
        try:
            events: List[EventData] = func(start_block, end_block)
            break
            # return end_block, func(start_block, end_block)
            # return end_block, events
        
        except Exception as e:
            # Assume this is HTTPConnectionPool(host='localhost', port=8545): Read timed out. (read timeout=10)
            # from Go Ethereum. This translates to the error "context was cancelled" on the server side:
            # https://github.com/ethereum/go-ethereum/issues/20426
            if i < retries - 1:
                # Give some more verbose info than the default middleware
                logger.warning(
                    f"Retrying events for block range {start_block} - {end_block} ({end_block-start_block}) failed with {e} , retrying in {delay} seconds")
                # Decrease the `eth_getBlocks` range
                end_block = start_block + ((end_block - start_block) // 2)
                # Let the JSON-RPC to recover e.g. from restart
                time.sleep(delay)
                continue
            else:
                logger.warning("Out of retries")
                raise

    return end_block, events

def _fetch_events_for_all_contracts(
    w3: Web3,
    event_type: type[BaseContractEvent],
    argument_filters: Dict[str, Any],
    from_block: int,
    to_block: int
) -> List[EventData]:
    """Get events using eth_getLogs API.

    This method is detached from any contract instance.

    This is a stateless method, as opposed to create_filter.
    It can be safely called against nodes which do not provide 
    `eth_newFilter` API, like Infura.

    Args:
        w3 (Web3): _description_
        event_type (type[BaseContractEvent]): _description_
        argument_filters (Dict[str, Any]): _description_
        from_block (int): _description_
        to_block (int): _description_

    Raises:
        TypeError: _description_

    Returns:
        List[EventData]: _description_
    """
    if from_block is None:
        raise TypeError("Missing mandatory keyword argument to get_logs: from_block")

    # Currently no way to poke this using a public web3.py API.
    # This will return raw underlying ABI JSON object for the event
    abi: ABIEvent = event_type._get_event_abi()

    # Depending on the Solidity version used to compile
    # the contract that uses the ABI,
    # it might have Solidity ABI encoding v1 or v2.
    # We just assume the default that you set on Web3 object here.
    # More information here https://eth-abi.readthedocs.io/en/latest/index.html
    codec: ABICodec = w3.codec

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
        abi,
        codec,
        address=argument_filters.get("address"),
        argument_filters=argument_filters,
        fromBlock=from_block,
        toBlock=to_block
    )

    logger.debug(
        f"Querying eth_getLogs with the following parameters: "
        f"{event_filter_params}"
    )

    # Call JSON-RPC API on your Ethereum node.
    # get_logs() returns raw AttributedDict entries
    logs: List[LogReceipt] = w3.eth.get_logs(event_filter_params)

    # Convert raw binary data to Python proxy objects as described by ABI
    all_events: List[EventData] = []
    for log in logs:
        # Convert raw JSON-RPC log result to human readable event by using ABI data
        # More information how process_log works here
        # https://github.com/ethereum/web3.py/blob/fbaf1ad11b0c7fac09ba34baff2c256cffe0a148/web3/_utils/events.py#L200
        evt: EventData = get_event_data(codec, abi, log)
        # Note: This was originally yield,
        # but deferring the timeout exception caused the throttle logic not to work
        all_events.append(evt)
    return all_events


if __name__ == "__main__":
    # Simple demo that scans all the token transfers of RCC token (11k).
    # The demo supports persistent state by using a JSON file.
    # You will need an Ethereum node for this.
    # Running this script will consume around 20k JSON-RPC calls.
    # With locally running Geth, the script takes 10 minutes.
    # The resulting JSON state file is 2.9 MB.

    # # We use tqdm library to render a nice progress bar in the console
    # # https://pypi.org/project/tqdm/
    # from tqdm import tqdm

    class HexJsonEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, HexBytes) or isinstance(obj, bytes):
                return obj.hex()
            if isinstance(obj, AttributeDict):
                return dict(obj)
            return super().default(obj)

    class JSONifiedState(EventScannerState):
        """Store the state of scanned blocks and all events.

        All state is an in-memory dict.
        Simple load/store massive JSON on start up.
        """

        def __init__(self):
            # self.state = None
            self.state = {}
            self.fname = "test-state.json"
            # How many second ago we saved the JSON file
            self.last_save = 0

        def reset(self):
            """Create initial state of nothing scanned."""
            self.state = {
                "last_scanned_block": 0,
                "blocks": {},
            }

        def restore(self):
            """Restore the last scan state from a file."""
            try:
                self.state = json.load(open(self.fname, "rt"))
                print(f"Restored the state, previously {self.state['last_scanned_block']} blocks have been scanned")
            
            except (IOError, json.decoder.JSONDecodeError):
                print("State starting from scratch")
                self.reset()

        def save(self):
            """Save everything we have scanned so far in a file."""
            with open(self.fname, "wt") as f:
                json.dump(self.state, f, cls=HexJsonEncoder)

            self.last_save = time.time()

        #
        # EventScannerState methods implemented below
        #

        def get_last_scanned_block(self):
            """The number of the last block we have stored."""
            return self.state["last_scanned_block"]

        def delete_data(self, since_block):
            """Remove potentially reorganised blocks from the scan data."""
            for block_num in range(since_block, self.get_last_scanned_block()):
                if block_num in self.state["blocks"]:
                    del self.state["blocks"][block_num]

        def start_chunk(self, block_number, chunk_size):
            pass

        def end_chunk(self, block_number):
            """Save at the end of each block, so we can resume in the case of a crash or CTRL+C"""
            # Next time the scanner is started we will resume from this block
            self.state["last_scanned_block"] = block_number

            # Save the database file for every minute
            if time.time() - self.last_save > 60:
                self.save()

        def process_event(
            self, 
            block_when: datetime.datetime, 
            event: EventData
        ) -> str:
            """Record event in database.

            Args:
                block_when (datetime.datetime): _description_
                event (EventData): _description_

            Returns:
                str: _description_
            """
            # Events are keyed by their transaction hash and log index
            # One transaction may contain multiple events
            # and each one of those gets their own log index

            event_name = event.event                    # type: ignore ; "Transfer"
            log_index = event.logIndex                  # type: ignore ; Log index within the block 
            txhash = event.transactionHash.hex()        # type: ignore ; Transaction hash
            block_number = event.blockNumber            # type: ignore

            # Convert ERC-20 Transfer event to our internal format
            args = event["args"]
            # _transfer = {
            #     "from": args["from"],
            #     "to": args.to,
            #     "value": args.value,
            #     "timestamp": block_when.isoformat(),
            # }
            dto = {
                "event": event_name,
                "data": args,
                "timestamp": block_when.isoformat(),
            }
            # print()
            # print(f"log_index    : {log_index}")
            # print(f"txhash       : {txhash}")
            # print(f"block_number : {block_number}")
            # print(dto)
            # print()

            # Create empty dict as the block that contains all transactions by txhash
            if block_number not in self.state["blocks"]:
                self.state["blocks"][block_number] = {}

            block = self.state["blocks"][block_number]
            if txhash not in block:
                # We have not yet recorded any transfers in this transaction
                # (One transaction may contain multiple events if executed by a smart contract).
                # Create a tx entry that contains all events by a log index
                self.state["blocks"][block_number][txhash] = {}

            # Record event in database as bytes
            self.state["blocks"][block_number][txhash][log_index] = dto

            # Return a pointer that allows us to look up this event later if needed
            return f"{block_number}-{txhash}-{log_index}"

    def run():

        if len(sys.argv) < 2:
            print("Usage: eventscanner.py <chain_id>")
            sys.exit(1)

        chain_id = int(sys.argv[1])
        config = get_blockchain_config(chain_id)
        abi = get_abi(chain_id)

        # Enable logs to the stdout.
        # DEBUG is very verbose level
        logging.basicConfig(level=logging.INFO)

        rpc_url = f"{config.rpc_url}{config.project_id}"
        provider = HTTPProvider(rpc_url)

        # Remove the default JSON-RPC retry middleware
        # as it correctly cannot handle eth_getLogs block range
        # throttle down.
        
        # provider.middlewares[0].clear()
        provider.middlewares.clear() # type: ignore

        w3: Web3 = Web3(provider)
        
        # if config.client == "middleware":
        #     w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        # Prepare stub ERC-20 contract object
        # abi = json.loads(ABI)
        # contract = w3.eth.contract(abi=abi)
        contract = w3.eth.contract(
            Web3.to_checksum_address(config.smart_contract_address),  
            abi=abi
        )

        events: List[type[BaseContractEvent]] = [
            contract.events.OperationCreated,
            contract.events.FeesLockedConfirmed,
            contract.events.FeesLockedAndDepositConfirmed,
            contract.events.FeesDeposited,
            contract.events.FeesDepositConfirmed,
            contract.events.OperationFinalized,
        ]

        # Restore/create our persistent state
        state = JSONifiedState()
        state.restore()

        scanner = EventScanner(
            chain_id=chain_id,
            w3=w3,
            contract=contract,
            state=state,
            events=events,
            filters={},
            # How many maximum blocks at the time we request from JSON-RPC
            # and we are unlikely to exceed the response size limit of the JSON-RPC server
            max_chunk_scan_size=10000
        )
        
        title_length = 20
        print(f"{"chain_id":<{title_length}} : {chain_id}")
        print(f"{"Account address":<{title_length}} : {scanner.address}")
        print(f"{"Contract address":<{title_length}} : {config.smart_contract_address}")
        print(f"{"genesis block":<{title_length}} : {config.genesis_block}")

        # Assume we might have scanned the blocks all the way to the last Ethereum block
        # that mined a few seconds before the previous scan run ended.
        # Because there might have been a minor Ethereum chain reorganisations
        # since the last scan ended, we need to discard
        # the last few blocks from the previous scan results.
        chain_reorg_safety_blocks = 10
        scanner.delete_potentially_forked_block_data(
            state.get_last_scanned_block() - chain_reorg_safety_blocks
        )

        # Scan from [last block scanned] - [latest ethereum block]
        # Note that our chain reorg safety blocks cannot go negative
        start_block = max(
            state.get_last_scanned_block() - chain_reorg_safety_blocks,
            config.genesis_block,
        )
        print(f"{"start_block":<{title_length}} : {start_block}")
        
        end_block = scanner.get_suggested_scan_end_block()
        print(f"{"end_block":<{title_length}} : {end_block}")
        
        blocks_to_scan = end_block - start_block
        print(f"{"blocks_to_scan":<{title_length}} : {blocks_to_scan}")
        
        # Render a progress bar in the console
        start = time.time()
        with tqdm(total=blocks_to_scan) as progress_bar:
            
            def _update_progress(
                start_block: int, 
                end_block: int, 
                current_block: int, 
                current_block_timestamp: datetime.datetime, 
                chunk_size: int, 
                events_count: int,
            ):
                if current_block_timestamp:
                    formatted_time = current_block_timestamp.strftime("%d-%m-%Y")
                else:
                    formatted_time = "no block time available"
                    
                progress_bar.set_description(
                    f"Current block: {current_block} ({formatted_time}), "
                    f"blocks in a scan batch: {chunk_size}, events "
                    f"processed in a batch {events_count}")
                progress_bar.update(chunk_size)

            # Run the scan
            result, total_chunks_scanned = scanner.scan(
                start_block, end_block, progress_callback=_update_progress)

        state.save()
        duration = time.time() - start
        print(
            f"Scanned total {len(result)} events, in {duration} "
            f"seconds, total {total_chunks_scanned} chunk scans performed"
        )

    run()