# Blockchain bridge relayer (POC)

A centralized blockchain bridge relayer that aims to connect two blockchains (Proof Of Concept: POC)

## Get started

### Installation

#### Clone the directory

```bash
git clone https://github.com/AlyraButerin/bridge-relay-poc
cd bridge-relay-poc
```

#### Install dependencies

This project uses `poetry` to manage dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install poetry==1.8.3
poetry install 
```

#### Environment files

There are 3 files at root level.

- .env
- .env.config.dev
- .env.config.prod

Set your private key for PK_*
Set your project id for PROJECT_ID_* (see: https://dashboard.alchemy.com)

1. copy sample.env to .env
2. copy sample.env.config.dev to .env.config.dev
3. update .env.config.dev values
4. copy sample.env.config.prod to .env.config.prod
5. update .env.config.prod values

#### Configuration and abi files

There are 4 files at the location: src/config

- abi_dev.json
- abi.json
- bridge_relayer_config_dev.toml
- bridge_relayer_config.toml

1. edit **bridge_relayer_config_dev.toml** and **bridge_relayer_config.toml**
   1. set RelayerBridge smart contract's address
2. edit **abi.json** and **abi_dev.json**
   1. add the abi for each chain_id

### Run RabbitMQ server

For the POC we'll use the docker version as described in the official documentation [Installing RabbitMQ
](https://www.rabbitmq.com/docs/download)

#### Open the 1st terminal and run the command

```bash
# latest RabbitMQ 3.13
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management
```

#### Access to the management GUI

http://localhost:15672/

Default username and password of `guest` / `guest`

#### Create Queues

Through the RabbitMQ web GUI, go to:

1. Queues and Streams
2. Add a new queue
3. Name
   1. bridge.relayer.dev
   2. bridge.relayer.prod
4. Add queue

> ❗Queue name are set in
>
> `config/bridge_relayer_config_dev.toml`
> `config/bridge_relayer_config.toml`


### Run the bridge relayer

You need to run 2 event listeners and 1 event task listener.

*Example:*
2 event listeners, one for each blockchain

- chain id 441 (Allfeat)
- chain id 11155111 (Sepolia)

> Note: Add --debug to enable the debug

#### Run the event listener on 441

In a new terminal execute:

```bash
cd relayer-py
poetry run python bin/event_listener.py --chain_id 441
```

#### Run the event listener on 11155111

In a new terminal execute:

```bash
poetry run python bin/event_listener.py --chain_id 11155111
```

#### Run the event task listener

You need to run at least 1 listener, but you can increase the amount of listener as needed.

In a new terminal execute:

```bash
poetry run python bin/task_listener.py --watch
```

## Geth

```bash

# Start a geth node
geth geth --datadir . --dev --http --dev.period 12



geth HARDHAT_NETWORK=allfeat_local node scripts/as_bridge.js --deploy gethAllfeatLocal

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --deposit-fees gethAllfeatLocal

geth HARDHAT_NETWORK=allfeat_local node scripts/as_bridge.js --deploy gethAllfeatLocal

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --deploy gethAllfeatLocal


geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --deposit-token allfeatGethLocal

geth HARDHAT_NETWORK=allfeat_local node scripts/as_bridge.js --deploy geth,allfeat_local,1337,440

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --deploy geth,allfeat_local,1337,440

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --test-deposit-fees

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --test-deposit-token

geth HARDHAT_NETWORK=geth node scripts/as_bridge.js --update-operator


```

## Allfeat node

### Node

/Users/arnaudsene/Documents/Code/blockchain/substrate/build_a_blockchain/Allfeat

```bash
# start node
./target/release/allfeat --dev
```

### Front app

https://polkadot.js.org/apps/?rpc=wss%3A%2F%2Fharmonie-endpoint-02.allfeat.io#/settings
