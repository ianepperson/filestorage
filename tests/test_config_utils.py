import pytest

from filestorage import config_utils, StorageContainer
from filestorage.exceptions import FilestorageConfigError


@pytest.fixture
def store():
    return StorageContainer()


def test_set_nested_value():
    result = {}
    key = "foo.bar.baz"
    value = "value"

    config_utils.set_nested_value(key, value, result)

    assert result["foo"]["bar"]["baz"][None] == value


def test_set_nested_value_with_bracket():
    result = {}
    key = "foo.bar[2].baz"
    value = "value"

    config_utils.set_nested_value(key, value, result)

    assert result["foo"]["bar"]["[2]"]["baz"][None] == value


def test_get_keys_from():
    settings = {
        "foo.bar.baz": "first",
        "foo.bar.bang": "second",
        "something.else": "third",
        "foot.and.mouth": "nope",
        "foo[1].bar.bang": "second1",
    }

    key_dict = config_utils.get_keys_from("foo", settings)
    assert key_dict == {
        "bar": {"baz": {None: "first"}, "bang": {None: "second"}},
        "[1]": {"bar": {"bang": {None: "second1"}}},
    }


def test_setup_handler_with_filters(store):
    settings = {
        "store.handler": "DummyHandler",
        "store.handler.filters[0]": "RandomizeFilename",
        "store.handler.filters[1]": "ValidateExtension",
        "store.handler.filters[1].extensions": "['jpg', 'png']",
    }
    config_utils.setup_from_settings(settings, store)
    store.finalize_config()

    assert store.handler.__class__.__name__ == "DummyHandler"
    assert store.handler.filters[0].__class__.__name__ == "RandomizeFilename"
    assert store.handler.filters[1].__class__.__name__ == "ValidateExtension"
    assert store.handler.filters[1].extensions == {"jpg", "png"}


def test_setup_two_handlers(store):
    settings = {
        "store.handler": "DummyHandler",
        "store.handler.base_url": "//base",
        'store["foo"].handler': "DummyHandler",
        'store["foo"].handler.base_url': "//base.foo",
    }
    config_utils.setup_from_settings(settings, store)

    assert store.handler.base_url == "//base"
    assert store["foo"].handler.base_url == "//base.foo"


def test_setup_nested_handlers(store):
    settings = {
        "store.handler": "None",
        'store["foo"].handler': "DummyHandler",
        'store["foo"].handler.base_url': "//base.foo",
        'store["foo"]["bar"].handler': "DummyHandler",
        'store["foo"]["bar"].handler.base_url': "//base.foo.bar",
    }
    config_utils.setup_from_settings(settings, store)
    store.finalize_config()

    assert store.handler is None
    assert store["foo"].handler.base_url == "//base.foo"
    assert store["foo"]["bar"].handler.base_url == "//base.foo.bar"


def test_handler_full_name(store):
    settings = {
        "store.handler": "filestorage.handlers.DummyHandler",
    }
    config_utils.setup_from_settings(settings, store)
    store.finalize_config()

    assert store.handler.__class__.__name__ == "DummyHandler"


def test_missing_required_parameter(store):
    settings = {
        "store.handler": "DummyHandler",
        "store.handler.filters[0]": "ValidateExtension",
        # 'store.handler.filters[0].extensions': "['jpg', 'png']",
    }
    with pytest.raises(FilestorageConfigError) as err:
        config_utils.setup_from_settings(settings, store)

    assert "store.handler.filters[0]" in str(err.value)
    assert "missing 1 required positional argument: 'extensions'" in str(
        err.value
    )


def test_decode_ints_and_strings(store):
    settings = {
        "store.handler": "DummyHandler",
        # The URL isn't really checked well and could be a number
        "store.handler.base_url": "5",
        'store["six"].handler': "DummyHandler",
        # The quotes should force it to be a string
        'store["six"].handler.base_url': '"6"',
    }
    config_utils.setup_from_settings(settings, store)

    assert store.handler.base_url == 5
    assert store["six"].handler.base_url == "6"


def test_suggest_filters(store):
    settings = {
        "store.handler": "DummyHandler",
        "store.handler.filter[0]": "ValidateExtension",
        "store.handler.filter[0].extensions": "['jpg', 'png']",
    }
    with pytest.raises(FilestorageConfigError) as err:
        config_utils.setup_from_settings(settings, store)

    assert 'invalid setting "store.handler.filter"' in str(err.value)
    assert 'Did you mean "store.handler.filters"' in str(err.value)
