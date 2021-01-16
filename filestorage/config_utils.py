import difflib
import inspect
import importlib
from typing import Any, Dict, List, Tuple, Set

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


def get_init_properties(cls, to_class=object) -> Set[str]:
    """Given a class, determine the properties that class needs.
    Assumes that each sub-class will call super with **kwargs. (Which is not a
    good general assumption, but should work well enough for Handlers.)

    cls is the class to check, to_class is the final parent class to check.

    Returns a set of all parameters found.
    """
    result = set()
    init = getattr(cls, '__init__', None)

    if init is not None:
        for param in inspect.signature(init).parameters.values():
            if param.kind == param.VAR_KEYWORD:
                # Ignore any **kwargs
                continue
            if param.name == 'self':
                continue

            result.add(param.name)

    if issubclass(cls.mro()[1], to_class):
        result |= get_init_properties(cls.mro()[1], to_class)

    return result


def setup_from_settings(
    settings: Dict[str, str],
    store: StorageContainer,
    key_prefix: str = 'store',
) -> bool:
    """Setup the provided store with the settings dictionary.
    Will only pay attention to keys that start with the key_prefix.

    The config will not be finalized.

    Returns True if a handler was setup, False otherwise.
    """
    # Convert the flat dict to a nested dict where the same delimiters are
    # grouped together.
    settings_dict = get_keys_from(key_prefix, settings)

    # If there's configuration to be had, setup the store with it.
    if settings_dict:
        setup_store(store, key_prefix, '', settings_dict)
        return True
    else:
        # Otherwise, assume that the store isn't going to be used now
        store.handler = None
        return False


def setup_store(
    store: StorageContainer, key_prefix: str, name: str, settings_dict: Dict
):
    """Setup a specific store to the given name in the settings_dict.
    key_prefix denotes where this name came from (for good error messages).
    """
    name = name or ''
    try:
        handler_class_name = settings_dict['handler'][None]
    except KeyError:
        raise FilestorageConfigError(
            f'Pyramid settings has no key for {key_prefix}{name}.handler'
        )
    if handler_class_name.lower() == 'none':
        handler = None
    else:
        handler = get_handler(key_prefix + name, settings_dict['handler'])

    settings_dict.pop('handler')

    store.handler = handler

    # Setup any sub-store configuration
    for key, sub_config in settings_dict.items():
        if key.startswith('[') and key.endswith(']'):
            sub_store = key.lstrip('[').rstrip(']').strip('"').strip("'")
            setup_store(
                store=store[sub_store],
                key_prefix=key_prefix + key,
                name=key,
                settings_dict=sub_config,
            )
        else:
            raise FilestorageConfigError(
                f'Pyramid settings unknown key {key_prefix}.{key}'
            )


def get_handler(key_prefix: str, settings_dict: Dict) -> StorageHandlerBase:
    name = f'{key_prefix}.handler'
    handler_name = settings_dict.pop(None)
    try:
        handler_cls = try_import('filestorage.handlers', handler_name)
    except ValueError:
        raise FilestorageConfigError(f'Pyramid settings bad value for {name}')

    valid_args = get_init_properties(handler_cls, StorageHandlerBase)

    kwargs = {}
    for key, value in settings_dict.items():
        if key not in valid_args:
            maybe = difflib.get_close_matches(key, valid_args, 1)
            maybe_txt = ''
            if maybe:
                maybe_txt = f' Did you mean "{name}.{maybe[0]}"?'
            raise FilestorageConfigError(
                f'Pyramid invalid setting "{name}.{key}". {maybe_txt}'
            )
        if key == 'filters':
            kwargs['filters'] = get_all_filters(name, value)
        else:
            kwargs[key] = decode_kwarg(value)

    try:
        return handler_cls(**kwargs)
    except Exception as err:
        raise FilestorageConfigError(
            f'Pyramid settings bad args for {name}: {err}'
        )


def get_all_filters(key_prefix: str, settings_dict: Dict) -> List[FilterBase]:
    """Get all the filters from within the settings_dict"""
    filters: List[Tuple[int, FilterBase]] = []
    for filter_ref, filter_dict in settings_dict.items():
        filter_prefix = f'{key_prefix}.filters{filter_ref}'
        try:
            filter_id = int(filter_ref.lstrip('[').rstrip(']'))
        except Exception as err:
            raise FilestorageConfigError(
                f'Pyramid settings bad key {key_prefix}{filter_ref}: {err}'
            )
        filters.append((filter_id, get_filter(filter_prefix, filter_dict)))

    filters.sort()
    return [filter for ref, filter in filters]


def get_filter(key_prefix: str, settings_dict: Dict) -> FilterBase:
    """Get a single filter from within the settings_dict"""
    filter_name = settings_dict.pop(None)
    try:
        filter_cls = try_import('filestorage.filters', filter_name)
    except ValueError:
        raise FilestorageConfigError(
            f'Pyramid settings bad value for {key_prefix}'
        )

    kwargs = {key: decode_kwarg(value) for key, value in settings_dict.items()}
    try:
        return filter_cls(**kwargs)
    except Exception as err:
        raise FilestorageConfigError(
            f'Pyramid settings bad args for {key_prefix}: {err}'
        )


def unquote(value: str) -> str:
    """Removes the prefix and suffix if they are identical quotes"""
    if value[0] in {'"', "'"} and value[0] == value[-1]:
        return value[1:-1]
    return value


def decode_kwarg(value) -> Any:
    """Tries to determine what the kwarg should be. Decode lists, dicts, sets
    and integers.
    """
    if isinstance(value, dict):
        try:
            value = value.pop(None)
        except KeyError:
            raise ValueError(f'decode_kwarg got an invalid dict: {value!r}')
        return decode_kwarg(value)

    if not isinstance(value, str):
        raise ValueError(f'decode_kwarg expected a str, got: {value!r}')
    if (value.startswith('[') and value.endswith(']')) or (
        value.startswith('{') and value.endswith('}')
    ):
        # handle lists, sets and dicts
        try:
            return eval(value, {}, {})
        except Exception as err:
            raise FilestorageConfigError(
                f'Pyramid settings bad value {value}: {err}'
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


def get_keys_from(prefix: str, settings: Dict) -> Dict:
    """Get nested dicts from a dictionary of . separated keys"""
    result: Dict = {}
    for key, value in settings.items():
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
