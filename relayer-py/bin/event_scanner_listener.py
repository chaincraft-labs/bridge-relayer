from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
import os
from os.path import basename
import sys
from sys import argv
from textwrap import dedent


current_dir: str = os.path.dirname(os.path.abspath(__file__))
parent_dir: str = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# from src.relayer.application.app import App  # noqa: E402
from src.relayer.application.manage_event_from_blockchain_v2 import ManageEventFromBlockchain as App  # noqa: E402
from src.relayer.provider.relayer_blockchain_web3_v2 import (  # noqa: E402
    RelayerBlockchainProvider,
)
from src.relayer.provider.relayer_register_pika import (  # noqa: E402
    RelayerRegisterEvent,
)
from src.relayer.provider.relayer_event_storage import EventDataStoreToFile  # noqa: E402


def app(chain_id: int, debug: bool = False) -> None:
    # providers
    rb_provider = RelayerBlockchainProvider()
    rr_provider = RelayerRegisterEvent()
    es_provider = EventDataStoreToFile(chain_id=chain_id)

    # Set event filters
    event_filters = [
        "OperationCreated",
        "FeesLockedConfirmed",
        "FeesLockedAndDepositConfirmed",
        "FeesDeposited",
        "FeesDepositConfirmed",
        "OperationFinalized"
    ]

    # Call apps
    apps = App(
        chain_id=chain_id,
        event_filters=event_filters,
        relayer_blockchain_provider=rb_provider,
        relayer_register_provider=rr_provider,
        event_datastore_provider=es_provider,
        
    )

    # Scan events
    # apps(as_service=False)
    # apps(as_service=True, progress_bar=False, verbose=False)
    apps(as_service=True, progress_bar=False, verbose=True)


class Parser:
    """Parser class."""

    def __init__(self) -> None:
        """Init."""
        self.exe = basename(argv[0])
        self.parser = ArgumentParser(
            formatter_class=RawDescriptionHelpFormatter,
            description="Blockchain event listener.",
            epilog=dedent(f'''\
                examples:
                    Run the listener

                    {self.exe} --chain_id 80002

            ''')
        )

        self.parser.add_argument(
            '--chain_id', '-i',
            action='store',
            help='A chain_id number. e.g: 80002')

        self.parser.add_argument(
            '--debug', '-d',
            action="store_true",
            help='enable debug')

    def __call__(self) -> Namespace:
        """Parse arguments."""
        args: Namespace = self.parser.parse_args()
        return args


if __name__ == "__main__":
    try:
        parser = Parser()
        args: Namespace = parser()

        if args.chain_id:
            app(chain_id=int(args.chain_id), debug=args.debug)

        else:
            print("[ 💔 ] chain_id is missing!\n")
            parser.parser.print_help()

    except Exception as exc:
        print(f'{exc}')
