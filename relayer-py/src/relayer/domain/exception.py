"""Relayer exception."""


class RelayerException(Exception):
    """Base Relay exception class."""

# Configuration

class RelayerConfigABIFileMissing(RelayerException):
    """Raise when the 'abi.json' file is missing."""


class RelayerConfigTOMLFileMissing(RelayerException):
    """Raise when the '.toml' file is missing."""


    
class RelayerConfigABIAttributeMissing(RelayerException):
    """Raise when an ABI attribute is missing from abi.json file."""


class RelayerConfigBlockchainDataMissing(RelayerException):
    """Raise when no blockchain config retrieved for a specific chain id."""


class RelayerConfigRegisterDataMissing(RelayerException):
    """Raise when no register config retrieved."""


class RelayerConfigReplacePlaceholderTypeError(RelayerException):
    """Raise when bad args provided to replace placeholder."""


class RelayerConfigEventRuleKeyError(RelayerException):
    """Raise when invalid event name provided."""

# Blockchain

class RelayerEventsNotFound(RelayerException):
    """Raise when events not found."""


class RelayerErrorBlockPending(RelayerException):
    """Raise when a block is in pending status."""


class RelayerFetchEventOutOfRetries(RelayerException):
    """Raise when max retries has been reach while fetchin event data from RPC."""


class RelayerEventScanFailed(RelayerException):
    """Raise when event scan failed."""


# Register events

class RelayerRegisterEventFailed(RelayerException):
    """Raise when register event failed."""


class RelayerReadEventFailed(RelayerException):
    """Raise when read an event failed."""


# Event Converter 
class EventConverterTypeError(RelayerException):
    """Raise when trying to create an EventDTO from event."""


# Consumer / Execute smart contract function
class RelayerBlockFinalityTimeExceededError(RelayerException):
    """Raise when The function has exceeded the allocated time for processing."""


class RelayerBlockchainFailedExecuteSmartContract(RelayerException):
    """Raise when execute smart contract function failed."""


class RelayerClientVersionError(RelayerException):
    """Raise when retrieve client version failed."""


class RelayerBlockValidityError(RelayerException):
    """Raise when block validity failed."""


class RelayerCalculateBLockFinalityError(RelayerException):
    """Raise when calculate block finality failed."""


class RelayerBlockValidationFailed(RelayerException):
    """Raise when block validation failed."""


#  Event data stored

class EventDataStoreRegisterFailed(RelayerException):
    """Raise when the event cannot be set as registered in the state."""


class EventDataStoreSaveEventOperationError(RelayerException):
    """Raise when the event task cannot be save to the state."""


class EventDataStoreNoBlockToDelete(RelayerException):
    """Raise when there is no block to delete from event state."""


class EventDataStoreStateEmptyOrNotLoaded(RelayerException):
    """Raise when the state is empty or not loaded."""
