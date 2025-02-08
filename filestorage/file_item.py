import mimetypes
import os
from typing import NamedTuple, Optional, Tuple, BinaryIO

from . import utils


class SyncReader:
    """
    Returned when item is used as a context manager.

    > with item as f: -> SyncReader
    >     assert f.read() == b"contents"
    """

    def __init__(self, item: "FileItem"):
        self.data = item.data
        self.filename = item.filename
        if self.data is not None:
            self._reader = utils.any_to_sync(self.data.read)
            self._seeker = utils.any_to_sync(self.data.seek)

    def seek(self, offset: int) -> int:
        if self.data is None:
            return -1
        return self._seeker(offset)

    def read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b""
        return self._reader(size)

    closed = False


class AsyncReader:
    """
    Returned when item is used as an async context manager.

    > async with item as f: -> AsyncReader
    >     assert await f.read() == b"contents"
    """

    def __init__(self, item: "FileItem"):
        self.data = item.data
        self.filename = item.filename
        if self.data is not None:
            self._reader = utils.any_to_async(self.data.read)
            self._seeker = utils.any_to_async(self.data.seek)

    async def seek(self, offset: int) -> int:
        if self.data is None:
            return -1
        return await self._seeker(offset)

    async def read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b""
        return await self._reader(size)

    closed = False


class FileItem(NamedTuple):
    """
    Object containing a file and its metadata.

    To be altered by a Filter of type FilterBase, and
    stored with a Storage Handler of type StorageHandlerBase.
    """

    filename: str
    path: Tuple[str, ...] = tuple()
    data: Optional[BinaryIO] = None
    media_type: Optional[str] = None  # Formerly known as MIME-type

    def copy(self, **kwargs) -> "FileItem":
        """
        Make a copy of this FileItem, updating the properties from the kwargs.
        """
        filename = kwargs.get("filename", self.filename)
        path = kwargs.get("path", self.path)
        data = kwargs.get("data", self.data)
        media_type = kwargs.get("media_type", self.media_type)

        return FileItem(
            filename=filename, path=path, data=data, media_type=media_type
        )

    def __repr__(self) -> str:
        has_data = "no data" if self.data is None else "with data"
        return (
            f"<FileItem filename:{self.filename!r} "
            f"path:{self.path!r} {has_data}>"
        )

    @property
    def has_data(self) -> bool:
        """Indicate if this file contains any data."""
        return self.data is not None

    @property
    def url_path(self) -> str:
        """A relative URL path string for this path/filename"""
        return "/".join(self.path + (self.filename,))

    @property
    def fs_path(self) -> str:
        """A relative file system path string for this path/filename"""
        return os.path.join(*self.path, self.filename)

    @property
    def content_type(self) -> Optional[str]:
        """Indicate the MIME type of the content."""
        if self.media_type is not None:
            return self.media_type
        return mimetypes.guess_type(self.filename)[0]

    # Implement the syncronous read handler context.
    #
    # Allows using:
    #
    # > with item as f: -> SyncReader
    # >     assert f.read() == b"contents"

    def __enter__(self):
        reader = SyncReader(self)
        reader.seek(0)
        return reader

    def __exit__(self, *_, **__):
        pass

    # Implement the asyncronous read handler context.
    #
    # Allows using:
    #
    # > async with item as f: -> AsyncReader
    # >     assert await f.read() == b"contents"

    async def __aenter__(self):
        reader = AsyncReader(self)
        await reader.seek(0)
        return reader

    async def __aexit__(self, *_, **__):
        pass
