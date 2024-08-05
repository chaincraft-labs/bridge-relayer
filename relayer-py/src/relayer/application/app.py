"""Application for the bridge relayer."""
from typing import List

from src.relayer.application.manage_event_from_blockchain import (
    ManageEventFromBlockchain
)
from src.relayer.interface.relayer import (
    IRelayerBlockchain,
    IRelayerRegister,
)


class App:
    """Blockchain Bridge Relayer application."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        verbose: bool = True,
    ) -> None:
        """Init Blockchain Bridge Relayer instance.

        Args:
            relayer_blockchain_config (IRelayerBLockchainConfig):
                The relayer blockchain provider
            relayer_blockchain_event (IRelayerBlockchainEvent):
                The relayer blockchain configuration
            verbose (bool, optional): Verbose mode. Defaults to True.
        """
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.verbose: bool = verbose

    def __call__(self, chain_id: int, event_filters: List[str]) -> None:
        """Listen event main function.

        Args:
            chain_id (int): The blockchain id
            event_filters (list): The events to listen
        """
        # The blockchain event listener
        app = ManageEventFromBlockchain(
            relayer_blockchain_provider=self.rb_provider,
            relayer_register_provider=self.rr_provider,
            chain_id=chain_id,
            event_filters=event_filters,
            verbose=self.verbose,
        )

        # Start the listener
        app()
