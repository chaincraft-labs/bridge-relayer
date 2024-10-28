# Blockchain bridge relayer (POC)

[![Static Badge](https://img.shields.io/badge/3.12-blue?logo=python&logoColor=white&label=%7C%20Python)](https://www.python.org/downloads/release/python-3120/)
[![GitHub Tag](https://img.shields.io/github/v/tag/ArnaudSene/bridge-relay-poc?logo=github&label=%7C%20Tag)](https://github.com/ArnaudSene/bridge-relay-poc/releases/tag/v0.1.0) 
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ArnaudSene/bridge-relay-poc/01-deploy.yml?logo=githubactions&logoColor=white&label=%7C%20build)](https://github.com/ArnaudSene/bridge-relay-poc/actions/workflows/01-deploy.yml) 
![Endpoint Badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/ArnaudSene/ddcf34589ce0297a4bf5ab8cd21ebbf2/raw/3f80da2bbbdcabfca3a7f4dad39706415557e323/covbadge.json&logo=pytest&logoColor=white&label=%7C%20Coverage)

---

A **centralized blockchain bridge** relayer that aims to connect two blockchains (Proof Of Concept: POC)

A blockchain bridge is a technology that allows two different blockchains to communicate and exchange data or assets with each other. Blockchains are often siloed and operate independently, which means that assets or information on one blockchain cannot naturally move to or interact with another blockchain. A bridge acts as a connection point or "gateway" between these networks, enabling cross-chain transfers and interoperability.

For example, if someone wants to move cryptocurrency or tokens from Blockchain A (such as Ethereum) to Blockchain B (like Binance Smart Chain), a bridge relayer facilitates this transaction by locking or burning the tokens on Blockchain A and issuing an equivalent amount of tokens on Blockchain B.

A centralized blockchain bridge relayer would be responsible for managing these cross-chain transfers in a centralized manner, meaning that the authority and control over the relaying process reside with a single entity or small group, as opposed to a decentralized system where many participants validate and process the transactions.

In summary:

A bridge enables two different blockchains to communicate and share assets or information.
The relayer acts as an intermediary responsible for ensuring that the data or assets are securely transferred between the two blockchains.
A centralized relayer means that a central authority manages this process, potentially offering faster or more controlled operations but at the expense of decentralization.

## Get started

### Installation

#### Clone the directory

```bash
git clone https://github.com/AlyraButerin/bridge-relay-poc && cd bridge-relay-poc
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

The 'relayer-py' folder must contain 3 environment file as described below:

- `.env`             : Enable the production or development environment
- `.env.config.dev`  : Development environment settings
- `.env.config.prod` : Production environment settings


1. copy sample.env to .env
2. copy sample.env.config to `.env.config.dev` or `.env.config.prod`
3. update `.env.config.dev` or `.env.config.prod` values

> *See the `sample.env.config` file for more detail.*

#### Configuration and abi files

There are 4 files at the location: src/relayer/config

- abi_dev.json
- abi.json
- bridge_relayer_config_dev.toml
- bridge_relayer_config.toml


1. edit `bridge_relayer_config_dev.toml` and/or `bridge_relayer_config.toml` and set the chain IDs
2. edit **abi.json** and **abi_dev.json** and add the abi for each chain IDs


### Run the bridge relayer

The bridge relayer application executes 3 services as described below:

- an event listener for the first blockchain (e.g chain ID = 1337)
- an event listener for the second blockchain (e.g chain ID = 440)
- a task listener 

*The event listener* is responsible for monitoring and parsing all events emitted by the smart contract, storing these events in a local database (using LevelDB), and publishing them to a message queue via a broker (RabbitMQ).

*The task listener* is responsible for consuming new tasks from the message queue, interpreting them, and interacting with the appropriate blockchain to execute the required operations.

>! If you want to test locally you need to run 
>
> - A RabbitMQ server (see below the procedure with Docker)
> - 2 node clients for blockchains (See below to run geth and Allfeat client nodes) 

#### Run the event listeners for Allfeat and geth

Open a terminal and execute:

```bash
# Allfeat local node
cd relayer-py
poetry run python bin/event_listener.py --chain_id 440
```

In the second terminal execute:

```bash
# Geth local node
cd relayer-py
poetry run python bin/event_listener.py --chain_id 1337
```

#### Run the event task listener

Open a terminal and execute:

```bash
poetry run python bin/task_listener.py --watch
```


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

> ❗Queue names are set in
>
> `env.config.dev`
> `env.config.prod`


## Geth

You can find the official documentation to install and run a Geth node [geth.ethereum.org](https://geth.ethereum.org/docs/getting-started/installing-geth)

```bash
# Start a geth node
geth --datadir /your_data_path --dev.period 12 --http --http.corsdomain '*' --http.api web3,eth,debug,personal,net --vmdebug --dev console
```

## Allfeat node

You can find the official documentation to run a node [docs.allfeat.com](https://docs.allfeat.com/running-a-node/without-docker/)


```bash
# start node
./target/release/allfeat --dev
```

### Front app

https://polkadot.js.org/apps/?rpc=wss%3A%2F%2Fharmonie-endpoint-02.allfeat.io#/settings


## Deploy the smart contracts

You can find the official documentation for [deploying smart contract](https://github.com/AlyraButerin/Allfeat-EVM-bridge-POC/blob/dev/hardhat/COMMANDS.md)
