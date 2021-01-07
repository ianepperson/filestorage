import os
import shutil
from typing import Optional

try:
    # The aiofiles library is needed for async file operations
    import aiofiles
    import aiofiles.os
except ImportError:
    aiofiles = None

from filestorage import FileItem, StorageHandlerBase, AsyncStorageHandlerBase
from filestorage.exceptions import FilestorageConfigError


class LocalFileHandler(StorageHandlerBase):
    """Class for storing files locally"""

    async_ok = False

    def __init__(self, base_path, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path

    def local_path(self, item: FileItem) -> str:
        """Returns the local path to the file."""
        return os.path.join(self.base_path, item.fs_path)

    def make_dir(self, item: Optional[FileItem] = None):
        """Ensures the provided path exists."""
        local_path = self.base_path
        if item:
            local_path = os.path.join(self.base_path, *item.path)
        os.makedirs(local_path, exist_ok=True)

    def validate(self) -> None:
        # Create the folder if it doesn't exist
        self.make_dir(tuple())

    def _exists(self, item: FileItem) -> bool:
        return os.path.exists(self.local_path(item))

    def _delete(self, item: FileItem) -> None:
        try:
            os.remove(self.local_path(item))
        except FileNotFoundError:
            pass

    def _save(self, item: FileItem) -> Optional[str]:
        item.seek(0)

        filename = self.resolve_filename(item)
        with open(self.local_path(item), 'wb') as destination:
            shutil.copyfileobj(item.data, destination)

        return filename

    def resolve_filename(self, item: FileItem) -> str:
        """Ensures a unique name for this file in the folder"""
        if not self.exists(item):
            return item.filename

        basename, ext = os.path.splitext(item.filename)
        counter = 1
        while True:
            name = f'{basename}-{counter}'
            if not self.exists(name + ext, item.path):
                return name + ext
            counter += 1


class AsyncLocalFileHandler(AsyncStorageHandlerBase):
    """Class for storing files locally"""

    def __init__(self, base_path, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path

    def local_path(self, item: FileItem) -> str:
        """Returns the local path to the file."""
        return os.path.join(self.base_path, item.fs_path)

    async def make_dir(self, item: Optional[FileItem] = None):
        """Ensures the provided path exists."""
        path_parts = (self.base_path)
        if item:
            path_parts = path_parts + item.path

        local_path = ''
        # Walk the parts and make the folder
        for path_part in path_parts:
            local_path = os.path.join(local_path, path_part)
            await aiofiles.os.mkdir(local_path, exist_ok=True)

    async def validate(self) -> None:
        if aiofiles is None:
            raise FilestorageConfigError(
                'The aiofiles library is required for using '
                f'{self.__class__.__name__}'
            )
        self.os_exists = aiofiles.os.wrap(os.path.exists)
        # Create the folder if it doesn't exist
        await self.make_dir()

    async def _exists(self, item: FileItem) -> bool:
        try:
            await self.stat(self.local_path(item))
        except FileNotFoundError:
            return False
        else:
            return True

    async def _delete(self, item: FileItem) -> None:
        try:
            aiofiles.os.remove(self.local_path(item))
        except FileNotFoundError:
            pass

    async def _save(self, item: FileItem) -> Optional[str]:
        await item.async_seek(0)

        filename = await self.resolve_filename(item)
        async with aiofiles.open(self.local_path(item), 'wb') as destination:
            while True:
                chunk = item.async_read(1024)
                if not chunk:
                    break
                await destination.write(chunk)

        return filename

    async def resolve_filename(self, item: FileItem) -> str:
        """Ensures a unique name for this file in the folder"""
        if not await self.exists(item):
            return item.filename

        basename, ext = os.path.splitext(item.filename)
        counter = 1
        while True:
            name = f'{basename}-{counter}'
            if not await self.exists(name + ext, item.path):
                return name + ext
            counter += 1
