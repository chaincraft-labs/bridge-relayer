"""Converter tool."""
from io import BytesIO
from typing import Any
import pickle

from web3 import Web3


def _serialize_data(data: Any) -> BytesIO:
    """Serialize data to a BytesIO object.

    Args:
        data (Any): The data to serialize.

    Returns:
        BytesIO: The data serialized
    """
    pickle_data = pickle.dumps(
        data, protocol=pickle.HIGHEST_PROTOCOL)

    return BytesIO(pickle_data)


def to_bytes(data: Any) -> bytes:
    """Convert data to a bytes object.

    Args:
        data (Any): The data to convert.

    Returns:
        bytes: The data converted
    """
    return _serialize_data(data).getvalue()


def from_bytes(data: bytes) -> Any:
    """Convert data from a bytes object.

    Args:
        data (bytes): The data to convert.

    Returns:
        bytes: The data converted
    """
    return pickle.load(BytesIO(data))


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert a hex string to bytes.

    Args:
        hex_str (str): The hex string

    Returns:
        bytes: The bytes
    """
    return Web3.to_bytes(hexstr=hex_str)


def bytes_to_hex(hex_bytes: bytes) -> bytes:
    """Convert bytes to a hex string.

    Args:
        hex_bytes (bytes): The bytes

    Returns:
        bytes: The hex string
    """
    return Web3.to_hex(hex_bytes)
