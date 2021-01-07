import pytest

from filestorage import StorageContainer, store as default_store
from filestorage.handlers import DummyHandler


@pytest.fixture
def storage():
    return StorageContainer()


def test_check_the_default_storage():
    """A single storage instance is created by default. Ensure it's correct."""
    assert isinstance(default_store, StorageContainer)


def test_validate_handler(storage):
    storage.handler = DummyHandler()

    assert not storage.handler.validated

    storage.finalize_config()

    assert storage.handler.validated
