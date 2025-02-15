from asyncio import Future, isfuture
from io import BytesIO

import pytest
from mock import Mock

from filestorage import FileItem, StorageContainer, FilterBase
from filestorage.exceptions import FilestorageConfigError
from filestorage.handlers import DummyHandler, AsyncDummyHandler


@pytest.fixture
def store():
    return StorageContainer()


@pytest.fixture
def handler():
    return DummyHandler()


def test_different_paths():
    handlers = [
        DummyHandler(path=("foo",)),
        DummyHandler(path=("foo")),
        DummyHandler(path=["foo"]),
        DummyHandler(path="foo"),
    ]

    for handler in handlers:
        assert handler.path == ("foo",)


def test_validate():
    filter1 = Mock()
    filter2 = Mock()
    handler = DummyHandler(filters=[filter1, filter2])

    validate_result = handler.validate()

    assert validate_result is None
    assert handler.validated
    filter1.validate.assert_called()
    filter2.validate.assert_called()


def test_validate_async_filter():
    filter1 = Mock()
    filter1.validate.return_value = Future()
    handler = DummyHandler(filters=[filter1])

    validate_result = handler.validate()

    assert isfuture(validate_result)
    assert handler.validated
    filter1.validate.assert_called()


@pytest.mark.asyncio
async def test_validate_async_handler():
    handler = AsyncDummyHandler()

    handler.validate()

    assert handler.validated


@pytest.mark.asyncio
async def test_validate_bad_async_filter():
    filter1 = Mock()
    filter1.async_ok = False
    handler = AsyncDummyHandler(filters=[filter1])

    with pytest.raises(FilestorageConfigError) as err:
        await handler.validate()

    assert "cannot be used" in str(err.value)


def test_get_item():
    handler = DummyHandler(path=["foo"])
    item = handler.get_item("file.txt")

    assert isinstance(item, FileItem)
    assert item == FileItem(filename="file.txt", path=("foo",))


@pytest.mark.parametrize(
    ("dirty", "clean"),
    [
        ["..foo", "foo"],
        ["foo..", "foo.."],
        ["../foo", "_foo"],
        ["/.foo", "_.foo"],
        ["a b c", "a_b_c"],
        ["a/b/c", "a_b_c"],
        ["1/2/3", "1_2_3"],
        ["☺", "_"],
    ],
)
def test_sanitize_filename(handler, dirty, clean):
    assert handler.sanitize_filename(dirty) == clean


def test_get_url():
    handler = AsyncDummyHandler(base_url="http://eppx.com")

    assert handler.get_url("file.txt") == "http://eppx.com/file.txt"


def test_get_size(handler):
    handler.save_data(data=b"contents", filename="file.txt")

    item_size = handler.last_save_contents
    assert len(item_size) == handler.get_size("file.txt")


def test_get_accessed_time(handler):
    handler.save_data(data=b"contents", filename="file.txt")

    atime = handler.files["file.txt"].atime
    assert atime == handler.get_accessed_time("file.txt")


def test_get_created_time(handler):
    handler.save_data(data=b"contents", filename="file.txt")

    ctime = handler.files["file.txt"].ctime
    assert ctime == handler.get_created_time("file.txt")


def test_get_modified_time(handler):
    handler.save_data(data=b"contents", filename="file.txt")

    mtime = handler.files["file.txt"].mtime
    assert mtime == handler.get_modified_time("file.txt")


def test_save_file(handler):
    handler.save_data(data=b"contents", filename="file.txt")

    item = handler.last_save
    assert item.filename == "file.txt"
    with item as f:
        assert f.read() == b"contents"


@pytest.mark.asyncio
async def test_async_save_file():
    handler = AsyncDummyHandler()
    await handler.async_save_data(data=b"contents", filename="file.txt")

    item = handler.last_save
    assert item.filename == "file.txt"
    with item as f:
        assert f.read() == b"contents"


def test_save_field(handler):
    class Field:
        """Mimic old cgi.FieldStorage object."""

        filename = "file.txt"
        file = BytesIO(b"contents")

    # headers = {"content-disposition": "attachment; filename=file.txt"}
    # field = cgi.FieldStorage(headers=headers)
    # field.file = BytesIO(b"contents")

    handler.save_field(Field)

    item = handler.last_save
    assert item.filename == "file.txt"
    with item as f:
        assert f.read() == b"contents"


def test_delete_file(handler):
    assert not handler.exists("file.txt")

    handler.save_data(data=b"contents", filename="file.txt")
    assert handler.exists("file.txt")

    handler.delete("file.txt")
    assert not handler.exists("file.txt")


@pytest.mark.asyncio
async def test_async_delete_file():
    handler = AsyncDummyHandler()
    assert not await handler.async_exists("file.txt")

    await handler.async_save_data(data=b"contents", filename="file.txt")
    assert await handler.async_exists("file.txt")

    await handler.async_delete("file.txt")
    assert not await handler.async_exists("file.txt")


def test_subfolder_save(store, handler):
    store.handler = handler
    subfolder = store / "a" / "b"

    subfolder.save_data(data=b"contents", filename="file.txt")

    item = handler.last_save
    assert item.filename == "file.txt"
    assert item.path == ("a", "b")
    with item as f:
        assert f.read() == b"contents"


def test_subfolder_delete_file(store, handler):
    store.handler = handler
    subfolder = store / "a" / "b"
    assert not subfolder.exists("file.txt")

    subfolder.save_data(data=b"contents", filename="file.txt")
    assert subfolder.exists("file.txt")

    subfolder.delete("file.txt")
    assert not subfolder.exists("file.txt")


class MockFilter(FilterBase):
    def __init__(self, id_: str):
        self.mock = Mock()
        self.id_ = id_

    def _apply(self, item: FileItem) -> FileItem:
        self.mock._apply(item)
        # append the id_ to the filename
        return item.copy(filename=item.filename + self.id_)


def test_calls_filter(store):
    filter1 = MockFilter("-1")
    filter2 = MockFilter("-2")
    store.handler = DummyHandler(filters=[filter1, filter2])
    result = store.save_data(data=b"contents", filename="file.txt")

    filter1.mock._apply.assert_called()
    filter2.mock._apply.assert_called()
    assert result == "file.txt-1-2"


def test_filter_class_not_instance():
    """When the library user accidentally passes in the class instead of
    an instance of the class, handle the problem and prompt for the likely
    solution.
    """
    handler = DummyHandler(filters=[MockFilter])
    with pytest.raises(FilestorageConfigError) as err:
        handler.validate()

    assert str(err.value) == (
        "Filter MockFilter is a class, not an instance. "
        'Did you mean to use "filters=[MockFilter()]" instead?'
    )


def test_subfolder_get_url(store):
    store.handler = DummyHandler(base_url="http://foo.bar")
    subfolder = store / "folder"

    assert subfolder.base_url == "http://foo.bar"
    assert subfolder.get_url("test.txt") == "http://foo.bar/folder/test.txt"
