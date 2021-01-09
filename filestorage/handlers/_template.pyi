from filestorage import (
    FileItem as FileItem,
    StorageHandlerBase as StorageHandlerBase,
)
from filestorage.exceptions import (
    FilestorageConfigError as FilestorageConfigError,
)
from typing import Any

class NewStorageHandler(StorageHandlerBase):
    def __init__(self, **kwargs: Any) -> None: ...
