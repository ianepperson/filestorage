import inspect
from abc import ABC, abstractmethod
from asyncio import gather, isfuture, iscoroutine
from io import BytesIO
from typing import (
    Awaitable,
    BinaryIO,
    cast,
    List,
    Optional,
    Tuple,
    Union,
    TYPE_CHECKING,
)
from urllib.parse import urljoin

from . import utils
from .file_item import FileItem
from .exceptions import FilestorageConfigError
from .filter_base import FilterBase

if TYPE_CHECKING:
    import cgi
    from .storage_container import StorageContainer


class StorageHandlerBase(ABC):
    """Base class for all storage handlers."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        filters: Optional[List[FilterBase]] = None,
        path: Union[Tuple[str, ...], List[str], str, None] = None,
    ):
        self.handler_name: Optional[str] = None
        self._base_url = base_url
        self._filters = filters or []

        # It's a bit too easy to monkey up creating a tuple. Allow the library
        # users to provide a path in a couple of different ways.
        self._path: Tuple[str, ...]
        if isinstance(path, str):
            self._path = (path,)
        elif path:
            self._path = tuple(path)
        else:
            self._path = tuple()

    @property
    def base_url(self) -> str:
        return self._base_url or ''

    @property
    def path(self) -> Tuple[str, ...]:
        return self._path

    @property
    def filters(self) -> List[FilterBase]:
        return self._filters

    def __str__(self):
        return f'<{self.__class__.__name__}("{self.handler_name}")>'

    def validate(self) -> Optional[Awaitable]:
        """Validate that the configuration is set up properly and the necessary
        libraries are available.

        If any configuration is amiss, raises a FilestorageConfigError.
        """
        coroutines: List[Awaitable] = []
        # Verify that any provided filters are valid.
        for filter_ in self._filters:
            if inspect.isclass(filter_):
                filter_name: str = filter_.__name__  # type: ignore
                raise FilestorageConfigError(
                    f'Filter {filter_name} is a class, not an instance. '
                    f'Did you mean to use "filters=[{filter_name}()]" instead?'
                )
            result = filter_.validate()
            if iscoroutine(result) or isfuture(result):
                coroutines.append(cast(Awaitable, result))

        result = self._validate()
        if iscoroutine(result) or isfuture(result):
            coroutines.append(cast(Awaitable, result))

        if not coroutines:
            return None
        return gather(*coroutines)

    def _validate(self) -> Optional[Awaitable]:
        """Validate any subclass."""
        pass

    def get_item(
        self,
        filename: str,
        subpath: Optional[Tuple[str, ...]] = None,
        data: Optional[BinaryIO] = None,
    ) -> FileItem:
        path = self._path
        if subpath is not None:
            path = path + subpath

        return FileItem(filename=filename, path=path, data=data)

    def get_url(self, filename: str) -> str:
        """Return the URL of a given filename in this storage container."""
        item = self.get_item(filename)
        return urljoin(self.base_url, item.url_path)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Perform a quick pass to sanitize the filename"""
        # Strip out any . prefix - which should eliminate attempts to write
        # special Unix files
        filename = filename.lstrip('.')

        # Strip out any non-alpha, . or _ characters.
        def clean_char(c: str) -> str:
            if c.isalnum() or c in ('.', '_'):
                return c
            return '_'

        filename = ''.join(clean_char(c) for c in filename)

        return filename

    def exists(self, filename: str) -> bool:
        """Determine if the given filename exists in the storage container."""
        item = self.get_item(filename)
        return cast(bool, self._exists(item))

    @abstractmethod
    def _exists(self, item: FileItem) -> bool:
        """Determine if the given path/filename exists in the storage
        container.
        """
        pass

    def delete(self, filename: str) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        item = self.get_item(filename)
        return self._delete(item)

    @abstractmethod
    def _delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        pass

    @abstractmethod
    def _save(self, item: FileItem) -> str:
        """Save the provided file to the given filename in the storage
        container. Returns the name of the file saved
        """
        pass

    def save_file(self, filename: str, data: BinaryIO) -> str:
        """Verifies that the provided filename is legitimate and saves it to
        the storage container.

        Returns the filename that was saved.
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)

        for filter_ in self.filters:
            item = filter_.call(item)

        return self._save(item)

    def save_field(self, field: 'cgi.FieldStorage') -> str:
        """Save a file stored in a CGI field."""
        if not field.file:
            raise RuntimeError('No file data in the field')

        return self.save_file(
            field.filename or 'file', cast(BinaryIO, field.file)
        )

    def save_data(self, filename: str, data: bytes) -> str:
        """Save a file from the byte data provided."""
        fileio = BytesIO(data)
        return self.save_file(filename, fileio)


class AsyncStorageHandlerBase(StorageHandlerBase, ABC):
    """Base class for all asynchronous storage handlers."""

    def __init__(self, allow_sync_methods=True, **kwargs):
        self.allow_sync_methods = allow_sync_methods
        super().__init__(**kwargs)

    def validate(self) -> Optional[Awaitable]:
        """Validate that the configuration is set up properly and the necessary
        libraries are available.

        If anything is amiss, raises a FilestorageConfigError.
        """
        # Verify that any provided filters are ok to use.
        for filter_ in self.filters:
            if not filter_.async_ok:
                raise FilestorageConfigError(
                    f'Filter {filter_} cannot be used in '
                    f'asynchronous storage handler {self}'
                )
        return super().validate()

    async def async_exists(self, filename: str) -> bool:
        """Determine if the given filename exists in the storage container."""
        item = self.get_item(filename)
        return await self._async_exists(item)

    def _exists(self, item: FileItem) -> bool:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync exists method not allowed')
        return utils.async_to_sync(self._async_exists)(item)

    @abstractmethod
    async def _async_exists(self, item: FileItem) -> bool:
        """Determine if the given filename exists in the storage container."""
        pass

    async def async_delete(self, filename: str) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        item = self.get_item(filename)
        await self._async_delete(item)

    def _delete(self, item: FileItem) -> None:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync delete method not allowed')
        utils.async_to_sync(self._async_delete)(item)

    @abstractmethod
    async def _async_delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        pass

    def _save(self, item: FileItem) -> str:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync save method not allowed')
        return utils.async_to_sync(self._async_save)(item)

    @abstractmethod
    async def _async_save(self, item: FileItem) -> str:
        """Save the provided file to the given filename in the storage
        container. Returns the name of the file saved.
        """
        pass

    async def async_save_file(self, filename: str, data: BinaryIO) -> str:
        """Verifies that the provided filename is legitimate and saves it to
        the storage container.

        Returns the filename that was saved.
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)
        for filter_ in self.filters:
            item = await filter_.async_call(item)

        new_filename = await self._async_save(item)
        if new_filename is not None:
            filename = new_filename
        return filename

    async def async_save_field(self, field: 'cgi.FieldStorage') -> str:
        """Save a file stored in a CGI field."""
        if not field.file:
            raise RuntimeError('No file data in the field')

        return await self.async_save_file(
            field.filename or 'file', cast(BinaryIO, field.file)
        )

    async def async_save_data(self, filename: str, data: bytes) -> str:
        """Save a file from the byte data provided."""
        fileio = BytesIO(data)
        return await self.async_save_file(filename, fileio)


