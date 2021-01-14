import os
from typing import Optional, Set

try:
    # The aiofiles library is needed for async file operations
    import aiofiles
    import aiofiles.os  # type: ignore
except ImportError:
    # The validate method will ensure this isn't None prior to use
    aiofiles = None  # type: ignore

from filestorage import (
    FileItem,
    StorageHandlerBase,
    AsyncStorageHandlerBase,
    utils,
)
from filestorage.exceptions import FilestorageConfigError


class LocalFileHandler(StorageHandlerBase):
    """Class for storing files locally"""

    async_ok = False
    chunk_size = 1024 * 8

    def __init__(self, base_path, auto_make_dir=False, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path
        self.auto_make_dir = auto_make_dir
        self._created_dirs: Set[str] = set()

    def local_path(self, item: FileItem) -> str:
        """Returns the local path to the file."""
        return os.path.join(self.base_path, item.fs_path)

    def make_dir(self, item: Optional[FileItem] = None):
        """Ensures the provided path exists."""
        if not item:
            item = self.get_item('')
        else:
            item = item.copy(filename='')

        local_path = self.local_path(item)
        if local_path in self._created_dirs:
            return

        os.makedirs(local_path, exist_ok=True)
        self._created_dirs.add(local_path)

    def validate(self) -> None:
        # Create the folder if it doesn't exist
        if self.auto_make_dir:
            self.make_dir()
        else:
            item = self.get_item('')
            if not self._exists(item):
                local_path = self.local_path(item)
                raise FilestorageConfigError(
                    f'Configured directory {local_path!r} does not exist'
                )

    def _exists(self, item: FileItem) -> bool:
        return os.path.exists(self.local_path(item))

    def _delete(self, item: FileItem) -> None:
        try:
            os.remove(self.local_path(item))
        except FileNotFoundError:
            pass

    def _save(self, item: FileItem) -> str:
        if item.data is None:
            raise RuntimeError('No data for file {item.filename!r}')

        if self.auto_make_dir:
            self.make_dir(item)

        item = self.resolve_filename(item)
        with open(self.local_path(item), 'wb') as destination:
            with item as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    destination.write(chunk)

        return item.filename

    def resolve_filename(self, item: FileItem) -> FileItem:
        """Ensures a unique name for this file in the folder"""
        if not self._exists(item):
            return item

        basename, ext = os.path.splitext(item.filename)
        for counter in range(1, 1000000):
            filename = f'{basename}-{counter}{ext}'
            item = item.copy(filename=filename)
            if not self._exists(item):
                return item
        else:
            raise RuntimeError(
                f'Cannot get unique name for file {basename}{ext}'
            )


def os_wrap(fn: utils.SyncCallable) -> utils.AsyncCallable:
    """Use the wrap function from aiofiles to wrap the additional required
    os methods
    """
    return aiofiles.os.wrap(fn)  # type: ignore


def disabled_method(*args, **kwargs):
    raise RuntimeError('method not allowed')


class AsyncLocalFileHandler(LocalFileHandler, AsyncStorageHandlerBase):
    """Class for storing files locally"""

    async def async_make_dir(self, item: Optional[FileItem] = None):
        """Ensures the provided path exists."""
        if not item:
            item = self.get_item('')
        else:
            item = item.copy(filename='')

        local_path = self.local_path(item)
        if local_path in self._created_dirs:
            return

        await os_wrap(os.makedirs)(local_path, exist_ok=True)  # type: ignore

    def validate(self) -> None:
        if aiofiles is None:
            raise FilestorageConfigError(
                'The aiofiles library is required for using '
                f'{self.__class__.__name__}'
            )

        # Ensure the sync methods can operate while validating
        temp_setting = self.allow_sync_methods
        self.allow_sync_methods = True
        super().validate()
        self.allow_sync_methods = temp_setting

    async def _async_exists(self, item: FileItem) -> bool:
        try:
            await aiofiles.os.stat(self.local_path(item))
        except FileNotFoundError:
            return False
        else:
            return True

    async def _async_delete(self, item: FileItem) -> None:
        try:
            await aiofiles.os.remove(self.local_path(item))
        except FileNotFoundError:
            pass

    async def _async_save(self, item: FileItem) -> str:
        if item.data is None:
            raise RuntimeError('No data for file {item.filename!r}')

        if self.auto_make_dir:
            await self.async_make_dir(item)

        item = await self.async_resolve_filename(item)
        open_context = aiofiles.open(self.local_path(item), 'wb')
        async with open_context as destination:  # type: ignore
            async with item as f:
                while True:
                    chunk = await f.read(self.chunk_size)
                    if not chunk:
                        break
                    await destination.write(chunk)

        return item.filename

    async def async_resolve_filename(self, item: FileItem) -> FileItem:
        """Ensures a unique name for this file in the folder"""
        if not await self._async_exists(item):
            return item

        basename, ext = os.path.splitext(item.filename)
        for counter in range(1, 1000000):
            filename = f'{basename}-{counter}{ext}'
            item = item.copy(filename=filename)
            if not await self._async_exists(item):
                return item
        else:
            raise RuntimeError(
                f'Cannot get unique name for file {basename}{ext}'
            )

    def _save(self, item: FileItem) -> str:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync save method not allowed')
        return super()._save(item)

    def _exists(self, item: FileItem) -> bool:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync exists method not allowed')
        return super()._exists(item)

    def _delete(self, item: FileItem) -> None:
        if not self.allow_sync_methods:
            raise RuntimeError('Sync delete method not allowed')
        super()._delete(item)
