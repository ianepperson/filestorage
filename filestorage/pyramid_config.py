"""Configure the store from settings in a Pyramid configuration file.

store.handler = S3Handler
store.handler.bucket_name = static
store.handler.filters[0] = RandomizeFilename
store.handler.filters[1] = ValidateExtension
store.handler.filters[1].extensions = ['jpg', 'png']

store['test'].handler = DummyHandler
store['test'].handler.base_url = http://foo.bar
"""

from filestorage import store
from filestorage.config_utils import setup_from_config


def get_store():
    return store


def includeme(config):
    # Add the store object to every request.
    name = config.registry.settings.get('store.name', 'store')
    config.add_request_method(get_store, name, True)

    setup_from_config(store, config.registry.settings)
    store.finalize_config()
