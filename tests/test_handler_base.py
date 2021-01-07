import cgi
from asyncio import Future, isfuture
from io import BytesIO

import pytest
from mock import Mock

from filestorage import FileItem, StorageContainer
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
        DummyHandler(path=('foo',)),
        DummyHandler(path=('foo')),
        DummyHandler(path=['foo']),
        DummyHandler(path='foo'),
    ]

    for handler in handlers:
        assert handler.path == ('foo',)


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

    await handler.validate()

    assert handler.validated


@pytest.mark.asyncio
async def test_validate_bad_async_filter():
    filter1 = Mock()
    filter1.async_ok = False
    handler = AsyncDummyHandler(filters=[filter1])

    with pytest.raises(FilestorageConfigError) as err:
        await handler.validate()

    assert 'cannot be used' in str(err.value)


def test_get_item():
    handler = DummyHandler(path=['foo'])
    item = handler.get_item('file.txt')

    assert isinstance(item, FileItem)
    assert item == FileItem(filename='file.txt', path=('foo',))


@pytest.mark.parametrize(
    ('dirty', 'clean'),
    [
        ['..foo', 'foo'],
        ['foo..', 'foo..'],
        ['../foo', '_foo'],
        ['/.foo', '_.foo'],
        ['a b c', 'a_b_c'],
        ['a/b/c', 'a_b_c'],
        ['1/2/3', '1_2_3'],
        ['☺', '_'],
    ],
)
def test_sanitize_filename(handler, dirty, clean):
    assert handler.sanitize_filename(dirty) == clean


def test_save_file(handler):
    handler.save_data(data=b'contents', filename='file.txt')

    assert handler.last_save.filename == 'file.txt'
    assert handler.last_save.sync_read() == b'contents'


@pytest.mark.asyncio
async def test_async_save_file():
    handler = AsyncDummyHandler()
    await handler.save_data(data=b'contents', filename='file.txt')

    assert handler.last_save.filename == 'file.txt'
    assert handler.last_save.sync_read() == b'contents'


def test_save_field(handler):
    headers = {'content-disposition': 'attachment; filename=file.txt'}
    field = cgi.FieldStorage(headers=headers)
    field.file = BytesIO(b'contents')
    handler.save_field(field)

    assert handler.last_save.filename == 'file.txt'
    assert handler.last_save.sync_read() == b'contents'


def test_delete_file(handler):
    assert not handler.exists('file.txt')

    handler.save_data(data=b'contents', filename='file.txt')
    assert handler.exists('file.txt')

    handler.delete('file.txt')
    assert not handler.exists('file.txt')


@pytest.mark.asyncio
async def test_async_delete_file():
    handler = AsyncDummyHandler()
    assert not await handler.exists('file.txt')

    await handler.save_data(data=b'contents', filename='file.txt')
    assert await handler.exists('file.txt')

    await handler.delete('file.txt')
    assert not await handler.exists('file.txt')


def test_subfolder_save(store, handler):
    store.handler = handler
    subfolder = store / 'a' / 'b'

    subfolder.save_data(data=b'contents', filename='file.txt')

    assert handler.last_save.filename == 'file.txt'
    assert handler.last_save.path == ('a', 'b')
    assert handler.last_save.sync_read() == b'contents'


def test_subfolder_delete_file(store, handler):
    store.handler = handler
    subfolder = store / 'a' / 'b'
    assert not subfolder.exists('file.txt')

    subfolder.save_data(data=b'contents', filename='file.txt')
    assert subfolder.exists('file.txt')

    subfolder.delete('file.txt')
    assert not subfolder.exists('file.txt')
