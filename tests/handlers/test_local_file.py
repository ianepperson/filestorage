import os
import pytest
from datetime import datetime
from tempfile import TemporaryDirectory

from filestorage import StorageContainer
from filestorage.exceptions import FilestorageConfigError
from filestorage.handlers import LocalFileHandler, AsyncLocalFileHandler


@pytest.fixture
def store():
    return StorageContainer()


@pytest.fixture
def directory():
    # Make a new directory and provide the path as a string.
    # Will remove the directory when complete.
    with TemporaryDirectory() as tempdir:
        yield tempdir


def exists(directory: str, filename: str) -> bool:
    """Check if the given file exists in the given directory.
    It's synchronous, but it's probably fine for a test.
    """
    return os.path.exists(os.path.join(directory, filename))


def get_contents(directory: str, filename: str) -> bytes:
    path = os.path.join(directory, filename)
    with open(path, 'rb') as f:
        return f.read()


def test_auto_create_directory(directory):
    directory = os.path.join(directory, 'folder', 'subfolder')
    handler = LocalFileHandler(base_path=directory, auto_make_dir=True)

    assert not os.path.exists(directory)
    handler.validate()

    assert os.path.exists(directory)


def test_error_when_no_directory(directory):
    directory = os.path.join(directory, 'folder', 'subfolder')
    handler = LocalFileHandler(base_path=directory)

    with pytest.raises(FilestorageConfigError) as err:
        handler.validate()

    assert directory.rstrip('/').rstrip('\\') in str(err.value)
    assert 'does not exist' in str(err.value)


def test_local_file_handler_save(directory):
    handler = LocalFileHandler(base_path=directory)

    handler.save_data(filename='test.txt', data=b'contents')

    assert exists(directory, 'test.txt')
    assert get_contents(directory, 'test.txt') == b'contents'


def test_local_file_handler_try_save_subfolder(directory, store):
    store.handler = LocalFileHandler(base_path=directory, auto_make_dir=True)
    handler = store / 'folder' / 'subfolder'

    handler.save_data(filename='test.txt', data=b'contents')

    directory = os.path.join(directory, 'folder', 'subfolder')
    assert exists(directory, 'test.txt')
    assert get_contents(directory, 'test.txt') == b'contents'


def test_local_file_save_same_filename(directory):
    handler = LocalFileHandler(base_path=directory)

    first = handler.save_data(filename='test.txt', data=b'contents 1')
    second = handler.save_data(filename='test.txt', data=b'contents 2')
    third = handler.save_data(filename='test.txt', data=b'contents 3')

    assert first == 'test.txt'
    assert second == 'test-1.txt'
    assert third == 'test-2.txt'

    assert exists(directory, first)
    assert exists(directory, second)
    assert exists(directory, third)

    assert get_contents(directory, first) == b'contents 1'
    assert get_contents(directory, second) == b'contents 2'
    assert get_contents(directory, third) == b'contents 3'


def test_local_file_handler_exists(directory):
    handler = LocalFileHandler(base_path=directory)
    assert not exists(directory, 'test.txt')

    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')


def test_local_file_handler_size(directory):
    handler = LocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')
    assert handler.size('test.txt') == 8


def test_local_file_handler_get_accessed_time(directory):
    handler = LocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    atime = handler.get_accessed_time('test.txt')
    assert atime == datetime.fromtimestamp(os.path.getatime(handler.local_path(item)))


def test_local_file_handler_get_created_time(directory):
    handler = LocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    ctime = handler.get_created_time('test.txt')
    assert ctime == datetime.fromtimestamp(os.path.getctime(handler.local_path(item)))


def test_local_file_handler_get_modified_time(directory):
    handler = LocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    mtime = handler.get_modified_time('test.txt')
    assert mtime == datetime.fromtimestamp(os.path.getmtime(handler.local_path(item)))


def test_local_file_handler_delete(directory):
    handler = LocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    handler.delete(filename='test.txt')

    assert not exists(directory, 'test.txt')


# Async tests #


def test_async_auto_create_directory(directory):
    directory = os.path.join(directory, 'folder', 'subfolder')
    handler = AsyncLocalFileHandler(base_path=directory, auto_make_dir=True)
    assert not os.path.exists(directory)

    handler.validate()

    assert os.path.exists(directory)


def test_async_error_when_no_directory(directory):
    directory = os.path.join(directory, 'folder', 'subfolder')
    handler = AsyncLocalFileHandler(base_path=directory)

    with pytest.raises(FilestorageConfigError) as err:
        handler.validate()

    assert directory.rstrip('/').rstrip('\\') in str(err.value)
    assert 'does not exist' in str(err.value)


def test_async_validate_when_no_sync(directory):
    directory = os.path.join(directory, 'folder', 'subfolder')
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False, auto_make_dir=True
    )
    assert not os.path.exists(directory)

    handler.validate()

    assert os.path.exists(directory)


