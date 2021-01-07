import io
import urllib
from abc import ABC, abstractmethod
from asyncio import gather, isfuture, iscoroutine
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Tuple,
    Union,
    TYPE_CHECKING,
)

from .file_item import FileItem
from .exceptions import FilestorageConfigError
from .filter_base import FilterBase

if TYPE_CHECKING:
    import cgi
    from .storage_container import StorageContainer

# Type aliases for legibility
MaybeAwaitBool = Union[bool, Awaitable[bool]]
MaybeAwaitStr = Union[str, Awaitable[str]]
MaybeAwaitNone = Union[None, Awaitable[None]]


class StorageHandlerBase(ABC):
    """Base class for all storage handlers."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        filters: Optional[List[FilterBase]] = None,
        path: Union[Tuple[str, ...], List[str], str, None] = None,
    ):
        self.handler_name = None
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

    def __str__(self):
        return f'<{self.__class__.__name__}("{self.handler_name}")>'

    def validate(self) -> Optional[Awaitable]:
        """Validate that the configuration is set up properly and the necessary
        libraries are available.

        If any configuration is amiss, raises a FilestorageConfigError.
        """
        coroutines = []
        # Verify that any provided filters are valid.
        for filter_ in self._filters:
            result = filter_.validate()
            if iscoroutine(result) or isfuture(result):
                coroutines.append(result)

        result = self._validate()
        if iscoroutine(result) or isfuture(result):
            coroutines.append(result)

        if not coroutines:
            return
        return gather(*coroutines)

    def _validate(self) -> None:
        """Validate any subclass."""
        pass

    def get_item(
        self,
        filename: str,
        subpath: Optional[Tuple[str, ...]] = None,
        data: Optional[io.BytesIO] = None,
    ) -> FileItem:
        path = self._path
        if subpath is not None:
            path = subpath + self._path

        return FileItem(filename=filename, path=path, data=data)

    GetUrlMethodType = Callable[[str], str]

    def get_url(self, filename: str) -> str:
        """Return the URL of a given filename in this storage container."""
        item = self.get_item(filename)
        return urllib.parse.urljoin(self.base_url, item.url_path)

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

    ExistsMethodType = Callable[[str], MaybeAwaitBool]

    def exists(self, filename: str) -> bool:
        """Determine if the given filename exists in the storage container."""
        item = self.get_item(filename)
        return self._exists(item)

    @abstractmethod
    def _exists(self, item: FileItem) -> bool:
        """Determine if the given path/filename exists in the storage
        container.
        """
        pass

    DeleteMethodType = Callable[[str], MaybeAwaitStr]

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
    def _save(self, item: FileItem) -> Optional[str]:
        """Save the provided file to the given filename in the storage
        container.
        """
        pass

    SaveFileMethodType = Callable[['io.BytesIO', str], MaybeAwaitStr]

    def save_file(self, data: 'io.BytesIO', filename: str) -> str:
        """Verifies that the provided filename is legitimate and saves it to
        the storage container.

        Returns the filename that was saved.
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)

        for filter_ in self._filters:
            item = filter_.call(item)

        new_filename = self._save(item)
        if new_filename is not None:
            filename = new_filename
        return filename

    SaveFieldMethodType = Callable[['cgi.FieldStorage'], MaybeAwaitStr]

    def save_field(self, field: 'cgi.FieldStorage') -> str:
        """Save a file stored in a CGI field."""
        return self.save_file(field.file, field.filename or 'file')

    SaveDataMethodType = Callable[[bytes, str], MaybeAwaitStr]

    def save_data(self, data: bytes, filename: str) -> str:
        """Save a file from the byte data provided."""
        fileio = io.BytesIO(data)
        return self.save_file(fileio, filename)


class SubFolder(StorageHandlerBase):
    """A handler for a sub-folder of a container.

    Note that this does not carry any config and depends on the
    StorageContainer to provide the handler when needed.
    """

    def __init__(self, store: 'StorageContainer', path: Tuple[str]):
        super().__init__(path=path)
        self._store = store

    def subfolder(self, folder_name: str) -> 'SubFolder':
        """Get a subfolder for this subfolder"""
        return SubFolder(store=self._store, path=self._path + (folder_name,))

    def __eq__(self, other: 'SubFolder') -> bool:
        return (
            isinstance(other, SubFolder)
            and (self._store is other._store)
            and (self._path == other._path)
        )

    def __truediv__(self, other: str) -> 'SubFolder':
        """Get a new subfolder when using the divide operator.

        Allows building a path with path-looking code:
            new_store = store / 'folder' / 'subfolder'
        """
        return self.subfolder(other)

    def update_file_item(self, item: FileItem) -> FileItem:
        new_path = self._store.handler.path + self._path
        return FileItem(filename=item.filename, path=new_path, data=item.data)

    def _exists(self, item: FileItem) -> bool:
        """Return the handler's _exists method from this folder"""
        item = self.update_file_item(item)
        return self._store.handler._exists(item)

    def _delete(self, item: FileItem) -> None:
        """Return the handler's _delete method from this folder"""
        item = self.update_file_item(item)
        return self._store.handler._delete(item)

    def _save(self, item: FileItem) -> str:
        """Return the handler's _save from this folder"""
        item = self.update_file_item(item)
        return self._store.handler._save(item)


class AsyncStorageHandlerBase(StorageHandlerBase, ABC):
    """Base class for all asynchronous storage handlers."""

    def validate(self) -> Optional[Awaitable]:
        """Validate that the configuration is set up properly and the necessary
        libraries are available.

        If anything is amiss, raises a FilestorageConfigError.
        """
        # Verify that any provided filters are ok to use.
        for filter_ in self._filters:
            if not filter_.async_ok:
                raise FilestorageConfigError(
                    f'Filter {filter_} cannot be used in '
                    f'asynchronous storage handler {self}'
                )
        return super().validate()

    async def _validate(self) -> None:
        """Validate any subclass."""
        pass

    @abstractmethod
    async def _exists(self, item: FileItem) -> bool:
        """Determine if the given filename exists in the storage container."""
        pass

    @abstractmethod
    async def _delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        pass

    @abstractmethod
    async def _save(self, item: FileItem) -> Optional[str]:
        """Save the provided file to the given filename in the storage
        container.
        """
        pass

    async def save_file(self, data: 'io.IOBase', filename: str) -> str:
        """Verifies that the provided filename is legitimate and saves it to
        the storage container.

        Returns the filename that was saved.
        """
        filename = self.sanitize_filename(filename)
        item = self.get_item(filename, data=data)
        for filter_ in self._filters:
            item = await filter_.async_call(item)

        new_filename = await self._save(item)
        if new_filename is not None:
            filename = new_filename
        return filename
