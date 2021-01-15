import codecs
import os
from .file_item import FileItem
from .storage_container import StorageContainer
from .handler_base import StorageHandlerBase, AsyncStorageHandlerBase
from .filter_base import FilterBase, AsyncFilterBase

# with open('VERSION', 'r', encoding='utf-8') as version_file:
#     __version__ = version_file.read().strip()


def _read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


__version__ = _read('VERSION').strip()

# Instantiate the store singleton
store = StorageContainer()


__all__ = [
    'store',
    'StorageContainer',
    'StorageHandlerBase',
    'AsyncStorageHandlerBase',
    'FileItem',
    'FilterBase',
    'AsyncFilterBase',
    'exceptions',
    'handlers',
    'filters',
    'pyramid_config',
    'config_utils',
]
