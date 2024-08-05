"""Application for the bridge relayer."""
from src.relayer.application import BaseApp
from src.relayer.domain.exception import BridgeRelayerRegisterEventFailed
from src.relayer.interface.relayer import IRelayerRegister
from src.relayer.domain.relayer import RegisterEventResult


class RegisterEvent(BaseApp):
    """Bridge relayer register event."""

    def __init__(
        self,
        relayer_register_provider: IRelayerRegister,
        verbose: bool = True,
    ) -> None:
        """Init the relayer register.

        Args:
            relayer_register_provider (IRelayerRegister): The register provider
        """
        self.rr_provider: IRelayerRegister = relayer_register_provider
        self.verbose: bool = verbose

    def __call__(self, event: bytes) -> RegisterEventResult:
        """Register an event.

        Args:
            event (EventDTO): An eventDTO instance

        Return:
            RegisterEventResult: The event registered result
        """
        result = RegisterEventResult()

        self.print_log("info", f"Registering event : {event}")
        
        try:
            self.rr_provider.register_event(event=event)
            result.ok = True
        except BridgeRelayerRegisterEventFailed as e:
            result.err = str(e)
        return result
