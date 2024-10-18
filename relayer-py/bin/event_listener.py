from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
import asyncio
import os
from os.path import basename
import sys
from sys import argv
from textwrap import dedent

current_dir: str = os.path.dirname(os.path.abspath(__file__))
parent_dir: str = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.application.listen_events import ListenEvents  # noqa: E402
from src.relayer.provider.relayer_blockchain_web3 import RelayerBlockchainProvider  # noqa: E402
from src.relayer.provider.relayer_register_aio_pika import RelayerRegisterEvent  # noqa: E402
from src.relayer.provider.relayer_repository_leveldb import RelayerRepositoryProvider  # noqa: E402


async def app(chain_id: int, debug: bool = False) -> None:
    log_level = 'debug' if debug else 'info'
    # providers
    relayer_blockchain_provider = RelayerBlockchainProvider()
    relayer_register_provider = RelayerRegisterEvent()
    relayer_repository_provider = RelayerRepositoryProvider()

    # Call apps
    listener =  ListenEvents(
        chain_id=chain_id,
        relayer_blockchain_provider=relayer_blockchain_provider,
        relayer_register_provider=relayer_register_provider,
        relayer_repository_provider=relayer_repository_provider,
        log_level=log_level,
    )
    
    await listener(as_service=True, progress_bar=False)


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
            asyncio.run(app(chain_id=int(args.chain_id), debug=args.debug))

        else:
            print("[ 💔 ] chain_id is missing!\n")
            parser.parser.print_help()

    except Exception as exc:
        print(f'{exc}')
