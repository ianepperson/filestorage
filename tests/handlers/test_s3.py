import pytest
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
