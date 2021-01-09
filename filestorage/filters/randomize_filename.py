import os
from typing import Callable
from uuid import uuid4

from filestorage import FilterBase, FileItem


def random_string_generator(filename: str) -> str:
    return str(uuid4())


class RandomizeFilename(FilterBase):
    """Randomize the name for every file"""

    async_ok = True

    def __init__(
        self,
        name_generator: Callable[[str], str] = random_string_generator,
    ):
        self.name_generator = name_generator

    def _apply(self, item: FileItem) -> FileItem:

        name, ext = os.path.splitext(item.filename)
        randomized_name = self.name_generator(name) + ext.lower()

        return item.copy(filename=randomized_name)
