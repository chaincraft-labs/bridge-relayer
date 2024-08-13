"""Event Storage to file."""

from typing import List
import json
from pathlib import Path
from typing import Any, Dict
from hexbytes import HexBytes

from web3.datastructures import AttributeDict

from src.relayer.domain.event import (
    EventDataDTO,
)
from src.relayer.interface.event_storage import IEventDataStore
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.domain.exception import EventDataStoreRegisterFailed


class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes) or isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, AttributeDict) or isinstance(obj, Dict):
            return dict(obj)
        return super().default(obj)


class EventDataStoreToFile(RelayerLogging, IEventDataStore):
    """Provider for event state."""

    def __init__(self, chain_id: int):
        """Init EventDataStoreToFile instance.

        Args:
            chain_id (int): The chain id
        """
        super().__init__()
        self.chain_id = str(chain_id)
        self.fname = f"{chain_id}-events-scanner.json"
        self.path = Path(__file__).parents[3] / "data"
        self.state = {}

    # -----------------------------------------------------------------
    #  Implemented functions
    # -----------------------------------------------------------------
    def read_events(self) -> Dict[str, Any]:
        """Read events from data storage.

        Returns:
            Dict[str, Any]: The event state
        """
        try:
            fname = self.get_file_path()
            self.state = json.load(open(fname, "rt"))
            self.logger.debug(f"Open data store {fname}")
            self.init()
        
        except (IOError, json.decoder.JSONDecodeError):
            self.state = {}
            self.init()
            self.commit()

        return self.state
    
    def commit(self):
        """Commit events (state) to a data storage (file).
        
            Create file name and directory if not exist
        """
        fname: Path = self.get_file_path()
        fname.parent.mkdir(parents=True, exist_ok=True)

        with open(fname, "wt") as f:
            json.dump(self.state, f, cls=HexJsonEncoder)

    def save_events(self, events: List[EventDataDTO], auto_commit: bool = True):
        """Save incoming events.

        Args:
            event (List[EventDataDTO]): A collection of event datas
            auto_commit (bool): Commit state to data store. Default is True
        """
        self.logger.debug(f"Saving events: {len(events)}")
        for event in events:
            self.save_event(event=event, auto_commit=auto_commit)

        if auto_commit:
            self.logger.debug("Commit state after save events")
            self.commit()

    def delete_event(self, since_block: int, auto_commit: bool = True):
        """Delete any data since this block was scanned.

        Purges any potential minor reorg data.

        Args:
            since_block (int): BLock limit to delete data
            auto_commit (bool): Commit state to data store. Default is True
        """
        self.logger.debug(f"Delete events back to block {since_block}")

        try:
            last_block = next(reversed(self.state[self.chain_id]["blocks"].keys()))
        except StopIteration:
            last_block = 0
        
        block_limit_to_delete = int(last_block) - since_block
        self.logger.debug(f"Block limit {block_limit_to_delete}")

        blocks_to_delete = []

        for block_num in reversed(self.state[self.chain_id]["blocks"].keys()):
            if int(block_num) <= block_limit_to_delete:
                self.state[self.chain_id]['last_scanned_block'] = int(block_num)
                break

            blocks_to_delete.append(block_num)

        if not blocks_to_delete:
            self.logger.debug(f"No block to delete {blocks_to_delete}")
            return
        
        self.logger.debug(f"Block to delete {blocks_to_delete}")

        for block_num in blocks_to_delete:
            del self.state[self.chain_id]["blocks"][str(block_num)]

        if auto_commit:
            self.logger.debug("Commit state after delete events")
            self.commit()

    def get_last_scanned_block(self) -> int:
        """Get the last block stored

        Returns:
            int: The block number
        """
        last_scanned_block = self.state[self.chain_id]['last_scanned_block']
        self.logger.debug(f"last_scanned_block={last_scanned_block}")
        return last_scanned_block
    
    def set_last_scanned_block(self, block_numer: int):
        """Set the last scanned block

        Args:
            block_numer (int): The block number
        """
        self.state[self.chain_id]['last_scanned_block'] = block_numer
        self.logger.debug(f"set last_scanned_block={block_numer}")

    def is_event_stored(self, event_key: str) -> bool:
        """Check if the event has already been stored.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"

        Returns:
            bool: True if the event has been stored.
        """
        try:
            (block_num, tx_hash, log_idx) = event_key.split("-")
            self.state[self.chain_id]['blocks'][block_num][tx_hash][log_idx]
            return True
        except (KeyError, ValueError):
            return False
        
    def is_event_registered(self, event_key: str) -> bool:
        """Check if the event has already been registered.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"

        Returns:
            bool: True if the event has been registered.
        """
        try:
            blocks = self.state[self.chain_id]['blocks']
            (block_num, tx_hash, log_idx) = event_key.split("-")
            blocks[block_num][tx_hash][log_idx]['handled']
            return True
        except (KeyError, ValueError):
            return False

    def set_event_as_registered(self, event_key: str, auto_commit: bool = False):
        """Set the event as registered.

            Once an event has been scanned it has to be registered to be 
            handled.

        Args:
            event_key (str): The event key
                e.g: "block_number-tx_hash-log_index"
        """
        try:
            blocks = self.state[self.chain_id]['blocks']
            (block_num, tx_hash, log_idx) = event_key.split("-")
            blocks[block_num][tx_hash][log_idx].update(
                {'handled': 'registered'}
            )

            self.logger.debug(f"Register event {event_key}")
            
        except (KeyError, ValueError) as e:
            msg = f'Unable to register event_key={event_key}. Error={e}'
            self.logger.error(msg)
            raise EventDataStoreRegisterFailed(msg)
        
        if auto_commit:
            self.logger.debug("Commit state after delete events")
            self.commit()

    def save_event(self, event: EventDataDTO, auto_commit: bool = True):
        """Save incoming event.

        Args:
            event (EventDataDTO): An event data
            auto_commit (bool): Commit state to data store. Default is True
        """
        log_index = str(event.log_index)
        block_number = str(event.block_number)
        txhash = event.tx_hash

        dto = {
            "event": str(event),
            "data": event.event["args"],
            "timestamp": event.block_datetime.isoformat(),
        }
        self.logger.debug(f"set event dto: {dto}")

        blocks = self.state[self.chain_id].get("blocks", {})

        if block_number not in blocks:
            blocks[block_number] = {}

        block = blocks[block_number]
        if txhash not in block:
            blocks[block_number][txhash] = {}

        blocks[block_number][txhash][log_index] = dto
        self.state[self.chain_id]['last_scanned_block'] = int(block_number)
        self.logger.debug(
            f"Event saved: {event.block_number}-{event.tx_hash}-{event.log_index}")
        
        if auto_commit:
            self.logger.debug("Commit state after save events")
            self.commit()
    # -----------------------------------------------------------------
    #  Internal functions
    # -----------------------------------------------------------------
    

    def get_file_path(self) -> Path:
        """Get the file name + pathname.

        Returns:
            Path: The full path where the data store is located
        """
        return self.path / self.fname

    def init(self):
        """Init the state structure."""

        if self.chain_id not in self.state:
            
            self.state[self.chain_id] = {
                "last_scanned_block": 0,
                "blocks": {},
            }
            self.logger.debug(f"Init state: {self.state}")
