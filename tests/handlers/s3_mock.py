from datetime import datetime

import botocore  # type: ignore


# Mock the AWS async resources that we'll be using
# AsyncMock is available in Python 3.8, but to keep things working with older
# versions, these explicit objects will provide the necessary mocking.


class MockS3AsyncObject:
    def __init__(self, bucket_name, filename):
        self._bucket_name = bucket_name
        self._filename = filename
        self._deleted = False

    async def delete(self):
        self._deleted = True


class MockS3AsyncBucket:
    def __init__(self, name):
        self._name = name
        self._upload_fileobj_file = None
        self._upload_fileobj_filename = None
        self._upload_fileobj_call_args = None

    async def upload_fileobj(self, file, filename, **kwargs):
        self._upload_fileobj_file = file
        self._upload_fileobj_filename = filename
        self._upload_fileobj_call_args = kwargs
        return None


class Meta:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MockS3AsyncResource:
    def __init__(self, make_object_missing=False):
        self._make_object_missing = make_object_missing
        self._file_object = None
        self._bucket = None
        self.meta = Meta(
            client=MockS3AsyncClient(make_object_missing=make_object_missing)
        )

    async def Object(self, bucket_name, filename):
        self._file_object = MockS3AsyncObject(bucket_name, filename)
        return self._file_object

    async def Bucket(self, bucket_name):
        self._bucket = MockS3AsyncBucket(bucket_name)
        return self._bucket


class MockS3AsyncClient:
    def __init__(self, make_object_missing=False):
        self._make_object_missing = make_object_missing
        self._head_object_kwargs = None

    async def head_object(self, **kwargs):
        self._head_object_kwargs = kwargs
        if self._make_object_missing:
            raise botocore.exceptions.ClientError(
                operation_name="head_object",
                error_response={
                    "Error": {"Code": "404"},
                },
            )
        # Perhaps there is a better way to mock this
        return {"ContentLength": "8", "LastModified": datetime(2015, 1, 1)}


class MockAsyncContext:
    def __init__(self, item):
        self.item = item
        self.called = False

    async def __aenter__(self):
        self.called = True
        return self.item

    async def __aexit__(self, exc_type, exc, tb):
        assert not exc
