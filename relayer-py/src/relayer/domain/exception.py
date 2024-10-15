"""Relayer exception."""


class RelayerException(Exception):
    """Base Relay exception class."""

# -----------------------------------------------------------------------
# Configuration

class RelayerConfigError(RelayerException):
    """Raise when no config data found."""


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

# -----------------------------------------------------------------------
# Blockchain / web3

class RelayerEventsNotFound(RelayerException):
    """Raise when events not found."""


class RelayerErrorBlockPending(RelayerException):
    """Raise when a block is in pending status."""


class RelayerFetchEventOutOfRetries(RelayerException):
    """Raise when max retries has been reach while fetchin event data from RPC."""


class RelayerEventScanFailed(RelayerException):
    """Raise when event scan failed."""

# -----------------------------------------------------------------------
# Register events

class RelayerRegisterEventFailed(RelayerException):
    """Raise when register event failed."""


class RelayerReadEventFailed(RelayerException):
    """Raise when read an event failed."""


# -----------------------------------------------------------------------
# Event Converter 
class EventConverterTypeError(RelayerException):
    """Raise when trying to create an EventDTO from event."""


# -----------------------------------------------------------------------
# Consumer / Execute smart contract function
class RelayerBlockFinalityTimeExceededError(RelayerException):
    """Raise when The function has exceeded the allocated time for processing."""


class RelayerBlockchainBuildTxError(RelayerException):
    """Raise when build transaction failed."""


class RelayerBlockchainSignTxError(RelayerException):
    """Raise when sign transaction failed."""


class RelayerBlockchainSendRawTxError(RelayerException):
    """Raise when send raw transaction failed."""


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


class RelayerBridgeTaskInvalidStatus(RelayerException):
    """Raise when bridge task status is invalid."""

# -----------------------------------------------------------------------
#  Repository

class RepositoryDatabaseNotProvided(RelayerException):
    """Raise when db is not provided."""


class RepositoryErrorOnSave(RelayerException):
    """Raise when cannot be save data."""


class RepositoryErrorOnGet(RelayerException):
    """Raise when cannot be get data"""


class RepositoryErrorOnDelete(RelayerException):
    """Raise when cannot be delete data"""

# -----------------------------------------------------------------------
# Event
 
class RepositoryErrorSetEventAsRegistered(RelayerException):
    """Raise when cannot set event as registered."""


class RepositoryRegisterErrorOnSave(RelayerException):
    """Raise when the event cannot be set as registered in the state."""


class RepositoryNoBlockToDelete(RelayerException):
    """Raise when there is no block to delete from event state."""


class RepositoryStateEmptyOrNotLoaded(RelayerException):
    """Raise when the state is empty or not loaded."""


class RepositoryLastScannedBlockInvalid(RelayerException):
    """Raise when the last scanned block is invalid."""
    