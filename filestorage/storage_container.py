from asyncio import gather, get_event_loop, isfuture, iscoroutine
from typing import Awaitable, List, Optional

from .exceptions import FilestorageConfigError
from .handler_base import StorageHandlerBase, SubFolder


class StorageContainer:
    """A class for handling storage configuration and retrieval.

    This is intended to be a singleton and contains global storage
    configurations that are lazily populated.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        parent: Optional['StorageContainer'] = None,
    ):
        self._name = name
        self._parent = parent
        self._children = {}
        self._handler = None
        self._filters = []
        self._finalized = False

    # Define all the function calls that will populate when the handler is set.
    exists: Optional[StorageHandlerBase.ExistsMethodType] = None
    delete: Optional[StorageHandlerBase.DeleteMethodType] = None
    save_file: Optional[StorageHandlerBase.SaveFileMethodType] = None
    save_field: Optional[StorageHandlerBase.SaveFieldMethodType] = None
    save_data: Optional[StorageHandlerBase.SaveDataMethodType] = None
    get_url: Optional[StorageHandlerBase.GetUrlMethodType] = None

    def _populate_handler_methods(self, handler: StorageHandlerBase) -> None:
        """Populate the public handler methods on this object"""
        self.exists = handler.exists
        self.delete = handler.delete
        self.save_file = handler.save_file
        self.save_field = handler.save_field
        self.save_data = handler.save_data
        self.get_url = handler.get_url

    @property
    def name(self) -> str:
        """Provide a name for this container based on its lineage"""
        parent = ''
        if self._parent is not None:
            parent = self._parent.name
        if self._name is None:
            return parent
        return f'{parent}[{repr(self._name)}]'

    @property
    def finalized(self) -> bool:
        return self._finalized

    @property
    def handler(self) -> StorageHandlerBase:
        if self._handler is None:
            raise FilestorageConfigError(
                f'No handler provided for store{self.name}'
            )
        return self._handler

    @handler.setter
    def handler(self, handler: StorageHandlerBase) -> None:
        """Set the handler for this store"""
        if self._finalized:
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: store already finalized!'
            )
        if self._handler is not None:
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: handler already set!'
            )
        if not isinstance(handler, StorageHandlerBase):
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: '
                f'{handler!r} is not a StorageHandler'
            )
        # Inject the handler name
        handler.handler_name = self._name
        self._handler = handler
        self._populate_handler_methods(handler)

    def finalize_config(
        self, coroutines: Optional[List[Awaitable]] = None
    ) -> None:
        """Validate the config and prevent any further config changes.

        If any of the validation returns a coroutine, add it to the coroutines
        list for running in parallel.
        """
        if self._finalized:
            return
        self._finalized = True

        if self._handler is None:
            raise FilestorageConfigError(
                f'No handler provided for store{self.name}'
            )

        # Indicate that this instance of the method should await any coroutines
        should_await = False
        if coroutines is None:
            should_await = True
            coroutines = []

        result = self._handler.validate()
        if iscoroutine(result) or isfuture(result):
            coroutines.append(result)

        for child in self._children.values():
            child.finalize_config(coroutines)

        if should_await and coroutines:
            # Get the coroutines to run in parallel
            results = gather(*coroutines)
            # Run them to completion before returning (synchronously)
            event_loop = get_event_loop()
            event_loop.run_until_complete(results)

    def subfolder(self, folder_name: str) -> SubFolder:
        """Get a subfolder for this container."""
        return SubFolder(store=self, path=(folder_name,))

    def __truediv__(self, other: str) -> SubFolder:
        """Get a new subfolder when using the divide operator.

        Allows building a path with path-looking code:
            new_store = store / 'folder' / 'subfolder'
        """
        return self.subfolder(other)

    def __getitem__(self, key: str) -> 'StorageContainer':
        """Get or create a storage container as a lookup.
        The provided container will be lazily configured.
        """
        return self._children.setdefault(
            key, StorageContainer(name=key, parent=self)
        )
