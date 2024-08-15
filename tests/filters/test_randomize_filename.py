from io import BytesIO

import pytest

from filestorage import FileItem
from filestorage.filters import RandomizeFilename


@pytest.fixture
def item():
    return FileItem(filename="file.txt", path=("folder",), data=BytesIO(b"content"))


def with_spam(old_name):
    return "SPAM-" + old_name + "-SPAM"


def test_randomize_filename(item):
    filter = RandomizeFilename()

    result1 = filter._apply(item)
    result2 = filter._apply(item)

    assert result1.filename != "file.txt"
    assert result1.filename != result2
    assert result1.filename.endswith(".txt")

    # And nothing else is changed
    assert item.data == result1.data
    assert item.path == result1.path


def test_custom_randomize_filename(item):
    filter = RandomizeFilename(name_generator=with_spam)

    result1 = filter._apply(item)

    assert result1.filename == "SPAM-file-SPAM.txt"
