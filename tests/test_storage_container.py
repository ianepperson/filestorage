from asyncio import Future

import pytest
from mock import Mock

from filestorage import StorageContainer, store as default_store
from filestorage.handlers import DummyHandler
from filestorage.exceptions import FilestorageConfigError


@pytest.fixture
def store():
    return StorageContainer()


@pytest.fixture
def handler(store):
    return DummyHandler(base_url='http://eppx.com/', path=('static',))


@pytest.fixture
def async_handler(store):
    handler = DummyHandler()
    handler.validate = Mock()
    handler.validate.return_value = Future()
    handler.validate.return_value.set_result(None)
    return handler


def test_check_the_default_storage():
    """A single storage instance is created by default. Ensure it's correct."""
    assert isinstance(default_store, StorageContainer)


def test_validate_handler(store, handler):
    store.handler = handler
    assert not store.finalized
    assert not store.handler.validated

    store.finalize_config()

    assert store.finalized
    assert store.handler.validated


def test_do_not_use(store):
    assert not store.do_not_use
    store.handler = None
    assert store.do_not_use

    # Can now finalize without errors and without config
    store.finalize_config()


def test_use_after_do_not_use_config(store, handler):
    store.handler = None
    store.handler = handler

    assert not store.do_not_use


def test_validate_async_handler(store, handler, async_handler):
    store.handler = handler
    store['a'].handler = async_handler

    store.finalize_config()

    async_handler.validate.assert_called()


def test_child_stores_naming(store):
    sub_a = store['a']
    sub_b = store['a']['b']

    assert not store.name
    assert sub_a.name == "['a']"
    assert sub_b.name == "['a']['b']"


def test_cant_get_children_after_final(store, handler):
    store.handler = handler
    store.finalize_config()

    with pytest.raises(FilestorageConfigError) as err:
        store['a']

    assert str(err.value) == "Getting store['a']: store already finalized!"


def test_path_by_div(store, handler):
    sub_a = store / 'a'
    sub_b = sub_a / 'b'
    store.handler = handler

    sub_b.save_data(filename='new_file.txt', data=b'As a cucumber.')

    item = store.handler.last_save
    assert item.sync_read() == b'As a cucumber.'
    assert item.url_path == 'static/a/b/new_file.txt'


def test_bad_handler_setting(store):
    with pytest.raises(FilestorageConfigError) as err:
        # Handler must be a handler!
        store.handler = 'foo'

    assert (
        str(err.value)
        == "Setting store.handler: 'foo' is not a StorageHandler"
    )


def test_finalized_without_setting(store):
    with pytest.raises(FilestorageConfigError) as err:
        store.finalize_config()

    assert str(err.value) == 'No handler provided for store'


def test_finalized_without_setting_substore(store, handler):
    store.handler = handler
    store_b = store['b']  # noqa

    with pytest.raises(FilestorageConfigError) as err:
        store.finalize_config()

    assert str(err.value) == "No handler provided for store['b']"


def test_finalized_finalizes_all_substores(store, handler):
    store.handler = handler
    handler_a = DummyHandler()
    handler_b = DummyHandler()
    handler_ac = DummyHandler()
    store['a'].handler = handler_a
    store['b'].handler = handler_b
    store['a']['c'].handler = handler_ac

    store.finalize_config()

    assert handler_a.validated
    assert handler_b.validated
    assert handler_ac.validated
