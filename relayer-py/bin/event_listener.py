from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
import os
from os.path import basename
import sys
from sys import argv
from textwrap import dedent


current_dir: str = os.path.dirname(os.path.abspath(__file__))
parent_dir: str = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.application.app import App  # noqa: E402
from src.relayer.provider.relayer_blockchain_web3 import (  # noqa: E402
    RelayerBlockchainProvider as p_relayer_blockchain,
)
from src.relayer.provider.relayer_register_pika import (  # noqa: E402
    RelayerRegisterEvent as p_relayer_register,
)


def app(chain_id: int, debug: bool = False) -> None:
    # providers
    rb_provider = p_relayer_blockchain()
    rr_provider = p_relayer_register()

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
        relayer_blockchain_provider=rb_provider,
        relayer_register_provider=rr_provider
    )

    # Listen events
    apps(chain_id=chain_id, event_filters=event_filters)


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
