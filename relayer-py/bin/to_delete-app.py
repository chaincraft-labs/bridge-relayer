import os
import json
import asyncio

import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os.path import basename
from sys import argv
from textwrap import dedent

from dotenv import load_dotenv
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware.geth_poa import async_geth_poa_middleware

# Load env
load_dotenv()

# Load abi
with open('abi.json', 'r') as f:
    abis = json.loads(f.read())
    abi = abis["v3"]

HTTPS_RPC_URL = os.environ["80002_HTTPS_RPC_URL"]
PROJECT_ID = os.environ["80002_PROJECT_ID"]
SMART_CONTRACT_ADDRESS = os.environ["80002_SMART_CONTRACT_ADDRESS"]


class BLockchainEventListener:

    def __init__(self):
        self.events = asyncio.Queue()
    
    async def watch_events(self):
        print("Watch event ...")
        while True:
            print(f"Queue size => {self.events.qsize()}")
            e = await self.events.get()
            print(f"after get")
            print(f"event => {e}")
            self.events.task_done()
        
    async def handle_event(self, event):
        print("put event in queue")
        await self.events.put(event)
        print(f"Queue size => {self.events.qsize()}")
        # and whatever
 
    async def log_loop(self, event_filter, poll_interval):
        while True:
            for event in await event_filter.get_new_entries():
                await self.handle_event(event)
            await asyncio.sleep(poll_interval)


    async def client_version(self, w3):
        print(await w3.client_version)


    def start(self):
        print("Start listen events ...")
        
        # instantiate Web3 instance
        w3 = AsyncWeb3(AsyncHTTPProvider(f"{HTTPS_RPC_URL}{PROJECT_ID}"))
        w3.middleware_onion.inject(async_geth_poa_middleware, layer=0)
        # Instantiate contract for event log
        w3_contract = w3.eth.contract(
            AsyncWeb3.to_checksum_address(SMART_CONTRACT_ADDRESS),
            abi=json.dumps(abi)
        )

        # Confirm that the connection succeeded
        asyncio.run(self.client_version(w3))
        
        # Define event filters
        event_filter_ownerset = asyncio.run(
            w3_contract.events.OwnerSet().create_filter(fromBlock='latest') # type: ignore
        )
        event_filter_ownerget = asyncio.run(
            w3_contract.events.OwnerGet().create_filter(fromBlock='latest') # type: ignore
        )
        
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                asyncio.gather(
                    self.log_loop(event_filter_ownerset, 2),
                    self.log_loop(event_filter_ownerget, 2)
                )
            )
        finally:
            loop.close()


class Parser:
    """Parser class."""

    def __init__(self):
        """Init."""
        self.exe = basename(argv[0])
        self.parser = ArgumentParser(
            formatter_class=RawDescriptionHelpFormatter,
            description="BLockchain event listener tool.",
            epilog=dedent(f'''\
                examples:
                  Run the listener
                  
                    {self.exe} --run
                    
                  Watch events
                  
                    {self.exe} --watch
            ''')
        )

        self.parser.add_argument(
            '--run', '-r',
            action='store_const',
            const=True,
            help='Run the listener')

        self.parser.add_argument(
            '--watch', '-w',
            action='store_const',
            const=True,
            help='Watch the events')

    def __call__(self):
        """Parse arguments."""
        args = self.parser.parse_args()
        return args



def main():
    """"""
    try:
        args = Parser()()
        
        bel = BLockchainEventListener()

        if args.run:
            bel.start()
                
        elif args.watch:
            asyncio.run(bel.watch_events())
            
        else:
            sys.stdout.write(f"Invalid arguments: {argv[1:]}!")

    except Exception as exc:
        print(f'{exc}')

if __name__ == '__main__':
    main()