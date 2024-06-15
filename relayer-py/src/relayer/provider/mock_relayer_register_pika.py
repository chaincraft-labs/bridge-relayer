"""Mock Provider that aims to simulate register events."""
from typing import Any, Callable
from src.relayer.interface.relayer import IRelayerRegister


class MockRelayerRegisterEvent(IRelayerRegister):
    """Mock RelayerRegisterEvent provider."""

    def register_event(self, event: bytes):
        raise NotImplementedError

    def read_events(self, callback: Callable[..., Any]):
        raise NotImplementedError
