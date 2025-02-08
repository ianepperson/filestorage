from datetime import datetime
from typing import Dict, Tuple, NamedTuple, Optional

from filestorage import FileItem, StorageHandlerBase, AsyncStorageHandlerBase

# A file kept in memory, with file system like properties.
_file = NamedTuple(
    "File",
    [
        ("contents", bytes),
        ("atime", datetime),
        ("ctime", datetime),
        ("mtime", datetime),
    ],
)


class DummyHandler(StorageHandlerBase):
    """Dummy class for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Store files where the key is the url path and the value is
        # a named tuple containing the contents of the file, the access
        # time, the creation time, and the time of last modification.
        self.files: Dict[str, _file] = {}
        self.last_save: Optional[FileItem] = None
        self.last_save_contents: bytes = b""
        self.last_delete: Optional[FileItem] = None
        self.validated = False

    def _validate(self) -> None:
        self.validated = True

    def get_file_key(self, item: FileItem) -> FileItem:
        return item.copy(data=None)

    def _exists(self, item: FileItem) -> bool:
        """Indicate if the given file exists within the given folder."""
        return item.url_path in self.files

    def assert_exists(self, filename: str, path: Tuple[str, ...]) -> None:
        """Assert that the given file exists in the dummy file system."""
        assert self._exists(FileItem(filename=filename, path=path))

    def _get_size(self, item: FileItem) -> int:
        """Indicate if the given file size is equal to the anticipated size."""
        return len(self.files[item.url_path].contents)

    def assert_get_size(
        self, filename: str, path: Tuple[str, ...], size: int
    ) -> None:
        """Assert that given file size is equal to the anticipated size."""
        assert self._get_size(FileItem(filename=filename, path=path)) == size

    def _get_accessed_time(self, item: FileItem) -> datetime:
        """Indicate if the given file access time is equal to the anticipated time."""
        return self.files[item.url_path].atime

    def assert_get_accessed_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file access time is equal to the anticipated time."""
        assert (
            self._get_accessed_time(FileItem(filename=filename, path=path))
            == date
        )

    def _get_created_time(self, item: FileItem) -> datetime:
        """Indicate if the given file creation time is equal to the anticipated time."""
        return self.files[item.url_path].ctime

    def assert_get_created_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file creation time is equal to the anticipated time."""
        assert (
            self._get_created_time(FileItem(filename=filename, path=path))
            == date
        )

    def _get_modified_time(self, item: FileItem) -> datetime:
        """Indicate if the given file modification time is equal to the anticipated time."""
        return self.files[item.url_path].mtime

    def assert_get_modified_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file modification time is equal to the anticipated time."""
        assert (
            self._get_modified_time(FileItem(filename=filename, path=path))
            == date
        )

    def _save(self, item: FileItem) -> str:
        """Save the provided file to the given filename in the storage
        container.
        """
        with item as f:
            self.last_save_contents = f.read()
            self.files[item.url_path] = _file(
                self.last_save_contents,
                datetime.now(),
                datetime.now(),
                datetime.now(),
            )
            f.seek(0)
        self.last_save = item
        return item.filename

    def assert_file_contains(
        self, filename: str, path: Tuple[str, ...], data: bytes
    ) -> None:
        """Assert that the given file contains the given data."""
        item = FileItem(filename=filename, path=path)
        assert self.files[item.url_path] == data

    def _delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        del self.files[item.url_path]
        self.last_delete = item


class AsyncDummyHandler(AsyncStorageHandlerBase, DummyHandler):
    """Dummy class for testing."""

    allow_async = True

    def get_file_key(self, item: FileItem) -> FileItem:
        return item.copy(data=None)

    async def _async_exists(self, item: FileItem) -> bool:
        """Indicate if the given file exists within the given folder."""
        return item.url_path in self.files

    def assert_exists(self, filename: str, path: Tuple[str, ...]) -> None:
        """Assert that the given file exists in the dummy file system."""
        assert self._exists(FileItem(filename=filename, path=path))

    async def _async_get_size(self, item: FileItem) -> int:
        """Indicate if the given file size is equal to the anticipated size."""
        return len(self.files[item.url_path].contents)

    def assert_get_size(
        self, filename: str, path: Tuple[str, ...], size: int
    ) -> None:
        """Assert that given file size is equal to the anticipated size."""
        assert self._get_size(FileItem(filename=filename, path=path)) == size

    async def _async_get_accessed_time(self, item: FileItem) -> datetime:
        """Get the last access time for the given file"""
        return self.files[item.url_path].atime

    def assert_get_accessed_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file access time is equal to the anticipated time."""
        assert (
            self._get_accessed_time(FileItem(filename=filename, path=path))
            == date
        )

    async def _async_get_created_time(self, item: FileItem) -> datetime:
        """Get the created time"""
        return self.files[item.url_path].ctime

    def assert_get_created_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file creation time is equal to the anticipated time."""
        assert (
            self._get_created_time(FileItem(filename=filename, path=path))
            == date
        )

    async def _async_get_modified_time(self, item: FileItem) -> datetime:
        """Return the last modified time"""
        return self.files[item.url_path].mtime

    def assert_get_modified_time(
        self, filename: str, path: Tuple[str, ...], date: datetime
    ) -> None:
        """Assert that given file modification time is equal to the anticipated time."""
        assert (
            self._get_modified_time(FileItem(filename=filename, path=path))
            == date
        )

    async def _async_save(self, item: FileItem) -> str:
        """Save the provided file to the given filename in the storage
        container. Returns the name of the file saved.
        """
        async with item as f:
            self.last_save_contents = await f.read()
            self.files[item.url_path] = _file(
                self.last_save_contents,
                datetime.now(),
                datetime.now(),
                datetime.now(),
            )
            await f.seek(0)
            self.last_save = item
        return item.filename

    def assert_file_contains(
        self, filename: str, path: Tuple[str, ...], data: bytes
    ) -> None:
        """Assert that the given file contains the given data."""
        item = FileItem(filename=filename, path=path)
        assert self.files[item.url_path] == data

    async def _async_delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        del self.files[item.url_path]
        self.last_delete = item
