from asyncio import gather, get_event_loop, isfuture, iscoroutine
from typing import Awaitable, cast, Dict, List, Optional, Union

from .exceptions import FilestorageConfigError
from .handler_base import (
    AsyncStorageHandlerBase,
    StorageHandlerBase,
    Folder,
)


class StorageContainer(Folder):
    """A class for handling storage configuration and retrieval.

    This is intended to be a singleton and contains global storage
    configurations that are lazily populated.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        parent: Optional['StorageContainer'] = None,
    ):
        # Init the folder superclass
        super().__init__(store=self, path=tuple())

        self._name: Optional[str] = name
        self._parent = parent
        self._children: Dict[str, 'StorageContainer'] = {}
        self._handler: Optional[StorageHandlerBase] = None
        self._do_not_use = False
        self._finalized = False

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
    def do_not_use(self) -> bool:
        return self._do_not_use

    @property
    def sync_handler(self) -> StorageHandlerBase:
        return cast(StorageHandlerBase, self.handler)

    @property
    def async_handler(self) -> AsyncStorageHandlerBase:
        handler = self.handler
        if not isinstance(handler, AsyncStorageHandlerBase):
            raise FilestorageConfigError(
                f'No async handler provided for store{self.name}'
            )

        return cast(AsyncStorageHandlerBase, handler)

    @property
    def handler(self) -> Union[StorageHandlerBase, AsyncStorageHandlerBase]:
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
        if self._do_not_use:
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: do_not_use already set!'
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

    def set_do_not_use(self) -> None:
        """Indicate that this container should not be used."""
        if self._finalized:
            raise FilestorageConfigError(
                f'Setting store{self.name}.set_do_not_use(): '
                'store already finalized!'
            )
        if self._handler is not None:
            raise FilestorageConfigError(
                f'Setting store{self.name}.set_do_not_use(): '
                'a handler is already set!'
            )
        self._do_not_use = True

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

        if self._do_not_use:
            return

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
            coroutines.append(cast(Awaitable, result))

        for child in self._children.values():
            child.finalize_config(coroutines)

        if should_await and coroutines:
            # Get the coroutines to run in parallel
            results = gather(*coroutines)
            # Run them to completion before returning (synchronously)
            event_loop = get_event_loop()
            event_loop.run_until_complete(results)

    def __getitem__(self, key: str) -> 'StorageContainer':
        """Get or create a storage container as a lookup.
        The provided container will be lazily configured.
        """
        return self._children.setdefault(
            key, StorageContainer(name=key, parent=self)
        )
