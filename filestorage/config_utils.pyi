from filestorage import (
    FilterBase as FilterBase,
    StorageContainer as StorageContainer,
    StorageHandlerBase as StorageHandlerBase,
)
from filestorage.exceptions import (
    FilestorageConfigError as FilestorageConfigError,
)
from typing import Any, Dict, List, Set

def try_import(default_module: str, model: str) -> Any: ...
def get_init_properties(cls: Any, to_class: Any = ...) -> Set[str]: ...
def setup_from_settings(
    settings: Dict[str, str], store: StorageContainer, key_prefix: str = ...
) -> bool: ...
def setup_store(
    store: StorageContainer, key_prefix: str, name: str, settings_dict: Dict
) -> Any: ...
def get_handler(key_prefix: str, settings_dict: Dict) -> StorageHandlerBase: ...
def get_all_filters(key_prefix: str, settings_dict: Dict) -> List[FilterBase]: ...
def get_filter(key_prefix: str, settings_dict: Dict) -> FilterBase: ...
def unquote(value: str) -> str: ...
def decode_kwarg(value: Any) -> Any: ...
def get_keys_from(prefix: str, settings: Dict) -> Dict: ...
def set_nested_value(key: str, value: str, result: Dict) -> Dict: ...
