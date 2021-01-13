# Use this as a template for creating new storage handler classes
from typing import Awaitable, Optional

# If creating an awaitable handler, use AsyncStorageHandlerBase instead and
# populate every _async_* method.
from filestorage import StorageHandlerBase, FileItem
from filestorage.exceptions import FilestorageConfigError


class NewStorageHandler(StorageHandlerBase):
    """My new class for storing files!"""

    def __init__(self, **kwargs):
        # New instance. Make sure to call the base class with super then
        # perform any other necessary setup steps.
        # At this point, the handlers may not be fully configured, so don't do
        # too much here.
        super().__init__(**kwargs)
        pass

    def _validate(self) -> Optional[Awaitable]:
        """Perform any setup or validation."""
        # This should be called prior to other calls, but it might not!
        # If there's a problem with the validation, raise an error.
        # If the problem is with the configuration:
        #     raise FilestorageConfigError('describe the problem')
        # Can be an async method if necessary and will be awaited on properly.
        raise FilestorageConfigError('This is a template, not a real handler!')

    # async def _async_exists(self, item: FileItem) -> bool:
    def _exists(self, item: FileItem) -> bool:
        """Indicate if the given file exists within the given folder."""
        # item.filename might be something like 'foo.txt'
        # item.path might be something like ('folder', 'subfolder')
        # If the path needs to look like a URL, you can build it with
        # item.url_path, which joins any path item with the filename
        pass

    # async def _async_save(self, item: FileItem) -> str:
    def _save(self, item: FileItem) -> str:
        """Save the provided file to the given filename in the storage
        container. Returns the name of the file saved.
        """
        # If the filename is modified to save it properly, return the new
        # filename. This might happen if the library can detect that the name
        # might conflict and to pick a new one.
        # The FileItem has sync and async read and seek methods to provide the
        # data in different ways.
        #
        #     data = item.sync_read()
        # or
        #     data = await item.async_read()
        pass

    # async def _async_delete(self, item: FileItem) -> None:
    def _delete(self, item: FileItem) -> None:
        """Delete the given item from the storage container, whether or not
        it exists.
        """
        pass
