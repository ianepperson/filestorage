import asyncio
import io
import os
from typing import NamedTuple, Optional, Tuple


class FileItem(NamedTuple):
    filename: str
    path: Tuple[str, ...] = tuple()
    data: Optional[io.BytesIO] = None

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
        new_values = {
            'filename': self.filename,
            'path': self.path,
            'data': self.data,
        }

        new_values.update(kwargs)
        return FileItem(**new_values)

    def sync_read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b''

        if asyncio.iscoroutinefunction(self.data.read):
            event_loop = asyncio.get_event_loop()
            return event_loop.run_until_complete(self.data.read(size))
        else:
            return self.data.read(size)

    async def async_read(self, size: int = -1) -> bytes:
        if self.data is None:
            return b''

        if asyncio.iscoroutinefunction(self.data.read):
            return await self.data.read(size)
        else:
            return self.data.read(size)

    def sync_seek(self, offset: int) -> int:
        if self.data is None:
            return 0

        if asyncio.iscoroutinefunction(self.data.seek):
            event_loop = asyncio.get_event_loop()
            return event_loop.run_until_complete(self.data.seek(offset))
        else:
            return self.data.seek(offset)

    async def async_seek(self, offset: int) -> int:
        if self.data is None:
            return 0

        if asyncio.iscoroutinefunction(self.data.seek):
            return await self.data.seek(offset)
        else:
            return self.data.seek(offset)
