import os
import pytest
from io import BytesIO

from filestorage import FileItem


@pytest.mark.parametrize(
    ("filename", "mediatype"),
    [
        ["foo", None],
        ["foo.txt", "text/plain"],
        ["foo.html", "text/html"],
        ["foo.jpg", "image/jpeg"],
        ["foo.png", "image/png"],
    ],
)
def test_content_type_guess(filename, mediatype):
    item = FileItem(filename=filename)

    assert item.content_type == mediatype


def text_content_type_fixed():
    item = FileItem(filename="foo.txt", media_type="wacky")

    assert item.content_type == "wacky"


def test_fileitem_reader():
    item = FileItem(filename="foo.txt", data=BytesIO(b"contents"))
    item.data.seek(3)

    with item as f:
        assert f.read() == b"contents"
        f.seek(3)
        assert f.read() == b"tents"


@pytest.mark.asyncio
async def test_async_fileitem_reader():
    item = FileItem(filename="foo.txt", data=BytesIO(b"contents"))
    item.data.seek(3)

    async with item as f:
        assert await f.read() == b"contents"
        await f.seek(3)
        assert await f.read() == b"tents"


def test_url_path():
    item = FileItem(filename="foo.txt", path=("folder", "subfolder"))

    assert item.url_path == "folder/subfolder/foo.txt"


def test_fs_path():
    item = FileItem(filename="foo.txt", path=("folder", "subfolder"))

    if os.name == "nt":
        assert item.fs_path == "folder\\subfolder\\foo.txt"
    else:
        assert item.fs_path == "folder/subfolder/foo.txt"


def test_has_data():
    item1 = FileItem(filename="foo.txt")
    item2 = FileItem(filename="foo.txt", data=BytesIO(b""))

    assert not item1.has_data
    assert item2.has_data


def test_copy_all():
    item = FileItem(
        filename="foo.txt",
        path=("folder",),
        data=BytesIO(b"contents"),
        media_type="stuff",
    )

    new_item = item.copy()

    # Identical tuples are identical
    assert new_item == item
    assert new_item.data is item.data


def test_copy_new_data():
    item = FileItem(
        filename="foo.txt",
        path=("folder",),
        data=BytesIO(b"contents"),
        media_type="stuff",
    )

    new_item = item.copy(data=BytesIO(b"other"))

    # Tuple is no longer identical as the data is different
    assert new_item != item
    assert new_item.filename == item.filename
    assert new_item.path == item.path
    assert new_item.media_type == item.media_type


def test_copy_new_filename():
    item = FileItem(
        filename="foo.txt",
        path=("folder",),
        data=BytesIO(b"contents"),
        media_type="stuff",
    )

    new_item = item.copy(filename="bar.txt")

    # Tuple is no longer identical as the data is different
    assert new_item != item
    assert new_item.filename == "bar.txt"
    assert new_item.data is item.data
    assert new_item.path == item.path
    assert new_item.media_type == item.media_type
