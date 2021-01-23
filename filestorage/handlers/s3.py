import uuid
from io import BytesIO
from typing import Awaitable, Optional

from filestorage import AsyncStorageHandlerBase, FileItem
from filestorage.exceptions import FilestorageConfigError

try:
    # The Literal type was introduced in Python 3.8
    from typing import Literal
except ImportError:
    Literal = None  # type: ignore

try:
    import aioboto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
    from aiobotocore.config import AioConfig  # type: ignore

    # Typing for boto3 is a pain, and typing for aioboto3 is even worse.
    # 'boto3-stubs[s3]' should help, but...
    # from mypy_boto3_s3 import S3ServiceResource - doesn't provide aioboto3
    # types.

except ImportError:
    aioboto3 = None


class AioBotoS3ResourceContext:
    async def __aenter__(self):
        ...

    async def __aexit__(self, exc_type: str, exc: Exception, tb):
        ...


if Literal is not None:
    # Python 3.8 +
    TypeACL = Literal[
        'private',
        'public-read',
        'public-read-write',
        'authenticated-read',
        'aws-exec-read',
        'bucket-owner-read',
        'bucket-owner-full-control',
        'log-delivery-write',
    ]

    # https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/s3.html
    # #changing-the-addressing-style
    TypeAddressingStyle = Literal[None, 'auto', 'path', 'virtual']
else:
    # Python 3.7
    TypeACL = str  # type: ignore
    TypeAddressingStyle = Optional[str]  # type: ignore


class S3Handler(AsyncStorageHandlerBase):
    """Class for storing files in an S3 service"""

    def __init__(
        self,
        bucket_name: str,
        acl: TypeACL = 'public-read',
        profile_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        region_name: Optional[str] = None,
        host_url: Optional[str] = None,
        addressing_style: TypeAddressingStyle = None,
        connect_timeout: int = 5,
        num_retries: int = 5,
        read_timeout: int = 10,
        keepalive_timeout: int = 12,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.bucket_name = bucket_name
        self.acl = acl
        self.host_url = host_url
        self.profile_name = profile_name
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_access_key_id = aws_access_key_id
        self.aws_session_token = aws_session_token

        # parameters passed to the AioConfig object
        self.aio_config_params = {
            'connect_timeout': connect_timeout,
            'read_timeout': read_timeout,
            'connector_args': {
                'keepalive_timeout': keepalive_timeout,
            },
            'retries': {
                'max_attempts': num_retries,
            },
        }

        if addressing_style:
            self.aio_config_params['s3'] = {
                'addressing_style': addressing_style
            }

        if region_name:
            self.aio_config_params['region_name'] = region_name

        self.__memoized_conn_options = None

    @property
    def __conn_options(self):
        # Memoize the connection options
        if self.__memoized_conn_options:
            return self.__memoized_conn_options

        self.__memoized_conn_options = {
            'config': AioConfig(**self.aio_config_params)
        }

        # This could be blank if the dev wants to use the local auth mechanisms
        # for AWS - either environment variables:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/
        #  guide/configuration.html#using-environment-variables
        # or a config file at ~/.aws.config:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/
        #  guide/configuration.html#using-a-configuration-file

        # Convert these secrets to str to support some secret handlers that
        # only provide the values when asked for as strings.
        if self.aws_access_key_id:
            self.__memoized_conn_options.update(
                {
                    'aws_access_key_id': str(self.aws_access_key_id),
                    'aws_secret_access_key': str(self.aws_secret_access_key),
                }
            )
            # Not well hidden, but might as well make it less visible
            self.aws_secret_access_key = '(hidden)'
            self.aws_access_key_id = '(hidden)'

        if self.aws_session_token:
            self.__memoized_conn_options['aws_session_token'] = str(
                self.aws_session_token
            )
            self.aws_session_token = '(hidden)'

        if self.profile_name:
            self.__memoized_conn_options['profile_name'] = str(
                self.profile_name
            )

        # The endpoint_url isn't part of the configuration.
        if self.host_url:
            self.__memoized_conn_options['endpoint_url'] = str(self.host_url)
        return self.__memoized_conn_options

    async def _validate(self) -> Optional[Awaitable]:
        """Perform any setup or validation."""
        if aioboto3 is None:
            raise FilestorageConfigError(
                'aioboto3 library required but not installed.'
            )

        # Call this in order to populate the options
        self.__conn_options
        return await self.test_credentials()

    async def test_credentials(self):
        """Perform a read, check, delete set of operations on a dummy file."""
        item = self.get_item(
            filename=f'__delete_me__{uuid.uuid4()}.txt',
            data=BytesIO(b'Credential test run from the filestorage library.'),
        )
        async with self.resource as s3:
            filename = await self._async_save(item, s3)
            item = self.get_item(filename=filename)
            await self._async_exists(item, s3)
            await self._async_delete(item, s3)

    @property
    def resource(self) -> 'AioBotoS3ResourceContext':
        """Provide a context manager for accessing the S3 resources.

        async with handler.resource as s3:
            pass

        If the bare client is needed:

        async with handler.resource as s3:
            client = s3.meta.client
        """
        return aioboto3.resource('s3', **self.__conn_options)

    async def get_bucket(self, resource):
        return await resource.Bucket(self.bucket_name)  # type: ignore

    async def _async_exists(self, item: FileItem, s3=None) -> bool:
        """Indicate if the given file exists within the given folder."""
        if s3 is None:
            # If not called with the s3 context, do it again.
            async with self.resource as s3:
                return await self._async_exists(item, s3)

        try:
            await s3.meta.client.head_object(
                Bucket=self.bucket_name, Key=item.url_path
            )
        except ClientError as err:
            if int(err.response.get('Error', {}).get('Code')) == 404:
                return False
            raise
        return True

    async def _async_save(self, item: FileItem, s3=None) -> str:
        """Save the provided file to the given filename in the storage
        container. Returns the name of the file saved.
        """
        extra = {'ACL': self.acl, 'ContentType': item.content_type}

        if s3 is None:
            # If not called with the s3 context, do it again.
            async with self.resource as s3:
                return await self._async_save(item, s3)

        bucket = await self.get_bucket(s3)
        with item as f:
            # It would be nice if there were a good way to use the async read
            # from here, but the aioboto3 doesn't support it. Instead, the
            # entire file contents are read into memory then transferred to S3.
            await bucket.upload_fileobj(
                f, item.url_path, ExtraArgs=extra
            )  # type: ignore

        return item.filename

    async def _async_delete(self, item: FileItem, s3=None) -> None:
        """Delete the given item from the storage container, whether or not
        it exists.
        """
        if s3 is None:
            # If not called with the s3 context, do it again.
            async with self.resource as s3:
                await self._async_delete(item, s3)

        file_object = await s3.Object(self.bucket_name, item.url_path)
        await file_object.delete()
