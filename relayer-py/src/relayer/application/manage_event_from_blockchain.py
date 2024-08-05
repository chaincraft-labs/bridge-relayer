"""Application for the bridge relayer."""
import sys
from typing import List

from src.relayer.application import BaseApp
from src.relayer.application.register_event import RegisterEvent
from src.relayer.domain.config import (
    RelayerRegisterConfigDTO,
    RelayerBlockchainConfigDTO,
)
from src.utils.converter import to_bytes
from src.relayer.interface.relayer import (
    IRelayerBlockchain,
    IRelayerRegister,
)
from src.relayer.domain.relayer import (
    RegisterEventResult,
    EventDTO,
)
from src.relayer.config.config import (
    get_blockchain_config,
    get_register_config,
)


class ManageEventFromBlockchain(BaseApp):
    """Manage blockchain event listener."""

    def __init__(
        self,
        relayer_blockchain_provider: IRelayerBlockchain,
        relayer_register_provider: IRelayerRegister,
        chain_id: int,
        event_filters: List[str],
        verbose: bool = True
    ) -> None:
        """Init blockchain event listener instance.

        Args:
            relayer_blockchain_event (IRelayerBlockchainEvent):
                The relayer blockchain provider
            relayer_blockchain_config (RelayerBlockchainConfigDTO):
                The relayer blockchain configuration
            chain_id (int): The chain id
            event_filters (List): The list of event to manage
            verbose (bool, optional): Verbose mode. Defaults to True.
        """
        self.register_config: RelayerRegisterConfigDTO = get_register_config()
        self.rb_provider: IRelayerBlockchain = relayer_blockchain_provider
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.chain_id: int = chain_id
        self.event_filters: List[str] = event_filters
        self.verbose: bool = verbose

    def __call__(self) -> None:
        """Listen event main function."""
        try:
            self.listen_events()
        except KeyboardInterrupt:
            self.print_log("emark", "Keyboard Interrupt")
            sys.exit()
        except Exception as e:
            self.print_log("fail", f"Error={e}")
            self()

    def listen_events(self, poll_interval: int = 2) -> None:
        """The blockchain event listener.

        Args:
            poll_interval int: The loop poll interval in second. Default is 2
        """
        self.rb_provider.set_chain_id(self.chain_id)
        self.rb_provider.set_event_filter(self.event_filters)
        config: RelayerBlockchainConfigDTO = get_blockchain_config(self.chain_id)

        self.print_log("main", "Running the event listener ...")
        self.print_log("emark", f"chain_id        : {self.chain_id}")
        self.print_log("emark", f"contract address: {config.smart_contract_address}")
        self.print_log("emark", f"listen to events: {self.event_filters}")

        self.rb_provider.listen_events(
            callback=self._handle_event,
            poll_interval=poll_interval,
        )

    def _handle_event(self, event_dto: EventDTO) -> RegisterEventResult:
        """Handle the event received from blockchain.

        Args:
            event_dto (EventDTO): The event DTO

        Return:
            RegisterEventResult: The event registered result
        """
        event_dto_to_byte: bytes = self._convert_data_to_bytes(event=event_dto)
        self.print_log("receiveEvent", f"Received event: {event_dto}")
        app = RegisterEvent(
            relayer_register_provider=self.rr_provider,
            verbose=self.verbose
        )
        return app(event=event_dto_to_byte)

    def _convert_data_to_bytes(self, event: EventDTO) -> bytes:
        """Convert attribut data to bytes.

        Args:
            event (EventDTO): The event DTO

        Returns:
            bytes: The event DTO as bytes format
        """
        return to_bytes(data=event)
