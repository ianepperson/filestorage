import asyncio
import io
from abc import ABC, abstractmethod
from typing import Awaitable, Optional, Tuple

from .exceptions import FilestorageConfigError


class FilterBase(ABC):
    async_ok = False

    def validate(self) -> Optional[Awaitable]:
        return self._validate()

    # For consistency with the storage handlers, use a _ method
    def _validate(self) -> Optional[Awaitable]:
        pass

    def call(self, fileio: io.IOBase, filename: str) -> Tuple[io.IOBase, str]:
        """Apply the filter synchronously"""
        result = self._apply(fileio, filename)
        if asyncio.iscoroutine(result):
            # Run to completion to get the result synchronously
            event_loop = asyncio.get_event_loop()
            result = event_loop.run_until_complete(result)

        return result

    async def async_call(
        self, fileio: io.IOBase, filename: str
    ) -> Tuple[io.IOBase, str]:
        """Apply the filter asynchronously"""
        if not self.async_ok:
            raise FilestorageConfigError(
                f'The {self.__class__.__name__} filter cannot be used '
                'asynchronously'
            )

        result = self._apply(fileio, filename)
        if not asyncio.iscoroutine(result):
            return result
        return await result

    @abstractmethod
    def _apply(
        self, fileio: io.IOBase, filename: str
    ) -> Tuple[io.IOBase, str]:
        return fileio, filename


class AsyncFilterBase(FilterBase, ABC):
    async_ok = True

    @abstractmethod
    async def _apply(
        self, fileio: io.IOBase, filename: str
    ) -> Tuple[io.IOBase, str]:
        return fileio, filename
