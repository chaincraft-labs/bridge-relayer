"""Event Storage to file."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from hexbytes import HexBytes

from web3.datastructures import AttributeDict

from src.relayer.application import BaseApp
from src.relayer.application.base_logging import RelayerLogging
from src.relayer.domain.event import EventDataDTO, RelayerParamsDTO
from src.relayer.domain.exception import (
    EventDataStoreNoBlockToDelete, 
    EventDataStoreRegisterFailed, 
    EventDataStoreStateEmptyOrNotLoaded
)
from src.relayer.interface.event_storage import IEventDataStore
from src.utils.converter import hex_to_bytes


class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes) or isinstance(obj, bytes):
            return HexBytes(obj).hex()
        if isinstance(obj, AttributeDict) or isinstance(obj, Dict):
            return dict(obj)
        return super().default(obj)


class EventDataStoreToFile(RelayerLogging, BaseApp, IEventDataStore):
    """Provider for event state."""

    def __init__(self, log_level: str = "info"):
        """Event data store

        Args:
            log_level (str): The log level. Defaults to 'info'.
        """
        super().__init__(level=log_level)
        self.chain_id = 0
        self.fname = ""
        self.base_fname = "-events-scanner.json"
        self.base_task_fname = "events-operation.json"
        self.path = Path(__file__).parents[3] / "data"
        self.state = {}
        self.state_task = {}

    # -----------------------------------------------------------------
    #  Implemented functions
    # -----------------------------------------------------------------
    def set_chain_id(self, chain_id: int):
        """Set the chain id

        Args:
            chain_id (int): The chain id
        """
        self.chain_id = str(chain_id)
        self.fname = f"{chain_id}{self.base_fname}"
        self._read_events()

    def read_event_tasks(self) -> Dict[str, Any]:
        """Read event tasks from data storage.

        Returns:
            Dict[str, Any]: The event state
        """
        try:
            fname = self._get_task_file_path()
            self.state_task = json.load(open(fname, "rt"))
            
            self.logger.debug(
                f"{self.Emoji.info.value} "
                f"Open event tasks data store fname={fname}"
            )

        except (IOError, json.decoder.JSONDecodeError):
            self.state_task = {}
            self._commit_task()

        return self.state_task

    def get_event_task_status(
        self, 
        operation_hash: str, 
        event_name: str
    ) -> Optional[str]:
        """Get event task status.

        Args:
            operation_hash (str): The operation hash
            event_name (str): The event name

        Returns:
            Optional[str]: The event task status.
        """
        try:
            return self.state_task[operation_hash][event_name]["status"]
        except KeyError:
            return None


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
            "event": event.event_name,
            "params": event.data.params(),
            "operationHash": event.data.operation_hash_str,
            "blockStep": event.data.block_step,
            "timestamp": event.block_datetime.isoformat(),
        }

        self.logger.debug(
            f"{self.Emoji.info.value}"
            f"chain_id={self.chain_id} "
            f"operationHash={event.data.operation_hash_str} "
            f"dto={dto}"
        )

        blocks = self.state[str(self.chain_id)].get("blocks", {})

        if block_number not in blocks:
            blocks[block_number] = {}
        
        block = blocks[block_number]
        if txhash not in block:
            blocks[block_number][txhash] = {}

        blocks[block_number][txhash][log_index] = dto
        self.state[self.chain_id]['last_scanned_block'] = block_number

        self.logger.debug(
            f"{self.Emoji.info.value}chain_id={self.chain_id} "
            f"Event saved "
            f"event_key={event.block_number}-{event.tx_hash}-{event.log_index}"
        )

        if auto_commit:
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Commit events state."
            )
            self._commit()

    def save_event_task(
        self,
        chain_id: int,
        block_key: str,
        operation_hash: str,
        event_name: str,
        auto_commit: bool,
        status: str,
    ):
        """Save event task.

        Args:
            chain_id (int): The chain id
            block_key (str): the block key e.g: "block_number-tx_hash-log_index"
            operation_hash (str): The operation hash
            event_name (str): The event name
            auto_commit (bool): Commit state to data store.
            status (str): The status of the event.
        """
        # New operation hash
        if self.state_task.get(operation_hash) is None:
            self.state_task[operation_hash] = {}
           
        # New event name
        if self.state_task[operation_hash].get(event_name) is None:
            self.state_task[operation_hash][event_name] = {
                "chain_id": chain_id,
                "block_key": block_key,
                "status": status,
            }
        else: # update status
            self.state_task[operation_hash][event_name]["status"] = status

        if auto_commit:
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Commit task events state."
            )
            self._commit_task()

    def delete_event(
        self,
        current_block: int,
        block_to_delete: int,
        auto_commit: bool = True
    ):
        """Delete any data since this block was scanned.

        Purges any potential minor reorg data.

        Args:
            current_block: (int): The current block on chain
            block_to_delete (int): Number of blocks to delete
            auto_commit (bool): Commit state to data store. Default is True
        """
        try:
            last_block = int(next(reversed(self.state[self.chain_id]["blocks"].keys())))
        except (StopIteration, KeyError):
            raise EventDataStoreNoBlockToDelete("No block to delete, state empty")

        block_limit_to_delete = current_block - block_to_delete

        if last_block <= block_limit_to_delete:
            raise EventDataStoreNoBlockToDelete("No block to delete")

        self.logger.debug(
            f"{self.Emoji.info.value}chain_id={self.chain_id} "
            f"block_limit_to_delete={block_limit_to_delete}"
        )
        blocks_to_delete = []

        for block_num in reversed(self.state[self.chain_id]["blocks"].keys()):
            if int(block_num) < block_limit_to_delete:
                self.state[self.chain_id]['last_scanned_block'] = int(block_num)
                break

            blocks_to_delete.append(block_num)

        self.logger.debug(
            f"{self.Emoji.info.value}chain_id={self.chain_id} "
            f"block_to_delete={blocks_to_delete}"
        )

        for block_num in blocks_to_delete:
            del self.state[self.chain_id]["blocks"][str(block_num)]

        if auto_commit:
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Commit state after delete events"
            )
            self._commit()


    def get_last_scanned_block(self) -> int:
        """Get the last block stored

        Returns:
            int: The block number
        """
        try:
            last_scanned_block = self.state[self.chain_id]['last_scanned_block']
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"last_scanned_block={last_scanned_block}"
            )
            return int(last_scanned_block)

        except KeyError:
            raise EventDataStoreStateEmptyOrNotLoaded("State empty or not loaded!")

    def set_last_scanned_block(self, block_numer: int, auto_commit: bool = True):
        """Set the last scanned block

        Args:
            block_numer (int): The block number
            auto_commit (bool): Commit state to data store. Default is True
        """
        try:
            self.state[self.chain_id]['last_scanned_block'] = block_numer

            if auto_commit:
                self.logger.debug(
                    f"{self.Emoji.info.value}chain_id={self.chain_id} "
                    f"Commit state after delete events"
                )
                self._commit()
        except KeyError:
            raise EventDataStoreStateEmptyOrNotLoaded("State empty or not loaded!")
        
    def get_event(
        self, 
        chain_id: int, 
        event_key: str
    ) -> Optional[EventDataDTO]:
        """Get the event

        Args:
            chain_id (int): The chain id
            event_key (str): The event key

        Returns:
            Optional[EventDataDTO]: The event data DTO. None if not found
        """
        try:
            (block_num, tx_hash, log_idx) = event_key.split("-")
            data = self.state[str(chain_id)]['blocks'][block_num][tx_hash][log_idx]

            return EventDataDTO(
                chain_id=chain_id,
                event_name=data['event'],
                block_number=block_num,
                tx_hash=tx_hash,
                log_index=log_idx,
                block_datetime=data['timestamp'],
                data=RelayerParamsDTO(
                    from_=data['params']['from'],
                    to=data['params']['to'],
                    chain_id_from=data['params']['chainIdFrom'],
                    chain_id_to=data['params']['chainIdTo'],
                    token_name=data['params']['tokenName'],
                    amount=data['params']['amount'],
                    nonce=data['params']['nonce'],
                    signature_str=data['params']['signature'],
                    signature_bytes=hex_to_bytes(data['params']['signature']),
                    operation_hash_str=data['operationHash'],
                    operation_hash_bytes=hex_to_bytes(data['operationHash']),
                    block_step=data['blockStep'],
                )
            )
            
        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed creating event data: {event_key}. {e} ")
            return None

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
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Event {event_key} is not registered"
            )
            return False

    def set_event_as_registered(
        self, 
        event_key: str, 
        auto_commit: bool = True
    ):
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

            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Register event_key={event_key}"
            )

        except (KeyError, ValueError) as e:
            msg = (f'Unable to register event_key={event_key}. error={e}')
            self.logger.debug(
                f"{self.Emoji.fail.value}chain_id={self.chain_id} {msg}")
            raise EventDataStoreRegisterFailed(msg)

        if auto_commit:
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Commit state after delete events"
            )
            self._commit()


    # -----------------------------------------------------------------
    #  Internal functions
    # -----------------------------------------------------------------
    def _read_events(self) -> Dict[str, Any]:
        """Read events from data storage.

        Returns:
            Dict[str, Any]: The event state
        """
        try:
            fname = self._get_file_path()
            self.state = json.load(open(fname, "rt"))
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Open events data store fname={fname}"
            )
            self._init()

        except (IOError, json.decoder.JSONDecodeError):
            self.state = {}
            self._init()
            self._commit()

        return self.state
    
    def _commit(self):
        """Commit events (state) to a data storage (file).
        
            Create file name and directory if not exist
        """
        fname: Path = self._get_file_path()
        fname.parent.mkdir(parents=True, exist_ok=True)

        with open(fname, "wt") as f:
            json.dump(self.state, f, cls=HexJsonEncoder)

    def _commit_task(self):
        """Commit events task (state) to a data storage (file).
        
            Create file name and directory if not exist
        """
        task_fname: Path = self._get_task_file_path()
        task_fname.parent.mkdir(parents=True, exist_ok=True)

        with open(task_fname, "wt") as f:
            json.dump(self.state_task, f, cls=HexJsonEncoder)

    def _get_file_path(self) -> Path:
        """Get the file name + pathname.

        Returns:
            Path: The full path where the data store is located
        """
        return self.path / self.fname
    
    def _get_task_file_path(self) -> Path:
        """Get the file name operation + pathname.

        Returns:
            Path: The full path where the data store is located
        """
        return self.path / self.base_task_fname

    def _init(self):
        """Init the state structure."""

        if self.chain_id not in self.state:

            self.state[self.chain_id] = {
                "last_scanned_block": 0,
                "blocks": {},
            }
            self.logger.debug(
                f"{self.Emoji.info.value}chain_id={self.chain_id} "
                f"Init state: {self.state}"
            )
