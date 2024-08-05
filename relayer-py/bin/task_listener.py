import os
import sys
from os.path import basename
from sys import argv
from textwrap import dedent
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
import time
from typing import Any, Optional


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.domain.relayer import EventDTO  # noqa: E402
from src.relayer.application.manage_event_from_blockchain import (  # noqa: E402
    ManageEventFromBlockchain,
)
from src.relayer.application.consume_event_task import (  # noqa: E402
    ConsumeEventTask,
)
from src.relayer.provider.relayer_register_pika import (  # noqa: E402
    RelayerRegisterEvent as _p_register,
)
from src.relayer.provider.relayer_blockchain_web3 import (  # noqa: E402
    RelayerBlockchainProvider as _p_blockchain,
)

def consume(debug: bool = False) -> None:
    """Consume events tasks from queue."""
    blockchain_provider = _p_blockchain()
    consumer_provider = _p_register()
    app = ConsumeEventTask(
        relayer_blockchain_provider=blockchain_provider,
        relayer_consumer_provider=consumer_provider,
    )
    app()


def send(
    number: int = 1,
    message: Optional[str] = None,
) -> None:
    """Register event to queue.

    Args:
        number (int, optional): A number of events to send. Defaults to 1.
        message (Optional[str], optional): A message. Defaults to None.
    """
    chain_id = 80002
    register_blockchain = _p_blockchain(debug=False)
    register_provider = _p_register(debug=False)
    
    app = ManageEventFromBlockchain(
        relayer_blockchain_provider=register_blockchain,
        relayer_register_provider=register_provider,
        chain_id=chain_id
    )

    for i in range(int(number)):
        if message is None:
            _message = "AttributeDict({'args': AttributeDict({'owner': '0x5a1C4Fb0AE5470B0a502b9395ff30E7292947c11'}), 'event': 'OwnerGet', 'logIndex': 0, 'transactionIndex': 0, 'transactionHash': HexBytes('0x0ab65baf4a54b4656a8747d86bdb46db51ad650cb2a27b3f8a2faea26ebe35b6'), 'address': '0x5816Eb4EAD3006AACbebFA01cE05d6BeE6ED75f4', 'blockHash': HexBytes('0x1458957cbb37c3769f3c2c634b07fd45f9d8608ef34c9e397d3cae7e8fa4347f'), 'blockNumber': 7669498})"
        else:
            _message = f"{message}_{i}"
        
        event_dto = EventDTO(name="TestEvent", data=_message)
        app._handle_event(event_dto=event_dto)

def callback(data: Any):
    print(f"handle message here !!! with data: {data}")
    print(f" [x] Received {data}")
    time.sleep(5)
    print(" [x] Done") 


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
                  Send events (for testing)
                  
                    {self.exe} --send
                    
                  Watch events
                  
                    {self.exe} --watch
            ''')
        )

        self.parser.add_argument(
            '--send', '-s',
            action='store_const',
            const=True,
            help='Send a message')
        
        self.parser.add_argument(
            '--message', '-m',
            action='store',
            help='A message')
        
        self.parser.add_argument(
            '--number', '-n',
            action='store',
            help='Number of message(s) to send')

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

        if args.send and args.number:
            message = None
            if args.message:
                message = args.message
            
            send(args.number, args.message)
            
        elif args.send:
            message = None
            if args.message:
                message = args.message
            send(message=message)
                
        elif args.watch:
            consume(debug=args.debug)
        else:
            parser.parser.print_help()

    except Exception as exc:
        print(f'{exc}')