@pytest.mark.asyncio
async def test_async_local_file_handler_save(directory):
    handler = AsyncLocalFileHandler(base_path=directory)

    await handler.async_save_data(filename='test.txt', data=b'contents')

    assert exists(directory, 'test.txt')
    assert get_contents(directory, 'test.txt') == b'contents'


@pytest.mark.asyncio
async def test_async_local_file_handler_exists(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    assert not exists(directory, 'test.txt')
    await handler.async_save_data(filename='test.txt', data=b'contents')

    assert exists(directory, 'test.txt')


@pytest.mark.asyncio
async def test_async_local_file_handler_size(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    await handler.async_save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')
    assert await handler.async_size('test.txt') == 8


@pytest.mark.asyncio
async def test_async_local_file_handler_get_accessed_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    await handler.async_save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    atime = await handler.async_get_accessed_time('test.txt')
    assert atime == datetime.fromtimestamp(os.path.getatime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_local_file_handler_get_created_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    await handler.async_save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    ctime = await handler.async_get_created_time('test.txt')
    assert ctime == datetime.fromtimestamp(os.path.getctime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_local_file_handler_get_modified_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    await handler.async_save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    mtime = await handler.async_get_modified_time('test.txt')
    assert mtime == datetime.fromtimestamp(os.path.getmtime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_local_file_handler_delete(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    await handler.async_save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    await handler.async_delete(filename='test.txt')

    assert not exists(directory, 'test.txt')


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_save(directory):
    handler = AsyncLocalFileHandler(base_path=directory)

    handler.save_data(filename='test.txt', data=b'contents')

    assert exists(directory, 'test.txt')
    assert get_contents(directory, 'test.txt') == b'contents'


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_exists(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    assert not exists(directory, 'test.txt')

    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_size(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')
    assert handler.size('test.txt') == 8


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_get_accessed_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    atime = handler.get_accessed_time('test.txt')
    assert atime == datetime.fromtimestamp(os.path.getatime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_get_created_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    ctime = handler.get_created_time('test.txt')
    assert ctime == datetime.fromtimestamp(os.path.getctime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_get_modified_time(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    item = handler.get_item('test.txt')
    mtime = handler.get_modified_time('test.txt')
    assert mtime == datetime.fromtimestamp(os.path.getmtime(handler.local_path(item)))


@pytest.mark.asyncio
async def test_async_to_sync_local_file_handler_delete(directory):
    handler = AsyncLocalFileHandler(base_path=directory)
    handler.save_data(filename='test.txt', data=b'contents')
    assert exists(directory, 'test.txt')

    handler.delete(filename='test.txt')

    assert not exists(directory, 'test.txt')


@pytest.mark.asyncio
async def test_async_local_file_handler_try_save_subfolder(directory, store):
    store.handler = AsyncLocalFileHandler(
        base_path=directory, auto_make_dir=True
    )
    handler = store / 'folder' / 'subfolder'

    await handler.async_save_data(filename='test.txt', data=b'contents')

    directory = os.path.join(directory, 'folder', 'subfolder')
    assert exists(directory, 'test.txt')
    assert get_contents(directory, 'test.txt') == b'contents'


@pytest.mark.asyncio
async def test_async_local_file_save_same_filename(directory):
    handler = AsyncLocalFileHandler(base_path=directory)

    first = await handler.async_save_data(
        filename='test.txt', data=b'contents 1'
    )
    second = await handler.async_save_data(
        filename='test.txt', data=b'contents 2'
    )
    third = await handler.async_save_data(
        filename='test.txt', data=b'contents 3'
    )

    assert first == 'test.txt'
    assert second == 'test-1.txt'
    assert third == 'test-2.txt'

    assert exists(directory, first)
    assert exists(directory, second)
    assert exists(directory, third)

    assert get_contents(directory, first) == b'contents 1'
    assert get_contents(directory, second) == b'contents 2'
    assert get_contents(directory, third) == b'contents 3'


def test_async_only_save(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.save_data(filename='test.txt', data=b'contents')

    assert str(err.value) == 'Sync save method not allowed'


def test_async_only_exists(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.exists(filename='test.txt')

    assert str(err.value) == 'Sync exists method not allowed'


@pytest.mark.asyncio
async def test_async_only_size(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.size(filename='test.txt')

    assert str(err.value) == 'Sync exists method not allowed'


@pytest.mark.asyncio
async def test_async_only_get_accessed_time(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.get_accessed_time(filename='test.txt')

    assert str(err.value) == 'Sync exists method not allowed'


@pytest.mark.asyncio
async def test_async_only_get_created_time(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.get_created_time(filename='test.txt')

    assert str(err.value) == 'Sync exists method not allowed'


@pytest.mark.asyncio
async def test_async_only_get_modified_time(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.get_modified_time(filename='test.txt')

    assert str(err.value) == 'Sync exists method not allowed'


def test_async_only_delete(directory):
    handler = AsyncLocalFileHandler(
        base_path=directory, allow_sync_methods=False
    )

    with pytest.raises(RuntimeError) as err:
        handler.delete(filename='test.txt')

    assert str(err.value) == 'Sync delete method not allowed'
