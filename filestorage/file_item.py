import os
from typing import NamedTuple, Optional, Tuple, BinaryIO

from . import utils


class FileItem(NamedTuple):
    filename: str
    path: Tuple[str, ...] = tuple()
    data: Optional[BinaryIO] = None

    def __repr__(self) -> str:
        has_data = 'no data' if self.data is None else 'with data'
        return (
            f'<FileItem filename:{self.filename!r} '
            f'path:{self.path!r} {has_data}>'
        )

    @property
    def url_path(self) -> str:
        """A relative URL path string for this path/filename"""
        return '/'.join(self.path + (self.filename,))

    @property
    def fs_path(self) -> str:
        """A relative file system path string for this path/filename"""
        return os.path.join(*self.path, self.filename)

    def copy(self, **kwargs) -> 'FileItem':
        filename = kwargs.get('filename', self.filename)
        path = kwargs.get('path', self.path)
        data = kwargs.get('data', self.data)

        return FileItem(filename=filename, path=path, data=data)

    def sync_read(self, size: Optional[int] = -1) -> bytes:
        if self.data is None:
            return b''

        return utils.any_to_sync(self.data.read)(size)

    async def async_read(self, size: Optional[int] = -1) -> bytes:
        if self.data is None:
            return b''

        return await utils.any_to_async(self.data.read)(size)

    def sync_seek(self, offset: int) -> int:
        if self.data is None:
            return 0

        return utils.any_to_sync(self.data.seek)(offset)

    async def async_seek(self, offset: int) -> int:
        if self.data is None:
            return 0

        return await utils.any_to_async(self.data.seek)(offset)
