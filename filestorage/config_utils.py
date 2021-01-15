import importlib
from typing import Any, Dict, List, Tuple

from filestorage import StorageHandlerBase, FilterBase, StorageContainer
from filestorage.exceptions import FilestorageConfigError


def try_import(default_module: str, model: str):
    """Attempt to import the given name."""
    module_name, _, cls_name = model.rpartition('.')
    module_name = module_name or default_module
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, cls_name)
    except (ImportError):
        raise ValueError('module not installed')
    except AttributeError:
        raise ValueError('bad class name')

    return cls


def setup_from_config(
    config: Dict[str, str], store: StorageContainer, key_prefix: str = 'store'
):
    """Setup the provided store with the config dictionary.
    Will only pay attention to keys that start with the key_prefix.

    The config will not be finalized.
    """
    # Convert the flat dict to a nested dict where the same delimiters are
    # grouped together.
    config_dict = get_keys_from(key_prefix, config)

    # If there's configuration to be had, setup the store with it.
    if config_dict:
        setup_store(store, key_prefix, '', config_dict)
    else:
        # Otherwise, assume that the store isn't going to be used now
        store.handler = None


def setup_store(
    store: StorageContainer, key_prefix: str, name: str, config_dict: Dict
):
    """Setup a specific store to the given name in the config_dict.
    key_prefix denotes where this name came from (for good error messages).
    """
    name = name or ''
    try:
        handler_class_name = config_dict['handler'][None]
    except KeyError:
        raise FilestorageConfigError(
            f'Pyramid config has no key for {key_prefix}{name}.handler'
        )
    if handler_class_name.lower() == 'none':
        handler = None
    else:
        handler = get_handler(key_prefix + name, config_dict['handler'])

    config_dict.pop('handler')

    store.handler = handler

    # Setup any sub-store configuration
    for key, sub_config in config_dict.items():
        if key.startswith('[') and key.endswith(']'):
            sub_store = key.lstrip('[').rstrip(']').strip('"').strip("'")
            setup_store(
                store=store[sub_store],
                key_prefix=key_prefix + key,
                name=key,
                config_dict=sub_config,
            )
        else:
            raise FilestorageConfigError(
                f'Pyramid config unknown key {key_prefix}{key}'
            )


def get_handler(key_prefix: str, config_dict: Dict) -> StorageHandlerBase:
    name = f'{key_prefix}.handler'
    handler_name = config_dict.pop(None)
    try:
        handler_cls = try_import('filestorage.handlers', handler_name)
    except ValueError:
        raise FilestorageConfigError(f'Pyramid config bad value for {name}')

    kwargs = {}
    for key, value in config_dict.items():
        if key == 'filters':
            kwargs['filters'] = get_all_filters(name, value)
        else:
            kwargs[key] = decode_kwarg(value)

    try:
        return handler_cls(**kwargs)
    except Exception as err:
        raise FilestorageConfigError(
            f'Pyramid config bad args for {name}: {err}'
        )


def get_all_filters(key_prefix: str, config_dict: Dict) -> List[FilterBase]:
    """Get all the filters from within the config_dict"""
    filters: List[Tuple[int, FilterBase]] = []
    for filter_ref, filter_dict in config_dict.items():
        filter_prefix = f'{key_prefix}.filters{filter_ref}'
        try:
            filter_id = int(filter_ref.lstrip('[').rstrip(']'))
        except Exception as err:
            raise FilestorageConfigError(
                f'Pyramid config bad key {key_prefix}{filter_ref}: {err}'
            )
        filters.append((filter_id, get_filter(filter_prefix, filter_dict)))

    filters.sort()
    return [filter for ref, filter in filters]


def get_filter(key_prefix: str, config_dict: Dict) -> FilterBase:
    """Get a single filter from within the config_dict"""
    filter_name = config_dict.pop(None)
    try:
        filter_cls = try_import('filestorage.filters', filter_name)
    except ValueError:
        raise FilestorageConfigError(
            f'Pyramid config bad value for {key_prefix}'
        )

    kwargs = {key: decode_kwarg(value) for key, value in config_dict.items()}
    try:
        return filter_cls(**kwargs)
    except Exception as err:
        raise FilestorageConfigError(
            f'Pyramid config bad args for {key_prefix}: {err}'
        )


def unquote(value: str) -> str:
    """Removes the prefix and suffix if they are identical quotes"""
    if value[0] in {'"', "'"} and value[0] == value[-1]:
        return value[1:-1]
    return value


def decode_kwarg(value) -> Any:
    if isinstance(value, dict):
        try:
            value = value.pop(None)
        except KeyError:
            raise ValueError(f'decode_kwarg got an invalid dict: {value!r}')
        return decode_kwarg(value)

    if not isinstance(value, str):
        raise ValueError(f'decode_kwarg expected a str, got: {value!r}')
    if value.startswith('[') and value.endswith(']'):
        # handle lists
        try:
            return eval(value, {}, {})
        except Exception as err:
            raise FilestorageConfigError(
                f'Pyramid config bad value {value}: {err}'
            )

    if value.isdigit():
        return int(value)

    return unquote(value)


# store.handler = S3Handler
# store.handler.bucket_name = static
# store.handler.filters[0] = RandomizeFilename
# store.handler.filters[1] = ValidateExtension
# store.handler.filters[1].extensions = ['jpg', 'png']

# store['test'].handler = DummyHandler
# store['test'].handler.base_url = http://foo.bar

# Turns into:

# {
#     None: {
#         'handler': {
#             None: 'S3Handler',
#             'bucket_name': 'static',
#             'filters': {
#                 '[0]': {None: 'RandomizeFilename'},
#                 '[1]': {
#                     None: 'ValidateExtension',
#                     'extensions': "['jpg', 'png']",
#                 },
#             },
#         }
#     },
#     "['test']": {
#         'handler': {
#             None: 'DummyHandler',
#             'base_url': 'http://foo.bar',
#         }
#     },
# }


def get_keys_from(prefix: str, config: Dict) -> Dict:
    """Get nested dicts from a dictionary of . separated keys"""
    result: Dict = {}
    for key, value in config.items():
        if key.startswith(f'{prefix}.') or key.startswith(f'{prefix}['):
            set_nested_value(key, value, result)

    return result.get(prefix, {})


def set_nested_value(key: str, value: str, result: Dict) -> Dict:
    """Modify the provided result dict in-place with the value at the key"""
    sub = result
    # Add a . to each [ to make the parsing delimiter consistent:
    # 'foo[0][1]' to 'foo.[0].[1]'
    key = key.replace('[', '.[')
    for part in key.split('.'):
        sub = sub.setdefault(part, {})
    sub[None] = value.strip()
    return result
