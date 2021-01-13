from filestorage import (
    AsyncStorageHandlerBase as AsyncStorageHandlerBase,
    FileItem as FileItem,
)
from filestorage.exceptions import (
    FilestorageConfigError as FilestorageConfigError,
)
from typing import Any, Optional

class AioBotoS3ResourceContext:
    async def __aenter__(self) -> None: ...
    async def __aexit__(
        self, exc_type: str, exc: Exception, tb: Any
    ) -> Any: ...

TypeACL: Any
TypeAddressingStyle: Any

class S3Handler(AsyncStorageHandlerBase):
    bucket_name: Any = ...
    acl: Any = ...
    host_url: Any = ...
    secret_key: Any = ...
    access_key: Any = ...
    aio_config_params: Any = ...
    def __init__(
        self,
        bucket_name: str,
        acl: TypeACL = ...,
        secret_key: Optional[str] = ...,
        access_key: Optional[str] = ...,
        region: Optional[str] = ...,
        host_url: Optional[str] = ...,
        addressing_style: TypeAddressingStyle = ...,
        connect_timeout: int = ...,
        num_retries: int = ...,
        read_timeout: int = ...,
        keepalive_timeout: int = ...,
        **kwargs: Any
    ) -> None: ...
    async def test_credentials(self) -> None: ...
    @property
    def resource(self) -> AioBotoS3ResourceContext: ...
    async def get_bucket(self, resource: Any): ...
