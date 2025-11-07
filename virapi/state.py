from typing import Any, Dict, Optional
import threading
import asyncio


class State:
    """
    State in progress for the application.

    Features:
        - Access by attributes: state.foo
        - Initialization from a dict: State({"a": 1})
        - Basic synchronous and asynchronous methods (get/set/update/aset/aget)
        - Atomic incr operation (synchronous)

    NOTE: This does NOT synchronize between processes; (for that, use Redis/DB).
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(initial or {})
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    # Access by attributes (read)
    def __getattr__(self, name: str) -> Any:
        # called only if the attribute is not in __dict__
        with self._lock:
            if name in self._data:
                return self._data[name]
        raise AttributeError(f"State has no attribute '{name}'")

    # Access by attributes (write)
    def __setattr__(self, name: str, value: Any) -> None:
        # protect internal attributes
        if name in ("_data", "_lock", "_async_lock"):
            object.__setattr__(self, name, value)
            return
        with self._lock:
            self._data[name] = value

    def __delattr__(self, name: str) -> None:
        with self._lock:
            if name in self._data:
                del self._data[name]
                return
        raise AttributeError(f"State has no attribute '{name}'")

    # Dict-like helpers
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def update(self, mapping: Dict[str, Any]) -> None:
        with self._lock:
            self._data.update(mapping)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    # Asynchronous
    async def aget(self, key: str, default: Any = None) -> Any:
        async with self._async_lock:
            return self._data.get(key, default)

    async def aset(self, key: str, value: Any) -> None:
        async with self._async_lock:
            self._data[key] = value

    async def aupdate(self, mapping: Dict[str, Any]) -> None:
        async with self._async_lock:
            self._data.update(mapping)