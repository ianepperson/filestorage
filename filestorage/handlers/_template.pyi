import abc
from filestorage import (
    FileItem as FileItem,
    StorageHandlerBase as StorageHandlerBase,
)
from filestorage.exceptions import (
    FilestorageConfigError as FilestorageConfigError,
)
from typing import Any

class NewStorageHandler(StorageHandlerBase, metaclass=abc.ABCMeta):
    def __init__(self, **kwargs: Any) -> None: ...
