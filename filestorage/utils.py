from asyncio import iscoroutinefunction

from typing import (
    Awaitable,
    cast,
    Callable,
    TypeVar,
    Union,
)

# asgiref doesn't yet have type info
from asgiref import sync  # type: ignore

T = TypeVar('T')
R = TypeVar('R')

AsyncCallable = Callable[[T], Awaitable[R]]
SyncCallable = Callable[[T], R]
MaybeAsyncCallable = Union[SyncCallable, AsyncCallable]


def sync_to_async(fn: SyncCallable, thread_sensitive=True) -> AsyncCallable:
    return cast(
        AsyncCallable,
        sync.sync_to_async(fn, thread_sensitive=thread_sensitive),
    )


def async_to_sync(fn: AsyncCallable) -> SyncCallable:
    return cast(SyncCallable, sync.async_to_sync(fn))


def any_to_async(
    fn: MaybeAsyncCallable, thread_sensitive=True
) -> AsyncCallable:
    if iscoroutinefunction(fn):
        return fn
    return sync_to_async(fn, thread_sensitive=thread_sensitive)


def any_to_sync(fn: MaybeAsyncCallable) -> SyncCallable:
    """Convert either an async or sync function into a sync function"""
    if iscoroutinefunction(fn):
        return async_to_sync(fn)
    return fn
