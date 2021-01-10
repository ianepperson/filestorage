import abc
import cgi
from . import utils as utils
from .exceptions import FilestorageConfigError as FilestorageConfigError
from .file_item import FileItem as FileItem
from .filter_base import FilterBase as FilterBase
from .storage_container import StorageContainer as StorageContainer
from abc import ABC
from typing import Any, Awaitable, BinaryIO, List, Optional, Tuple, Union

class StorageHandlerBase(ABC, metaclass=abc.ABCMeta):
    handler_name: Any = ...
    def __init__(
        self,
        base_url: Optional[str] = ...,
        filters: Optional[List[FilterBase]] = ...,
        path: Union[Tuple[str, ...], List[str], str, None] = ...,
    ) -> None: ...
    @property
    def base_url(self) -> str: ...
    @property
    def path(self) -> Tuple[str, ...]: ...
    def validate(self) -> Optional[Awaitable]: ...
    def get_item(
        self,
        filename: str,
        subpath: Optional[Tuple[str, ...]] = ...,
        data: Optional[BinaryIO] = ...,
    ) -> FileItem: ...
    def get_url(self, filename: str) -> str: ...
    @classmethod
    def sanitize_filename(cls: Any, filename: str) -> str: ...
    def exists(self, filename: str) -> bool: ...
    def delete(self, filename: str) -> None: ...
    def save_file(self, data: BinaryIO, filename: str) -> str: ...
    def save_field(self, field: cgi.FieldStorage) -> str: ...
    def save_data(self, data: bytes, filename: str) -> str: ...

class AsyncStorageHandlerBase(StorageHandlerBase, ABC, metaclass=abc.ABCMeta):
    def validate(self) -> Optional[Awaitable]: ...
    async def async_exists(self, filename: str) -> bool: ...
    async def async_delete(self, filename: str) -> None: ...
    async def async_save_file(self, data: BinaryIO, filename: str) -> str: ...
    async def async_save_field(self, field: cgi.FieldStorage) -> str: ...
    async def async_save_data(self, data: bytes, filename: str) -> str: ...

class Folder(AsyncStorageHandlerBase):
    @property
    def allow_sync(self): ...
    def __init__(
        self, store: StorageContainer, path: Tuple[str, ...]
    ) -> None: ...
    def subfolder(self, folder_name: str) -> Folder: ...
    def __eq__(self, other: Any) -> bool: ...
    def __truediv__(self, other: str) -> Folder: ...