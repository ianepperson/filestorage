from asyncio import get_event_loop, isfuture, iscoroutine
from typing import Awaitable, cast, Dict, Optional, Union

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
        handler = self.handler
        if handler is None:
            raise FilestorageConfigError(
                f'No handler provided for store{self.name}'
            )
        return cast(StorageHandlerBase, handler)

    @property
    def async_handler(self) -> AsyncStorageHandlerBase:
        handler = self.handler
        if not isinstance(handler, AsyncStorageHandlerBase):
            raise FilestorageConfigError(
                f'No async handler provided for store{self.name}'
            )

        return cast(AsyncStorageHandlerBase, handler)

    @property
    def handler(
        self,
    ) -> Union[StorageHandlerBase, AsyncStorageHandlerBase, None]:
        if self._do_not_use:
            return None
        if self._handler is None:
            raise FilestorageConfigError(
                f'No handler provided for store{self.name}'
            )
        return self._handler

    @handler.setter
    def handler(self, handler: Optional[StorageHandlerBase]) -> None:
        """Set the handler for this store"""
        if self._finalized:
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: store already finalized!'
            )
        if handler is None:
            self._handler = None
            self._do_not_use = True
            return

        if not isinstance(handler, StorageHandlerBase):
            raise FilestorageConfigError(
                f'Setting store{self.name}.handler: '
                f'{handler!r} is not a StorageHandler'
            )
        self._do_not_use = False
        # Inject the handler name
        handler.handler_name = self._name
        self._handler = handler

    async def async_finalize_config(self) -> None:
        """Validate the config and prevent any further config changes."""
        if self._finalized:
            return

        if self._do_not_use:
            return

        if self._handler is None:
            raise FilestorageConfigError(
                f'No handler provided for store{self.name}'
            )

        result = self._handler.validate()
        if iscoroutine(result) or isfuture(result):
            await cast(Awaitable, result)

        self._finalized = True

        for child in self._children.values():
            await child.async_finalize_config()

    def finalize_config(self) -> None:
        event_loop = get_event_loop()
        if event_loop.is_running():
            raise FilestorageConfigError(
                'Async event loop is already running. '
                'Must await store.async_finalize_config() instead.'
            )
        event_loop.run_until_complete(self.async_finalize_config())

    def __getitem__(self, key: str) -> 'StorageContainer':
        """Get or create a storage container as a lookup.
        The provided container will be lazily configured.
        """
        if self._finalized and key not in self._children:
            raise FilestorageConfigError(
                f'Getting store{self.name}[{key!r}]: store already finalized!'
            )
        return self._children.setdefault(
            key, StorageContainer(name=key, parent=self)
        )
