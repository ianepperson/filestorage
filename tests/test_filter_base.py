import pytest

from filestorage import FileItem, FilterBase, AsyncFilterBase
from filestorage.handlers import DummyHandler, AsyncDummyHandler


class SimpleFilter(FilterBase):
    async_ok = True

    def _apply(self, item: FileItem) -> FileItem:
        return item.copy(filename="filtered_name.txt")


class FailedFilter(FilterBase):
    async_ok = True

    def _apply(self, item: FileItem) -> FileItem:
        raise RuntimeError("called a FailedFilter")


class AsyncSimpleFilter(AsyncFilterBase):
    def _apply(self, item: FileItem) -> FileItem:
        return item.copy(filename="filtered_name.txt")


class AsyncFailedFilter(AsyncFilterBase):
    def _apply(self, item: FileItem) -> FileItem:
        raise RuntimeError("called a FailedFilter")


@pytest.mark.parametrize("Filter", [SimpleFilter, AsyncSimpleFilter])
def test_sync_filter_call(Filter):
    handler = DummyHandler(filters=[Filter()])

    handler.save_data(data=b"contents", filename="file.txt")

    item = handler.last_save
    assert item.filename == "filtered_name.txt"
    with item as f:
        assert f.read() == b"contents"


@pytest.mark.parametrize("Filter", [FailedFilter, AsyncFailedFilter])
def test_sync_filter_bad_call(Filter):
    handler = DummyHandler(filters=[Filter()])

    with pytest.raises(RuntimeError) as err:
        handler.save_data(data=b"contents", filename="file.txt")

    assert str(err.value) == "called a FailedFilter"


@pytest.mark.parametrize("Filter", [SimpleFilter, AsyncSimpleFilter])
@pytest.mark.asyncio
async def test_async_filter_call(Filter):
    handler = AsyncDummyHandler(filters=[Filter()])

    await handler.async_save_data(data=b"contents", filename="file.txt")

    item = handler.last_save
    assert item.filename == "filtered_name.txt"
    with item as f:
        assert f.read() == b"contents"


@pytest.mark.parametrize("Filter", [FailedFilter, AsyncFailedFilter])
@pytest.mark.asyncio
async def test_async_filter_bad_call(Filter):
    handler = AsyncDummyHandler(filters=[Filter()])

    with pytest.raises(RuntimeError) as err:
        await handler.async_save_data(data=b"contents", filename="file.txt")

    assert str(err.value) == "called a FailedFilter"
