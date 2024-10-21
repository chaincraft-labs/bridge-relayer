import asyncio
import os
import sys
from os.path import basename
from sys import argv
from textwrap import dedent
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.application.consume_events import ConsumeEvents  # noqa: E402
from src.relayer.provider.relayer_register_aio_pika import RelayerRegisterEvent  # noqa: E402
from src.relayer.provider.relayer_blockchain_web3 import RelayerBlockchainProvider  # noqa: E402
from src.relayer.provider.relayer_repository_leveldb import RelayerRepositoryProvider  # noqa: E402

async def consume(debug: bool = False) -> None:
    """Consume events tasks from queue."""
    log_level = 'debug' if debug else 'info'

    # providers (not instantiated)
    relayer_blockchain_provider = RelayerBlockchainProvider
    relayer_register_provider = RelayerRegisterEvent
    relayer_repository_provider = RelayerRepositoryProvider

    # app
    await ConsumeEvents(
        relayer_blockchain_provider=relayer_blockchain_provider,
        relayer_register_provider=relayer_register_provider,
        relayer_repository_provider=relayer_repository_provider,
        log_level=log_level,
    )()


class Parser:
    """Parser class."""

    def __init__(self):
        """Init."""
        self.exe = basename(argv[0])
        self.parser = ArgumentParser(
            formatter_class=RawDescriptionHelpFormatter,
            description="Event task listener.",
            epilog=dedent(f'''\
                examples:
                    
                  Watch events
                  
                    {self.exe} --watch
            ''')
        )

        self.parser.add_argument(
            '--watch', '-w',
            action='store_const',
            const=True,
            help='Watch messages')
        
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
                
        if args.watch:
            asyncio.run(consume(debug=args.debug))
        else:
            parser.parser.print_help()

    except Exception as exc:
        print(f'{exc}')