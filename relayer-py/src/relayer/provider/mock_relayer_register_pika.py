"""Mock Provider that aims to simulate register events."""
from typing import Any, Callable
from src.relayer.domain.exception import (
    BridgeRelayerReadEventFailed, 
    BridgeRelayerRegisterEventFailed
)
from src.relayer.interface.relayer import IRelayerRegister


class MockRelayerRegisterEvent(IRelayerRegister):
    """Mock RelayerRegisterEvent provider."""

    def __init__(self, exception = None):
        # self.event = event
        # self.name = name
        self.exception = exception
        self.events = []
                
    def register_event(self, event: bytes):
        try:
            if self.exception:
                raise self.exception

        except Exception as e:
            raise BridgeRelayerRegisterEventFailed(e)

    def read_events(self, callback: Callable[..., Any]):
        try:
            for event in self.events:
                callback(event)

        except Exception as e:
            raise BridgeRelayerReadEventFailed(e)