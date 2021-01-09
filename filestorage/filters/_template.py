# Use this as a template for creating new filter classes
from typing import Awaitable, Optional

# If creating an awaitable filter, use AsyncFilterBase instead and use
# async _apply(self, item).
from filestorage import FilterBase, FileItem


class NewFilter(FilterBase):
    """My new filter!"""

    # Indicate if this class can be used within a coroutine.
    # If all actions are performed in-memory, this can be True.
    # If any actions block syncronously (such as network IO, file IO, etc),
    # then this must be set to False.
    async_ok = False

    def __init__(self):
        # Determine any parameters that are necessary for this filter to work.
        # The base class does not have an __init__, so no need to call super().
        pass

    def _validate(self) -> Optional[Awaitable]:
        # Perform any checks of the configuration and make sure any required
        # libraries are available. Can perform checks synchronously or async.
        pass

    def _apply(self, item: FileItem) -> FileItem:
        # Perform any mutation of the filename or the file contents held within
        # the FileItem object. Return either the original item or a new
        # FileItem.
        # To easily make a new copy with updated members, for example:
        #     return item.copy(filename='new_name')
        #     return item.copy(data=BytesIO(b'new content'))
        return item
