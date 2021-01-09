from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from typing import Awaitable, cast, Optional, Union

from . import utils
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
        return utils.any_to_sync(self._apply)(item)

    async def async_call(self, item: FileItem) -> FileItem:
        """Apply the filter asynchronously"""
        if not self.async_ok:
            raise FilestorageConfigError(
                f'The {self.__class__.__name__} filter cannot be used '
                'asynchronously'
            )

        if iscoroutinefunction(self._apply):
            return await cast(utils.AsyncCallable, self._apply)(item)
        return cast(utils.SyncCallable, self._apply)(item)

    @abstractmethod
    def _apply(self, item: FileItem) -> Union[Awaitable[FileItem], FileItem]:
        return item


class AsyncFilterBase(FilterBase, ABC):
    async_ok = True

    @abstractmethod
    async def _apply(self, item: FileItem) -> FileItem:
        return item
