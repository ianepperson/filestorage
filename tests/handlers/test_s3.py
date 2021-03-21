import pytest
from datetime import datetime
from io import BytesIO

from filestorage.handlers import S3Handler
from . import s3_mock


@pytest.fixture
def mock_s3_resource(mocker):
    resource = s3_mock.MockS3AsyncResource()
    contextualized = s3_mock.MockAsyncContext(resource)
    mocker.patch(
        'filestorage.handlers.S3Handler.resource',
        new=contextualized,
    )
    return resource


@pytest.fixture
def mock_s3_resource_failure(mocker):
    resource = s3_mock.MockS3AsyncResource(make_object_missing=True)
    contextualized = s3_mock.MockAsyncContext(resource)
    mocker.patch(
        'filestorage.handlers.S3Handler.resource',
        new=contextualized,
    )
    return resource


@pytest.fixture
def handler():
    return S3Handler(bucket_name='bucket')


@pytest.fixture
def async_only_handler():
    return S3Handler(bucket_name='bucket', allow_sync_methods=False)


@pytest.mark.asyncio
async def test_validate(mock_s3_resource, handler):
    await handler.validate()


@pytest.mark.asyncio
async def test_async_exists(mock_s3_resource, handler):
    item = handler.get_item('foo.txt')

    assert await handler._async_exists(item)


def test_exists(mock_s3_resource, handler):
    item = handler.get_item('foo.txt')

    assert handler._exists(item)


def test_not_exists(mock_s3_resource_failure, handler):
    item = handler.get_item('foo.txt')

    assert not handler._exists(item)


@pytest.mark.asyncio
async def test_async_size(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    assert await handler._async_size(item) == 8


def test_size(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    assert handler._size(item) == 8


@pytest.mark.asyncio
async def test_async_get_accessed_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(NotImplementedError) as err:
        await handler._async_get_accessed_time(item)

    assert str(err.value) == 'get_accessed_time is not supported with the S3 handler'


def test_get_accessed_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(NotImplementedError) as err:
        handler._get_accessed_time(item)

    assert str(err.value) == 'get_accessed_time is not supported with the S3 handler'


@pytest.mark.asyncio
async def test_async_get_created_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(NotImplementedError) as err:
        await handler._async_get_created_time(item)

    assert str(err.value) == 'get_created_time is not supported with the S3 handler'


def test_get_created_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(NotImplementedError) as err:
        handler._get_created_time(item)

    assert str(err.value) == 'get_created_time is not supported with the S3 handler'


@pytest.mark.asyncio
async def test_async_get_modified_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    assert await handler._async_get_modified_time(item) == datetime(2015, 1, 1)


def test_get_modified_time(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    assert handler._get_modified_time(item) == datetime(2015, 1, 1)


@pytest.mark.asyncio
async def test_async_save(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    await handler._async_save(item)

    call_args = mock_s3_resource._bucket._upload_fileobj_call_args
    assert call_args == {
        'ExtraArgs': {'ACL': 'public-read', 'ContentType': 'text/plain'}
    }


def test_save(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', data=BytesIO(b'contents'))

    handler._save(item)

    call_args = mock_s3_resource._bucket._upload_fileobj_call_args
    assert call_args == {
        'ExtraArgs': {'ACL': 'public-read', 'ContentType': 'text/plain'}
    }


@pytest.mark.asyncio
async def test_async_delete(mock_s3_resource, handler):
    item = handler.get_item('foo.txt')

    await handler._async_delete(item)

    assert mock_s3_resource._file_object._deleted


def test_delete(mock_s3_resource, handler):
    item = handler.get_item('foo.txt')

    handler._delete(item)

    assert mock_s3_resource._file_object._deleted


# When allow_sync_methods is False, these should all throw a RuntimeError


def test_cant_save(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._save(item)

    assert str(err.value) == 'Sync save method not allowed'


def test_cant_exists(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._exists(item)

    assert str(err.value) == 'Sync exists method not allowed'


def test_cant_size(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._size(item)

    assert str(err.value) == 'Sync exists method not allowed'


def test_cant_get_accessed_time(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._get_accessed_time(item)

    assert str(err.value) == 'Sync exists method not allowed'


def test_cant_get_created_time(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._get_created_time(item)

    assert str(err.value) == 'Sync exists method not allowed'


def test_cant_get_modified_time(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._get_modified_time(item)

    assert str(err.value) == 'Sync exists method not allowed'


def test_cant_delete(async_only_handler):
    item = async_only_handler.get_item('foo.txt', data=BytesIO(b'contents'))

    with pytest.raises(RuntimeError) as err:
        async_only_handler._delete(item)

    assert str(err.value) == 'Sync delete method not allowed'


@pytest.mark.asyncio
async def test_async_save_in_folder(mock_s3_resource, handler):
    item = handler.get_item(
        'foo.txt', data=BytesIO(b'contents'), subpath=('folder',)
    )

    await handler._async_save(item)

    assert (
            mock_s3_resource._bucket._upload_fileobj_filename == 'folder/foo.txt'
    )


@pytest.mark.asyncio
async def test_async_delete_in_folder(mock_s3_resource, handler):
    item = handler.get_item('foo.txt', subpath=('folder',))

    await handler._async_delete(item)

    assert mock_s3_resource._file_object._deleted
    assert mock_s3_resource._file_object._filename == 'folder/foo.txt'
