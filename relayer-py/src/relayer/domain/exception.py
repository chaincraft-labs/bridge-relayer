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



# Blockchain events
class BridgeRelayerEventDataMissing(BridgeRelayerException):
    """Raise when an event is receive but data are missing."""


class BridgeRelayerBlockchainNotConnected(BridgeRelayerException):
    """Raise when not connected to bloclchain client."""

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