"""Base DTO."""
from dataclasses import dataclass
from types import UnionType
from typing import Any, Optional

@dataclass
class BaseResult:
    """Base Result DTO."""
    
    _ok: Optional[Any] = None
    _err: Optional[Any] = None
    
    @property
    def ok(self) -> Any:
        """"""
        return self._ok
    
    @ok.setter
    def ok(self, value: Any) -> None:
        """"""
        self._ok = value
        self._err = None
    
    @property
    def err(self) -> Any:
        """"""
        return self._err
    
    @err.setter
    def err(self, value: Any) -> None:
        """"""
        self._err = value
        self._ok = None   
   
    def __bool__(self):
        return bool(self.ok)
    