from asyncio import iscoroutine, isfuture, get_event_loop
from abc import ABC, abstractmethod
from typing import Awaitable, Optional

from .exceptions import FilestorageConfigError
from .file_item import FileItem


class FilterBase(ABC):
    async_ok = False

    def validate(self) -> Optional[Awaitable]:
        return self._validate()

    # For consistency with the storage handlers, use a _ method
    def _validate(self) -> Optional[Awaitable]:
        pass

    def call(self, item: FileItem) -> FileItem:
        """Apply the filter synchronously"""
        result = self._apply(item)
        if iscoroutine(result) or isfuture(result):
            # Run to completion to get the result synchronously
            event_loop = get_event_loop()
            result = event_loop.run_until_complete(result)

        return result

    async def async_call(self, item: FileItem) -> FileItem:
        """Apply the filter asynchronously"""
        if not self.async_ok:
            raise FilestorageConfigError(
                f'The {self.__class__.__name__} filter cannot be used '
                'asynchronously'
            )

        result = self._apply(item)
        if not (iscoroutine(result) or isfuture(result)):
            return result
        return await result

    @abstractmethod
    def _apply(self, item: FileItem) -> FileItem:
        return item


class AsyncFilterBase(FilterBase, ABC):
    async_ok = True

    @abstractmethod
    async def _apply(self, item: FileItem) -> FileItem:
        return item
