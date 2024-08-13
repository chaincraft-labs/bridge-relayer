"""Relayer exception."""


class BridgeRelayerException(Exception):
    """Base Relay exception class."""

# Configuration
class BridgeRelayerConfigEnvFileMissing(BridgeRelayerException):
    """Raise when the '.env' file is missing."""
    

class BridgeRelayerConfigEnvFileAttributeMissing(BridgeRelayerException):
    """Raise when an attribute is missing from .env file."""

    
class BridgeRelayerConfigABIFileMissing(BridgeRelayerException):
    """Raise when the 'abi.json' file is missing."""

    
class BridgeRelayerConfigTOMLFileMissing(BridgeRelayerException):
    """Raise when the '.toml' file is missing."""

    
class BridgeRelayerConfigABIAttributeMissing(BridgeRelayerException):
    """Raise when an ABI attribute is missing from abi.json file."""


class BridgeRelayerConfigBlockchainDataMissing(BridgeRelayerException):
    """Raise when no blockchain config retrieved for a specific chain id."""


class BridgeRelayerConfigRegisterDataMissing(BridgeRelayerException):
    """Raise when no register config retrieved."""


class BridgeRelayerConfigReplacePlaceholderTypeError(BridgeRelayerException):
    """Raise when bad args provided to replace placeholder."""


class BridgeRelayerConfigEventRuleKeyError(BridgeRelayerException):
    """Raise when invalid event name provided."""


# Blockchain events
class BridgeRelayerEventDataMissing(BridgeRelayerException):
    """Raise when an event is receive but data are missing."""


class BridgeRelayerBlockchainNotConnected(BridgeRelayerException):
    """Raise when not connected to bloclchain client."""


class BridgeRelayerListenEventFailed(BridgeRelayerException):
    """Raise when event listener failed."""


class BridgeRelayerEventsFilterTypeError(BridgeRelayerException):
    """Raise when events filter is invalid type."""


class BridgeRelayerEventsNotFound(BridgeRelayerException):
    """Raise when events not founds in ABI."""


class BridgeRelayerInvalidStartBlock(BridgeRelayerException):
    """Raise when start block is greater than end block."""


class BridgeRelayerErrorBlockPending(BridgeRelayerException):
    """Raise when a block is in pending status."""


class BridgeRelayerFetchEventOutOfRetries(BridgeRelayerException):
    """Raise when max retries has been reach while fetchin event data from RPC."""


# Register events

class BridgeRelayerRegisterEventFailed(BridgeRelayerException):
    """Raise when register event failed."""


class BridgeRelayerReadEventFailed(BridgeRelayerException):
    """Raise when read an event failed."""


class BridgeRelayerRegisterCredentialError(BridgeRelayerException):
    """Raise when trying to set credential for register."""
    
    
class BridgeRelayerRegisterConnectionError(BridgeRelayerException):
    """Raise when connecting to register platform failed."""
    
    
class BridgeRelayerRegisterChannelError(BridgeRelayerException):
    """Raise when creating channel failed."""
    
    
class BridgeRelayerRegisterDeclareQueueError(BridgeRelayerException):
    """Raise when declaring a queue failed."""


# Event Converter 
class EventConverterTypeError(BridgeRelayerException):
    """Raise when trying to create an EventDTO from event."""


# Event Consumer
class BlockFinalityTimeExceededError(BridgeRelayerException):
    """Raise when The function has exceeded the allocated time for processing."""


#  Event data stored

class EventDataStoreRegisterFailed(BridgeRelayerException):
    """Raise when the event cannot be set as registered in the state."""
    