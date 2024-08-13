from pathlib import Path
from typing import Any, Dict, List
from src.relayer.domain.event import EventDataDTO
from src.relayer.interface.event_storage import IEventDataStore


class MockEventDataStore(IEventDataStore):
    """"""
    def __init__(self, chain_id: int):
        """Init EventDataStoreToFile instance.

        Mock with chain_id = 123

        Args:
            chain_id (int): The chain id
        """
        self.chain_id = str(chain_id)
        self.fname = f"{chain_id}-events-scanner.json"
        self.path = Path(__file__).parents[3] / "data"
        self.state = {
            "123": {
                "last_scanned_block": 14840,
                "blocks": {
                    "14836": {
                        "0x846462eb461c8a7b49558f19e8ae21e0e9ac1ea004467ce54459f90eeda445cd": {
                            "0": {
                                "event": "OperationCreated",
                                "data": {
                                    "operationHash": b"~\x87wm\xba\xf8)L\xcf3\xd88\xd0\x0ex\x1e\xe6\xf6\xf4\xc1/\xb4-\x12g\x000\x89\xbb\x99\x87\xb4",
                                    "params": {
                                        "from": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                        "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                        "chainIdFrom": 440,
                                        "chainIdTo": 1337,
                                        "tokenName": "allfeat",
                                        "amount": 1000000000000000,
                                        "nonce": 3,
                                        "signature": b"\xbf$\xe3f\xb1\xb2\x832U@ \xd0\xf7\xdc\x8a\xda\x16\xb0Qup\xe6\x82,J\xaa\x00\x05s\xb7icT@\xe2\xe7\xfa\x16\xf7+\xfc\xf8\xaan%\xe4|:Hv(\x7f\xb9\x94T)HK\xc1\xc7%\xf6\x94\x84\x1c",
                                    },
                                    "blockStep": 14836,
                                },
                                "timestamp": "2024-08-07T15:09:14.607810",
                            }
                        }
                    },
                    "14840": {
                        "0x33cd4af61bd844e5641e5d8de1234385c3988f40e4d6f72e91f63130553f1962": {
                            "0": {
                                "event": "OperationCreated",
                                "data": {
                                    "operationHash": b"\xbb1@\xd3lU\x8a\xe7\xc7\xfd2o\xd3\xc4\x94\x84\x0c\xf3~eN'`\x03x]\x8f\xbd\xad\x02\xb8\xa1",
                                    "params": {
                                        "from": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                        "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
                                        "chainIdFrom": 440,
                                        "chainIdTo": 1337,
                                        "tokenName": "allfeat",
                                        "amount": 1000000000000000,
                                        "nonce": 4,
                                        "signature": b"\x8b\xa2\xd0;\xc2\x89\xb9f\xfb\xf5SZ\xca\x19>`cfT\xe58kvW\xb54f\xfeU\xcd\xb8\x1dB\xed\x1f1J\x86\x16\x0e\xf6(\xf5\xdb\xd4\x07qJ\x9b:I\x10\x0b\xd0Pq\x9aQ\xc8w\xd0\x9fn\xcd\x1c",
                                    },
                                    "blockStep": 14840,
                                },
                                "timestamp": "2024-08-07T15:09:14.607810",
                            }
                        }
                    },
                },
            }
        }
        
    def read_events(self) -> Dict[str, Any]:
        """"""
        return self.state

    def save_events(self, events: List[EventDataDTO], auto_commit: bool = True):
        pass

    def delete_event(self, since_block: int, auto_commit: bool = True):
        pass

    def get_last_scanned_block(self) -> int:
        last_scanned_block = self.state[self.chain_id]['last_scanned_block']
        return last_scanned_block

    def set_last_scanned_block(self, block_numer: int):
        pass

    def is_event_stored(self, event_key: str) -> bool:
        pass

    def is_event_registered(self, event_key: str) -> bool:
        pass

    def set_event_as_registered(self, event_key: str):
        pass

    def save_event(self, event: EventDataDTO, auto_commit: bool = True):
        pass

