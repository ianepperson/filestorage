from typing import Dict, Tuple, Optional

from filestorage import FileItem, StorageHandlerBase


class DummyHandler(StorageHandlerBase):
    """Dummy class for testing."""

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        # Store files where the key is the url path and the value is
        # the bytes that were stored to the file.
        self.files: Dict[str, bytes] = {}
        self.validated = False

    def _validate(self) -> None:
        self.validated = True

    def get_file_key(self, item: FileItem) -> FileItem:
        return item.copy(data=None)

    def _exists(self, item: FileItem) -> bool:
        """Indicate if the given file exists within the given folder."""
        return item.url_path in self.files

    def assert_exists(self, filename: str, path: Tuple[str]) -> None:
        """Assert that the given file exists in the dummy file system."""
        assert self._exists(FileItem(filename=filename, path=path))

    def _save(self, item: FileItem) -> Optional[str]:
        """Save the provided file to the given filename in the storage
        container.
        """
        self.files[item.url_path] = item.sync_read()

    def assert_file_contains(
        self, filename: str, path: Tuple[str], data: bytes
    ) -> None:
        """Assert that the given file contains the given data."""
        item = FileItem(filename=filename, path=path)
        assert self.files[item.url_path] == data

    def _delete(self, item: FileItem) -> None:
        """Delete the given filename from the storage container, whether or not
        it exists.
        """
        del self.files[item.url_path]
