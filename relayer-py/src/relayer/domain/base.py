"""Base DTO."""
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class BaseResult:
    """Base Result DTO."""
    
    _ok: Optional[Any] = None
    _err: Optional[Any] = None
    
    @property
    def ok(self) -> Any:
        """Get ok."""
        return self._ok
    
    @ok.setter
    def ok(self, value: Any) -> None:
        """Set ok and reset err."""
        self._ok = value
        self._err = None
    
    @property
    def err(self) -> Any:
        """Get err."""
        return self._err
    
    @err.setter
    def err(self, value: Any) -> None:
        """Set err and reset ok."""
        self._err = value
        self._ok = None   
   
    def __bool__(self):
        """Get instance as boolean."""
        return bool(self.ok)
    