class Folder(AsyncStorageHandlerBase):
    """A handler for a sub-folder of a container.

    Note that this does not carry any config and depends on the
    StorageContainer to provide the handler when needed.
    """

    @property
    def async_ok(self):
        return isinstance(self._store.handler, AsyncStorageHandlerBase)

    @property
    def filters(self) -> List[FilterBase]:
        return self._store.sync_handler.filters

    @property
    def base_url(self) -> str:
        return self._store.sync_handler.base_url

    def __init__(self, store: 'StorageContainer', path: Tuple[str, ...]):
        super().__init__(path=path)
        self._store = store

    def subfolder(self, folder_name: str) -> 'Folder':
        """Get a subfolder for this folder"""
        return Folder(store=self._store, path=self._path + (folder_name,))

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Folder)
            and (self._store is other._store)
            and (self._path == other._path)
        )

    def __truediv__(self, other: str) -> 'Folder':
        """Get a new subfolder when using the divide operator.

        Allows building a path with path-looking code:
            new_store = store / 'folder' / 'subfolder'
        """
        return self.subfolder(other)

    def _get_subfolder_file_item(self, item: FileItem) -> FileItem:
        new_path = self._store.sync_handler.path + self._path
        return FileItem(filename=item.filename, path=new_path, data=item.data)

    # Pass through any exists methods

    def _exists(self, item: FileItem) -> bool:
        """Return the handler's _exists method from this folder"""
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._exists(item)

    async def _async_exists(self, item: FileItem) -> bool:
        """Return the handler's _async_exists method from this folder"""
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_exists(item)

    # Pass through any delete methods

    def _delete(self, item: FileItem) -> None:
        """Return the handler's _delete method from this folder"""
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._delete(item)

    async def _async_delete(self, item: FileItem) -> None:
        """Return the handler's _async_delete method from this folder"""
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_delete(item)

    # Pass through any save methods

    def _save(self, item: FileItem) -> str:
        """Return the handler's _save from this folder"""
        item = self._get_subfolder_file_item(item)
        return self._store.sync_handler._save(item)

    async def _async_save(self, item: FileItem) -> str:
        """Return the handler's _async_save from this folder"""
        item = self._get_subfolder_file_item(item)
        return await self._store.async_handler._async_save(item)
