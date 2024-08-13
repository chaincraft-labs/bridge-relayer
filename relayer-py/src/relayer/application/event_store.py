"""Magage event storage."""
from datetime import datetime
import time
from src.relayer.application import BaseApp
from src.relayer.interface.event_storage import IEventDataStore
from src.relayer.domain.event_store import (
    EventDataDTO,
    EventDatasDTO,
)


class StoreEventFromBlockchain(BaseApp):
    """Manage storage for events."""

    def __init__(
        self,
        event_datastore_provider: IEventDataStore,
        chain_id: int,
    ):
        """_summary_

        Args:
            event_datastore_provider (IEventDataStore): _description_
            chain_id (int): _description_

        Returns:
            _type_: _description_
        """
        self.chain_id: int = chain_id
        self.state = {}     # Events state
        self.last_save = 0  # How many second ago we saved the JSON file
        # configuration
        # self.fname = f"{chain_id}-events-scanner.json"
        # providers
        self.evt_store: IEventDataStore = event_datastore_provider

    # S T O R A G E
    def set_chain_id(self):
        """"""
        if self.chain_id not in self.state:
            self.state[self.chain_id] = {
                "last_scanned_block": 0,
                "blocks": {},
            }

    def open_or_init(self):
        """Init or restore the last scan state."""
        try:
            self.state = self.event_datastore.read()
            self.set_chain_id()
        
        except Exception as e:
            print("State starting from scratch")
            self.reset()

    def save_events(self):
        """Save events scanned."""
        self.evt_store.save()

    def reset(self):
        """Create initial state of nothing scanned."""
        self.state = {}
        self.set_chain_id()

    def get_last_scanned_block(self):
        """Get the number of the last block stored."""
        block = self.state[self.chain_id].get("last_scanned_block", 0)
        return block

    def delete_potentially_forked_block_data(self, after_block: int):
        """Purge old data in th e case of blockchain reorganisation.

        Args:
            after_block (int): _description_
        """
        if after_block > 0:
            self.evt_store.delete_data(since_block=after_block)

    def end_chunk(self, block_number: int, end_block: int):
        """
            Save at the end of each block, so we can resume 
            in the case of a crash or CTRL+C
            
        """
        # Next time the scanner is started we will resume from this block
        if end_block > block_number:
            self.state[self.chain_id]["last_scanned_block"] = block_number
        else:
            self.state[self.chain_id]["last_scanned_block"] = end_block

        # Save the database file for every minute
        if time.time() - self.last_save > 60:
            self.save()

    def delete_data(self, since_block):
        """Remove potentially reorganised blocks from the scan data."""
        for block_num in range(since_block, self.get_last_scanned_block()):
            if block_num in self.state[self.chain_id].get("blocks", {}):
                del self.state[self.chain_id]["blocks"][block_num]
    
    def process_event(
        self, 
        block_when: datetime, 
        event: EventDataDTO
    ) -> str:
        """Record event in database.

        Args:
            block_when (datetime.datetime): _description_
            event (EventData): _description_

        Returns:
            str: _description_
        """
        log_index = str(event.logIndex)
        block_number = str(event.blockNumber)
        txhash = event.transactionHash.hex()

        dto = {
            "event": event.event,
            "data": event["args"],
            "timestamp": block_when.isoformat(),
        }

        blocks = self.state[self.chain_id].get("blocks", {})

        if block_number not in blocks:
            blocks[block_number] = {}

        block = blocks[block_number]
        if txhash not in block:
            blocks[block_number][txhash] = {}

        blocks[block_number][txhash][log_index] = dto

        # Return a pointer that allows us to look up this event later 
        # if needed
        return f"{block_number}-{txhash}-{log_index}"

